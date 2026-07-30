"""tests.test_cli"""

from __future__ import annotations

from typing import Annotated

import pytest

from xnano.cli import Argument, CliError, Command, Option
from xnano.cli.command import HelpException


def test_command_decorator_and_simple_parsing() -> None:
    app = Command(name="my-app", strict=True)
    runs: list[tuple[int, bool, str]] = []

    @app
    @Command.option("--count", default=1, help="Number of repetitions")
    @Command.option(
        ["--verbose", "-v"], is_flag=True, help="Enable verbose output"
    )
    def main(count: int, verbose: bool, name: str) -> None:
        runs.append((count, verbose, name))

    app.run(["--count", "3", "-v", "Alice"])
    assert runs == [(3, True, "Alice")]


def test_command_strict_validation() -> None:
    app_strict = Command(name="strict-app", strict=True)

    @app_strict
    def main(count: int) -> None:
        pass

    _target, parsed = app_strict.parse_arguments(["--count", "42"])
    assert parsed["count"] == 42

    with pytest.raises(ValueError, match="Invalid value for parameter"):
        app_strict.parse_arguments(["--count", "not-an-int"])


def test_missing_required_positional() -> None:
    app = Command(name="required-app")

    @app
    def main(name: str) -> None:
        pass

    with pytest.raises(ValueError, match="Missing required argument: name"):
        app.parse_arguments([])


def test_subcommands() -> None:
    app = Command(name="git")
    sub_runs: list[tuple] = []

    @app.command(name="commit", description="Record changes")
    @Command.option("--message", help="Commit message")
    @Command.option("--amend", is_flag=True, help="Amend")
    def commit(message: str, amend: bool) -> None:
        sub_runs.append(("commit", message, amend))

    @app.command(name="push")
    def push(remote: str = "origin", branch: str = "main") -> None:
        sub_runs.append(("push", remote, branch))

    app.run(["commit", "--message", "Fix bug", "--amend"])
    app.run(["push", "upstream", "dev"])
    app.run(["push"])
    assert sub_runs[0] == ("commit", "Fix bug", True)
    assert sub_runs[1] == ("push", "upstream", "dev")
    assert sub_runs[2] == ("push", "origin", "main")


def test_help_exception_and_plain_help() -> None:
    app = Command(name="tool", description="A tool")

    @app
    def main(verbose: bool = False) -> None:
        pass

    with pytest.raises(HelpException):
        app.parse_arguments(["--help"])
    help_text = app.get_help()
    assert "Usage: tool" in help_text
    assert "--verbose" in help_text or "verbose" in help_text.lower()


def test_option_and_argument_metadata_types() -> None:
    option = Option("-f", "--force", help="Force")
    assert option.flags == ("-f", "--force")
    argument = Argument(help="Target", metavar="TARGET")
    assert argument.metavar == "TARGET"
    error = CliError("boom", exit_code=2)
    assert error.exit_code == 2


def test_annotated_command_combines_arguments_options_and_repeats() -> None:
    app = Command(name="deploy", strict=True)
    calls: list[tuple[str, list[str], bool]] = []

    @app
    def deploy(
        environment: Annotated[
            str,
            Argument(
                help="Deployment environment",
                metavar="ENV",
                choices=("staging", "production"),
            ),
        ],
        tag: Annotated[
            list[str],
            Option("-t", "--tag", help="Image tag"),
        ],
        force: Annotated[
            bool,
            Option("-f", "--force", help="Skip confirmation"),
        ] = False,
    ) -> None:
        calls.append((environment, tag, force))

    app.run(["production", "--tag", "api", "-t", "worker", "--force"])

    assert calls == [("production", ["api", "worker"], True)]
    help_text = app.get_help()
    assert "ENV" in help_text
    assert "--tag" in help_text
