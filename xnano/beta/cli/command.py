"""xnano.beta.cli.command

---

Define typed commands and subcommands from ordinary Python methods.
"""

from __future__ import annotations

import argparse
import dataclasses
import inspect
import sys
from typing import (
    Annotated,
    Any,
    Callable,
    get_args,
    get_origin,
    get_type_hints,
)

from xnano.beta.cli.errors import CliError, HelpRequested
from xnano.beta.cli.help import format_plain_help, print_error, render_help
from xnano.beta.cli.parameters import Argument, Option
from xnano.beta.utils import validation

UNSET = object()


@dataclasses.dataclass
class _Parameter:
    """Resolved command parameter used while parsing arguments."""

    parameter_name: str
    flags: list[str] | None = None
    default: Any = UNSET
    help: str | None = None
    metavar: str | None = None
    choices: tuple[Any, ...] | None = None
    is_flag: bool = False
    annotation: Any = Any
    required: bool = True
    hidden: bool = False
    is_option: bool = False
    repeat: bool = False


@dataclasses.dataclass
class Command:
    """A command or subcommand group.

    Attributes:
        name: The name of the command.
        description: A description of the command.
        strict: Whether to validate parameter types against annotations.
        show_help: Whether ``--help`` / ``-h`` are recognized.
        help: Compatibility alias for ``show_help``.
        parameters: Resolved command parameters.
        subcommands: Registered subcommands.

    Example:
        >>> command = Command(name="hello")
        >>> @command
        ... def greet(name: str) -> str:
        ...     return f"Hello, {name}"
        >>> command.run(["Ada"])
        'Hello, Ada'
    """

    name: str | None = None
    """Command name shown in usage."""
    description: str | None = None
    """Command summary shown in help."""
    strict: bool = False
    """Whether annotations are validated strictly."""
    show_help: bool = True
    """Whether ``-h`` and ``--help`` are enabled."""
    # Drop-in alias used by older help code / tests.
    help: bool = True
    """Compatibility alias for ``show_help``."""

    UNSET: Any = dataclasses.field(default=UNSET, init=False, repr=False)
    """Sentinel used for parameters without defaults."""

    _callback: Callable[..., Any] | None = dataclasses.field(
        default=None, init=False, repr=False
    )
    _subcommands: dict[str, Command] = dataclasses.field(
        default_factory=dict, init=False, repr=False
    )
    _parameters: list[_Parameter] = dataclasses.field(
        default_factory=list, init=False, repr=False
    )
    _parser: argparse.ArgumentParser | None = dataclasses.field(
        default=None, init=False, repr=False
    )
    _parser_dirty: bool = dataclasses.field(
        default=True, init=False, repr=False
    )

    def __post_init__(self) -> None:
        self.show_help = bool(self.help)

    @property
    def parameters(self) -> list[_Parameter]:
        """Resolved parameters for help rendering."""
        return list(self._parameters)

    @property
    def subcommands(self) -> dict[str, "Command"]:
        """Registered subcommands."""
        return dict(self._subcommands)

    @staticmethod
    def option(
        name_or_flags: str | list[str],
        *,
        default: Any = None,
        help: str | None = None,
        is_flag: bool | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Attach option names and help text to a command parameter."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            options = getattr(func, "_cli_options", None)
            if options is None:
                options = []
                setattr(func, "_cli_options", options)
            if isinstance(name_or_flags, str):
                flags = [name_or_flags]
            else:
                flags = list(name_or_flags)
            options.append(
                {
                    "flags": flags,
                    "default": default,
                    "help": help,
                    "is_flag": is_flag,
                }
            )
            return func

        return decorator

    def command(
        self,
        name: str | None = None,
        *,
        description: str | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator to register a subcommand."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            func_name = getattr(func, "__name__", None) or "command"
            command_name = name or func_name.replace("_", "-")
            command_description = description or func.__doc__
            subcommand = Command(
                name=command_name,
                description=command_description,
                strict=self.strict,
                help=self.help,
            )
            subcommand._callback = func
            subcommand._register_from_function(func)
            self._subcommands[command_name] = subcommand
            self._parser_dirty = True
            return func

        return decorator

    def register_callback(
        self, func: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Register the main callback for this command."""
        self._callback = func
        self._register_from_function(func)
        self._parser_dirty = True
        return func

    def add_subcommand(self, subcommand: "Command") -> None:
        """Add a subcommand programmatically."""
        if not subcommand.name:
            raise CliError("Subcommand must have a name to be added.")
        self._subcommands[subcommand.name] = subcommand
        self._parser_dirty = True

    def _register_from_function(self, func: Callable[..., Any]) -> None:
        """Inspect ``func`` and build parameter metadata."""
        self._parameters.clear()
        signature = inspect.signature(func)
        try:
            type_hints = get_type_hints(func, include_extras=True)
        except Exception:
            type_hints = {}

        explicit_options = getattr(func, "_cli_options", [])
        parameter_to_explicit: dict[str, dict[str, Any]] = {}
        for option in explicit_options:
            flags = option["flags"]
            parameter_name = None
            for flag in flags:
                if flag.startswith("--"):
                    parameter_name = flag[2:].replace("-", "_")
                    break
            if parameter_name is None:
                for flag in flags:
                    if flag.startswith("-"):
                        parameter_name = flag[1:].replace("-", "_")
                        break
            if parameter_name is None:
                parameter_name = flags[0].replace("-", "_")
            parameter_to_explicit[parameter_name] = option

        for name, param in signature.parameters.items():
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue

            annotation = type_hints.get(name, Any)
            metadata_argument: Argument | None = None
            metadata_option: Option | None = None
            origin = get_origin(annotation)
            if origin is Annotated:
                args = get_args(annotation)
                annotation = args[0] if args else Any
                for extra in args[1:]:
                    if isinstance(extra, Argument):
                        metadata_argument = extra
                    elif isinstance(extra, Option):
                        metadata_option = extra

            default = param.default
            has_default = default is not inspect.Parameter.empty
            if isinstance(default, Option):
                metadata_option = default
                default = UNSET
                has_default = False
            if isinstance(default, Argument):
                metadata_argument = default
                default = UNSET
                has_default = False

            explicit = parameter_to_explicit.get(name)
            repeat = get_origin(annotation) is list

            if metadata_option is not None or explicit is not None:
                if explicit is not None:
                    flags = list(explicit["flags"])
                    option_default = explicit["default"]
                    if option_default is None and has_default:
                        option_default = default
                    elif option_default is None:
                        option_default = UNSET
                    is_flag = explicit["is_flag"]
                    help_text = explicit["help"]
                    choices = None
                    hidden = False
                    metavar = None
                else:
                    assert metadata_option is not None
                    flags = list(metadata_option.flags) or [
                        "--" + name.replace("_", "-")
                    ]
                    option_default = default if has_default else UNSET
                    is_flag = None
                    help_text = metadata_option.help
                    choices = (
                        tuple(metadata_option.choices)
                        if metadata_option.choices is not None
                        else None
                    )
                    hidden = metadata_option.hidden
                    metavar = metadata_option.metavar

                if is_flag is None:
                    is_flag = (annotation is bool) or (
                        option_default is not UNSET
                        and isinstance(option_default, bool)
                    )
                self._parameters.append(
                    _Parameter(
                        parameter_name=name,
                        flags=flags,
                        default=option_default,
                        help=help_text,
                        metavar=metavar,
                        choices=choices,
                        is_flag=bool(is_flag),
                        annotation=annotation,
                        required=not has_default and option_default is UNSET,
                        hidden=hidden,
                        is_option=True,
                        repeat=repeat,
                    )
                )
            elif metadata_argument is not None:
                self._parameters.append(
                    _Parameter(
                        parameter_name=name,
                        flags=None,
                        default=default if has_default else UNSET,
                        help=metadata_argument.help,
                        metavar=metadata_argument.metavar,
                        choices=(
                            tuple(metadata_argument.choices)
                            if metadata_argument.choices is not None
                            else None
                        ),
                        annotation=annotation,
                        required=not has_default,
                        is_option=False,
                        repeat=repeat,
                    )
                )
            else:
                # Match stable CLI: every inferred parameter gets a ``--name``
                # flag and may also be filled positionally when the flag form
                # is unused (see ``_parse_manual``).
                flag_name = "--" + name.replace("_", "-")
                is_flag = annotation is bool or (
                    has_default and isinstance(default, bool)
                )
                self._parameters.append(
                    _Parameter(
                        parameter_name=name,
                        flags=[flag_name],
                        default=default if has_default else UNSET,
                        help=None,
                        is_flag=is_flag,
                        annotation=annotation,
                        required=not has_default,
                        # Help treats non-explicit required params as args.
                        is_option=has_default or annotation is bool,
                        repeat=repeat,
                    )
                )

    def _build_parser(self) -> argparse.ArgumentParser:
        """Build (and cache) the argparse tree for this command."""
        if self._parser is not None and not self._parser_dirty:
            return self._parser

        parser = argparse.ArgumentParser(
            prog=self.name or "cli",
            description=self.description,
            add_help=False,
            allow_abbrev=False,
        )
        if self.show_help:
            parser.add_argument(
                "-h",
                "--help",
                action="store_true",
                help=argparse.SUPPRESS,
            )

        for parameter in self._parameters:
            kwargs: dict[str, Any] = {}
            if parameter.help:
                kwargs["help"] = parameter.help
            if parameter.metavar:
                kwargs["metavar"] = parameter.metavar
            if parameter.choices is not None:
                kwargs["choices"] = list(parameter.choices)
            if parameter.is_option:
                assert parameter.flags is not None
                if parameter.is_flag:
                    # default-True flags get --no-* style via store_false
                    if parameter.default is True:
                        kwargs["action"] = "store_false"
                    else:
                        kwargs["action"] = "store_true"
                        kwargs["default"] = False
                else:
                    if parameter.repeat:
                        kwargs["action"] = "append"
                    if parameter.default is not UNSET:
                        kwargs["default"] = parameter.default
                    elif not parameter.required:
                        kwargs["default"] = None
                parser.add_argument(
                    *parameter.flags,
                    dest=parameter.parameter_name,
                    **kwargs,
                )
            else:
                if parameter.repeat:
                    kwargs["nargs"] = "*"
                elif not parameter.required:
                    kwargs["nargs"] = "?"
                    if parameter.default is not UNSET:
                        kwargs["default"] = parameter.default
                parser.add_argument(parameter.parameter_name, **kwargs)

        if self._subcommands:
            sub = parser.add_subparsers(dest="_subcommand")
            for name, subcommand in self._subcommands.items():
                # Nested parsers are built on demand during parse.
                sub.add_parser(name, add_help=False)

        self._parser = parser
        self._parser_dirty = False
        return parser

    def parse_arguments(
        self, arguments: list[str]
    ) -> tuple["Command", dict[str, Any]]:
        """Parse arguments without exiting the process.

        Raises:
            HelpRequested: When help was requested.
            CliError: On usage / validation failures.
        """
        # Prefer the stable hand-parser semantics for drop-in parity with
        # existing tests, while exposing argparse caching for future work.
        return self._parse_manual(arguments)

    def _parse_manual(
        self, arguments: list[str]
    ) -> tuple["Command", dict[str, Any]]:
        """Parse positional arguments and named options from tokens."""
        parsed_values: dict[str, Any] = {}
        # Stable semantics: every parameter can be filled positionally in
        # declaration order when not already set by a flag.
        positional_params = list(self._parameters)
        option_by_flag: dict[str, _Parameter] = {}
        for parameter in self._parameters:
            if parameter.flags:
                for flag in parameter.flags:
                    option_by_flag[flag] = parameter

        positional_index = 0
        options_enabled = True
        index = 0
        while index < len(arguments):
            arg = arguments[index]
            if options_enabled and arg == "--":
                options_enabled = False
                index += 1
                continue
            if options_enabled and self.show_help and arg in ("--help", "-h"):
                raise HelpRequested(self)
            if options_enabled and arg.startswith("-") and arg != "-":
                if "=" in arg:
                    flag, value = arg.split("=", 1)
                else:
                    flag = arg
                    value = None
                parameter = option_by_flag.get(flag)
                if parameter is None:
                    raise CliError(f"Unknown option: {flag}", command=self)
                if parameter.is_flag:
                    if value is not None:
                        parsed_values[parameter.parameter_name] = value
                    elif parameter.default is True:
                        parsed_values[parameter.parameter_name] = False
                    else:
                        parsed_values[parameter.parameter_name] = True
                else:
                    if value is None:
                        if index + 1 >= len(arguments):
                            raise CliError(
                                f"Option {flag} requires a value",
                                command=self,
                            )
                        value = arguments[index + 1]
                        index += 1
                    if parameter.repeat:
                        parsed_values.setdefault(
                            parameter.parameter_name, []
                        ).append(value)
                    else:
                        parsed_values[parameter.parameter_name] = value
            else:
                if self._subcommands and arg in self._subcommands:
                    return self._subcommands[arg]._parse_manual(
                        arguments[index + 1 :]
                    )
                while (
                    positional_index < len(positional_params)
                    and positional_params[positional_index].parameter_name
                    in parsed_values
                ):
                    positional_index += 1
                if positional_index < len(positional_params):
                    matched = positional_params[positional_index]
                    if matched.repeat:
                        parsed_values.setdefault(
                            matched.parameter_name, []
                        ).append(arg)
                    else:
                        parsed_values[matched.parameter_name] = arg
                        positional_index += 1
                else:
                    if self._subcommands:
                        raise CliError(
                            f"Unknown command or unexpected argument: {arg}",
                            command=self,
                        )
                    raise CliError(
                        f"Unexpected positional argument: {arg}",
                        command=self,
                    )
            index += 1

        validated: dict[str, Any] = {}
        for parameter in self._parameters:
            name = parameter.parameter_name
            value = parsed_values.get(name)
            if value is None:
                if parameter.default is not UNSET:
                    value = parameter.default
                elif parameter.is_flag:
                    value = False if parameter.default is not True else True
                elif parameter.required:
                    raise CliError(
                        f"Missing required argument: {name}",
                        command=self,
                    )
                else:
                    value = None
            if value is not None and value is not UNSET:
                if self.strict:
                    try:
                        value = validation.validate_type(
                            value, parameter.annotation
                        )
                    except Exception as error:
                        raise CliError(
                            f"Invalid value for parameter '{name}': {error}",
                            command=self,
                        ) from error
                else:
                    try:
                        value = validation.validate_type(
                            value, parameter.annotation
                        )
                    except Exception:
                        pass
            validated[name] = None if value is UNSET else value
        return self, validated

    def run(self, arguments: list[str] | None = None) -> Any:
        """Parse arguments and run the command, exiting on errors/help."""
        if arguments is None:
            arguments = sys.argv[1:]
        try:
            target, parsed = self.parse_arguments(arguments)
        except HelpRequested as help_requested:
            print(render_help(help_requested.command), end="")
            sys.exit(0)
        except CliError as error:
            print_error(error.message, error.command or self)
            sys.exit(error.exit_code)
        except ValueError as error:
            # Compatibility with callers raising plain ValueError.
            print_error(str(error), self)
            sys.exit(2)

        if target._callback is None:
            print(render_help(target), end="")
            sys.exit(0)
        return target._callback(**parsed)

    def get_help(self) -> str:
        """Return plain help text for this command."""
        return format_plain_help(self)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Register a callback or run with ``sys.argv``."""
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return self.register_callback(args[0])
        return self.run(sys.argv[1:])


# Re-raise CliError as ValueError in parse for drop-in test compatibility
_original_parse = Command.parse_arguments


def _parse_arguments_compat(
    self: Command, arguments: list[str]
) -> tuple[Command, dict[str, Any]]:
    try:
        return _original_parse(self, arguments)
    except CliError as error:
        raise ValueError(error.message) from error
    except HelpRequested as help_requested:
        raise HelpException(help_requested.command) from help_requested


Command.parse_arguments = _parse_arguments_compat  # type: ignore[method-assign]


@dataclasses.dataclass
class HelpException(Exception):
    """Stop command parsing after help has been requested.

    Attributes:
        command: Command whose help should be displayed.
    """

    command: Command
    """Command whose help should be displayed."""

    def __post_init__(self) -> None:
        super().__init__()


__all__ = (
    "Command",
    "HelpException",
    "UNSET",
)
