---
title: "CLI Commands"
icon: "lucide/terminal"
---

# CLI Commands

[Command]{data-preview} declares options and subcommands for process arguments. Decorate a callback, declare options, call `run()`.

It is not a TUI host — pair it with [Terminal]{data-preview} only when a tool needs both a CLI entry and an interactive session.

## A Root Command

Construct a `Command`, register a callback with `@cli`, and decorate options with `@Command.option`. Parameter names map from flags (`--name` → `name`).

```python title="A Root Command" hl_lines="3 5 6 7 8"
from xnano.cli import Command

cli = Command(name="tool", description="A small utility")

@cli # (1)!
@Command.option("--name", default="world", help="Who to greet")
def greet(name: str = "world") -> None:
    print(f"hello, {name}")

if __name__ == "__main__":
    cli.run() # (2)!
```

1. `@cli` registers the function as this command's main callback. The same form works as `cli(greet)` after the function is defined.
2. `run()` parses `sys.argv[1:]` by default. Pass a list explicitly in tests: `cli.run(["--name", "hammad"])`.

<br/>

```bash title="Usage"
uv run python tool.py
# hello, world

uv run python tool.py --name hammad
# hello, hammad

uv run python tool.py --help
```

Types on the signature drive coercion when values are parseable (`int`, `bool`, and so on). Set `Command(strict=True)` to raise on bad values instead of falling back to the raw string.

## Subcommands

`@cli.command()` nests another command under a name. Options attach to the subcommand function the same way.

```python title="Subcommands" hl_lines="5 6 7 8 10 11 12 13 14"
from xnano.cli import Command

cli = Command(name="ship", description="Release helpers")

@cli.command(name="greet", description="Print a greeting")
@Command.option("--name", default="world", help="Who to greet")
def greet(name: str = "world") -> None:
    print(f"hello, {name}")

@cli.command(name="bump")
@Command.option("--major", is_flag=True, help="Bump the major version")
def bump(major: bool = False) -> None: # (1)!
    kind = "major" if major else "patch"
    print(f"bumping {kind}")

if __name__ == "__main__":
    cli.run()
```

1. Boolean options become flags when annotated `bool` or when `is_flag=True` is set. Present on the command line → `True`; absent → the default.

<br/>

```bash title="Usage"
uv run python ship.py greet --name crew
uv run python ship.py bump --major
uv run python ship.py --help
uv run python ship.py bump --help
```

Subcommand names default from the function name with underscores turned into hyphens (`def dry_run` → `dry-run`) when `name=` is omitted. Descriptions fall back to the function docstring.

## Options and Positionals

Flags use `@Command.option`; parameters without an explicit option still appear as `--param-name` style flags derived from the signature. Short aliases take a list of flags:

```python title="Short Flags"
@Command.option(["--verbose", "-v"], is_flag=True, help="Verbose output")
def build(verbose: bool = False) -> None:
    ...
```

<br/>

The same validation helpers used for fields also coerce CLI values when types are annotated.

[Command]: ../api/xnano/cli/command.md
[Terminal]: ../api/xnano/tui/terminal.md
