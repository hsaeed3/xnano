"""xnano.cli.command

---

Command-line interface for argument parsing and command execution,
built with library components and validation helpers.
"""

from __future__ import annotations

import dataclasses
import inspect
import sys
from typing import Any, Callable

from xnano import _validation as validation

UNSET = object()


@dataclasses.dataclass
class HelpException(Exception):
    """Exception raised when help is requested.

    Attributes:
        command: The command for which help was requested.
    """

    command: Command
    """The command for which help was requested."""

    def __post_init__(self) -> None:
        super().__init__()


@dataclasses.dataclass
class CommandLineParameter:
    """A command-line interface parameter representation.

    Attributes:
        parameter_name: The parameter name in the Python function.
        flags: CLI option flags, or None if it is a positional argument.
        default: Default value of the parameter.
        help: Description of the parameter.
        is_flag: Whether the option is a boolean flag.
        annotation: Type annotation of the parameter.
        required: Whether the parameter is required.
        explicit: Whether the parameter was explicitly defined via option decorator.
    """

    parameter_name: str
    """The parameter name in the Python function."""
    flags: list[str] | None = None
    """CLI option flags, or None if it is a positional argument."""
    default: Any = UNSET
    """Default value of the parameter."""
    help: str | None = None
    """Description of the parameter."""
    is_flag: bool = False
    """Whether the option is a boolean flag."""
    annotation: Any = Any
    """Type annotation of the parameter."""
    required: bool = True
    """Whether the parameter is required."""
    explicit: bool = False
    """Whether the parameter was explicitly defined via option decorator."""


@dataclasses.dataclass
class Command:
    """A command-line interface command or subcommand group.

    Attributes:
        name: The name of the command.
        description: A description of the command.
        strict: Whether to validate parameter types against annotations.
        help: Whether to automatically generate and display a help message.
    """

    name: str | None = None
    """The name of the command."""
    description: str | None = None
    """A description of the command."""
    strict: bool = False
    """Whether to validate parameter types against annotations."""
    help: bool = True
    """Whether to automatically generate and display a help message."""

    _callback: Callable[..., Any] | None = dataclasses.field(
        default=None, init=False
    )
    _subcommands: dict[str, Command] = dataclasses.field(
        default_factory=dict, init=False
    )
    _parameters: list[CommandLineParameter] = dataclasses.field(
        default_factory=list, init=False
    )

    @staticmethod
    def option(
        name_or_flags: str | list[str],
        *,
        default: Any = None,
        help: str | None = None,
        is_flag: bool | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator to attach option metadata to a command function.

        Args:
            name_or_flags: A single flag or a list of flags.
            default: The default value for the option.
            help: Help text for the option.
            is_flag: Whether this option is a boolean flag.

        Returns:
            A decorator that attaches option metadata to the decorated function.
        """

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
        """Decorator to register a subcommand.

        Args:
            name: The name of the subcommand. Inferred from function name if not provided.
            description: Description of the subcommand. Inferred from docstring if not provided.

        Returns:
            A decorator that registers the function as a subcommand.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            func_name = getattr(func, "__name__", None) or "command"
            cmd_name = name or func_name.replace("_", "-")
            cmd_desc = description or func.__doc__

            sub_cmd = Command(
                name=cmd_name,
                description=cmd_desc,
                strict=self.strict,
                help=self.help,
            )
            sub_cmd._callback = func
            sub_cmd._register_from_function(func)

            self._subcommands[cmd_name] = sub_cmd
            return func

        return decorator

    def register_callback(
        self, func: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Registers the callback function for this command.

        Args:
            func: The callback function to register.

        Returns:
            The callback function.
        """
        self._callback = func
        self._register_from_function(func)
        return func

    def add_subcommand(self, subcommand: Command) -> None:
        """Adds a subcommand programmatically.

        Args:
            subcommand: The subcommand to add.
        """
        if not subcommand.name:
            raise ValueError("Subcommand must have a name to be added.")
        self._subcommands[subcommand.name] = subcommand

    def _register_from_function(self, func: Callable[..., Any]) -> None:
        """Inspects the callback function to build the parameters.

        Args:
            func: The function to inspect.
        """
        signature = inspect.signature(func)
        try:
            from typing import get_type_hints

            type_hints = get_type_hints(func)
        except Exception:
            type_hints = {}

        explicit_options = getattr(func, "_cli_options", [])
        parameter_to_explicit = {}
        for opt in explicit_options:
            flags = opt["flags"]
            parameter_name = None
            for flag in flags:
                if flag.startswith("--"):
                    parameter_name = flag[2:].replace("-", "_")
                    break
            if not parameter_name:
                for flag in flags:
                    if flag.startswith("-"):
                        parameter_name = flag[1:].replace("-", "_")
                        break
            if not parameter_name:
                parameter_name = flags[0].replace("-", "_")

            parameter_to_explicit[parameter_name] = opt

        for name, param in signature.parameters.items():
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue

            annotation = type_hints.get(name, Any)
            default = param.default
            has_default = default is not inspect.Parameter.empty

            explicit = parameter_to_explicit.get(name)

            if explicit:
                flags = explicit["flags"]
                opt_default = explicit["default"]
                if opt_default is None and has_default:
                    opt_default = default
                elif opt_default is None:
                    opt_default = UNSET

                is_flag = explicit["is_flag"]
                if is_flag is None:
                    is_flag = (annotation is bool) or (
                        opt_default is not UNSET
                        and isinstance(opt_default, bool)
                    )

                self._parameters.append(
                    CommandLineParameter(
                        parameter_name=name,
                        flags=flags,
                        default=opt_default,
                        help=explicit["help"],
                        is_flag=is_flag,
                        annotation=annotation,
                        required=not has_default and opt_default is UNSET,
                        explicit=True,
                    )
                )
            else:
                flag_name = "--" + name.replace("_", "-")
                is_flag = annotation is bool or (
                    has_default and isinstance(default, bool)
                )
                self._parameters.append(
                    CommandLineParameter(
                        parameter_name=name,
                        flags=[flag_name],
                        default=default if has_default else UNSET,
                        help=None,
                        is_flag=is_flag,
                        annotation=annotation,
                        required=not has_default,
                        explicit=False,
                    )
                )

    def parse_arguments(
        self, arguments: list[str]
    ) -> tuple[Command, dict[str, Any]]:
        """Parses command-line arguments.

        Args:
            arguments: A list of command-line argument strings.

        Returns:
            A tuple containing:
                - The target Command to execute.
                - A dictionary of validated parameter values.

        Raises:
            HelpException: If help is requested.
            ValueError: If parsing or validation fails.
        """
        option_by_flag = {}
        for param in self._parameters:
            if param.flags:
                for flag in param.flags:
                    option_by_flag[flag] = param

        parsed_values = {}
        positional_params = list(self._parameters)

        index = 0
        while index < len(arguments):
            arg = arguments[index]

            if self.help and arg in ("--help", "-h"):
                raise HelpException(self)

            if arg.startswith("-"):
                if "=" in arg:
                    flag, val = arg.split("=", 1)
                else:
                    flag = arg
                    val = None

                param = option_by_flag.get(flag)
                if not param:
                    raise ValueError(f"Unknown option: {flag}")

                if param.is_flag:
                    if val is not None:
                        parsed_values[param.parameter_name] = val
                    else:
                        parsed_values[param.parameter_name] = True
                else:
                    if val is not None:
                        parsed_values[param.parameter_name] = val
                    else:
                        if index + 1 >= len(arguments):
                            raise ValueError(f"Option {flag} requires a value")
                        parsed_values[param.parameter_name] = arguments[
                            index + 1
                        ]
                        index += 1
            else:
                if self._subcommands and arg in self._subcommands:
                    sub_cmd = self._subcommands[arg]
                    return sub_cmd.parse_arguments(arguments[index + 1 :])

                # Match to the first remaining positional parameter that hasn't been set yet
                matched_param = None
                for p in positional_params:
                    if p.parameter_name not in parsed_values:
                        matched_param = p
                        break

                if matched_param:
                    parsed_values[matched_param.parameter_name] = arg
                else:
                    if self._subcommands:
                        raise ValueError(
                            f"Unknown command or unexpected argument: {arg}"
                        )
                    else:
                        raise ValueError(
                            f"Unexpected positional argument: {arg}"
                        )
            index += 1

        validated_values = {}
        for param in self._parameters:
            name = param.parameter_name
            val = parsed_values.get(name)

            if val is None:
                if param.default is not UNSET:
                    val = param.default
                elif param.required:
                    raise ValueError(f"Missing required argument: {name}")
                else:
                    val = None

            if val is not None and val is not UNSET:
                if self.strict:
                    try:
                        val = validation.validate_type(val, param.annotation)
                    except Exception as err:
                        raise ValueError(
                            f"Invalid value for parameter '{name}': {err}"
                        )
                else:
                    try:
                        val = validation.validate_type(val, param.annotation)
                    except Exception:
                        pass

            validated_values[name] = None if val is UNSET else val

        return self, validated_values

    def run(self, arguments: list[str] | None = None) -> Any:
        """Parses arguments and runs the command/subcommand.

        Args:
            arguments: The arguments to parse. Defaults to sys.argv[1:].

        Returns:
            The return value of the callback.
        """
        if arguments is None:
            arguments = sys.argv[1:]

        try:
            target_command, parsed_args = self.parse_arguments(arguments)
        except HelpException as help_exception:
            print(help_exception.command.get_help())
            sys.exit(0)
        except ValueError as error:
            print(f"Error: {error}", file=sys.stderr)
            print(self.get_help(), file=sys.stderr)
            sys.exit(2)

        if target_command._callback is None:
            print(target_command.get_help())
            sys.exit(0)

        return target_command._callback(**parsed_args)

    def get_help(self) -> str:
        """Generates a help message for this command.

        Returns:
            The generated help message.
        """
        lines = []
        usage = f"Usage: {self.name or 'cli'}"
        if self._subcommands:
            usage += " [COMMAND]"

        options_list = []
        arguments_list = []
        for param in self._parameters:
            if param.flags is None or (
                not param.explicit and param.default is UNSET
            ):
                arguments_list.append(param)
            else:
                options_list.append(param)

        if options_list:
            usage += " [OPTIONS]"
        for arg in arguments_list:
            usage += f" {arg.parameter_name.upper()}"

        lines.append(usage)
        lines.append("")

        if self.description:
            lines.append(self.description.strip())
            lines.append("")

        if arguments_list:
            lines.append("Arguments:")
            for arg in arguments_list:
                help_text = arg.help or ""
                desc = f"  {arg.parameter_name.upper():<20} {help_text}"
                if arg.default is not UNSET:
                    desc += f" (default: {arg.default})"
                lines.append(desc)
            lines.append("")

        if options_list or self.help:
            lines.append("Options:")
            for opt in options_list:
                flags_str = ", ".join(opt.flags or [])
                help_text = opt.help or ""
                desc = f"  {flags_str:<20} {help_text}"
                if opt.default is not UNSET:
                    desc += f" [default: {opt.default}]"
                lines.append(desc)
            if self.help:
                lines.append(
                    f"  {'--help, -h':<20} Show this message and exit."
                )
            lines.append("")

        if self._subcommands:
            lines.append("Commands:")
            for name, sub_cmd in self._subcommands.items():
                desc = sub_cmd.description or ""
                first_line_desc = desc.strip().split("\n")[0]
                lines.append(f"  {name:<20} {first_line_desc}")
            lines.append("")

        return "\n".join(lines)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Invokes the CLI or registers a callback if called as a decorator.

        If the first argument is a callable (and no other arguments are passed),
        it registers that callable as the main command callback.
        Otherwise, it runs the command with command-line arguments.
        """
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return self.register_callback(args[0])

        cli_args = sys.argv[1:]
        return self.run(cli_args)


__all__ = (
    "Command",
    "CommandLineParameter",
    "HelpException",
)
