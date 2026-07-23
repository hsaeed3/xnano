"""tests.web.test_commands"""

from __future__ import annotations

import pytest

from xnano.cli.command import Command, HelpException


def test_command_decorator_and_simple_parsing() -> None:
    """Tests basic option and parameter definition and execution."""
    app = Command(name="my-app", strict=True)

    runs = []

    @app
    @Command.option("--count", default=1, help="Number of repetitions")
    @Command.option(
        ["--verbose", "-v"], is_flag=True, help="Enable verbose output"
    )
    def main(count: int, verbose: bool, name: str) -> None:
        runs.append((count, verbose, name))

    # Test running with correct arguments
    app.run(["--count", "3", "-v", "Alice"])
    assert len(runs) == 1
    assert runs[0] == (3, True, "Alice")


def test_command_strict_validation() -> None:
    """Tests strict parameter type validation and coercion."""
    # With strict=True, invalid type raises ValueError
    app_strict = Command(name="strict-app", strict=True)

    @app_strict
    def main(count: int) -> None:
        pass

    # Coercion should work
    target, parsed = app_strict.parse_arguments(["--count", "42"])
    assert parsed["count"] == 42

    # Invalid int should raise ValueError
    with pytest.raises(
        ValueError, match="Invalid value for parameter 'count'"
    ):
        app_strict.parse_arguments(["--count", "not-an-int"])

    # With strict=False, invalid type should fallback to the raw value
    app_lax = Command(name="lax-app", strict=False)

    @app_lax
    def main_lax(count: int) -> None:
        pass

    target, parsed = app_lax.parse_arguments(["--count", "not-an-int"])
    assert parsed["count"] == "not-an-int"


def test_missing_required_positional_argument() -> None:
    """Tests that missing a required positional argument raises ValueError."""
    app = Command(name="required-app")

    @app
    def main(name: str) -> None:
        pass

    with pytest.raises(ValueError, match="Missing required argument: name"):
        app.parse_arguments([])


def test_subcommands() -> None:
    """Tests subcommand routing and parsing."""
    app = Command(name="git")

    sub_runs = []

    @app.command(name="commit", description="Record changes to repository")
    @Command.option("--message", help="Commit message")
    @Command.option("--amend", is_flag=True, help="Amend previous commit")
    def commit(message: str, amend: bool) -> None:
        sub_runs.append(("commit", message, amend))

    @app.command(name="push")
    def push(remote: str = "origin", branch: str = "main") -> None:
        sub_runs.append(("push", remote, branch))

    # Test routing to commit
    app.run(["commit", "--message", "Fix bug", "--amend"])
    assert len(sub_runs) == 1
    assert sub_runs[-1] == ("commit", "Fix bug", True)

    # Test routing to push
    app.run(["push", "upstream", "dev"])
    assert len(sub_runs) == 2
    assert sub_runs[-1] == ("push", "upstream", "dev")

    # Test push default values
    app.run(["push"])
    assert len(sub_runs) == 3
    assert sub_runs[-1] == ("push", "origin", "main")


def test_help_generation() -> None:
    """Tests automatic help text generation and HelpException raising."""
    app = Command(name="test-help", description="Test help CLI tool")

    @app
    @Command.option("--count", default=1, help="Repetition count")
    def main(count: int, name: str) -> None:
        pass

    # Requesting help via flag should raise HelpException
    with pytest.raises(HelpException) as exc_info:
        app.parse_arguments(["--help"])

    help_text = exc_info.value.command.get_help()
    assert "Usage: test-help [OPTIONS] NAME" in help_text
    assert "Test help CLI tool" in help_text
    assert "--count" in help_text
    assert "--help, -h" in help_text

    # With subcommands
    git_app = Command(name="git")

    @git_app.command(name="commit", description="Record changes")
    def commit():
        pass

    with pytest.raises(HelpException) as exc_info:
        git_app.parse_arguments(["commit", "--help"])

    sub_help_text = exc_info.value.command.get_help()
    assert "Usage: commit" in sub_help_text
    assert "Record changes" in sub_help_text
