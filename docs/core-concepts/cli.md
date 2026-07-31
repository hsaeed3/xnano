---
title: "CLI Commands"
icon: "lucide/terminal"
---

# CLI Commands

!!! warning "Experimental"

    `Command` is a small, experimental CLI surface for prototypes and internal
    tools. It is not a replacement for [typer](https://typer.tiangolo.com/) or
    [click](https://click.palletsprojects.com/), and the API may still change.

[Command]{data-preview} is xnano's process-argument surface: options,
subcommands, and help for small tools. It is not a TUI host.

Use it when a project needs a real argv entrypoint. Pair it with
[Terminal](terminal.md) only when the same project also runs an interactive
session.

A `Command` can:

- Register a root callback <small>(`@cli` or `register_callback`)</small>
- Declare options and flags <small>(`@Command.option`)</small>
- Nest subcommands <small>(`@cli.command()` or `add_subcommand`)</small>
- Coerce values from type annotations <small>(optionally `strict=True`)</small>
- Emit help <small>(`--help` / `-h`)</small>

<div class="grid-concept-diagram" role="img" aria-label="Diagram: argv flows into Command parse, then into a callback or nested subcommand">
<svg viewBox="0 0 720 220" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="cli-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>

  <rect class="gcd-panel" x="28" y="60" width="140" height="80" rx="12" />
  <text class="gcd-label" x="98" y="96" text-anchor="middle">argv</text>
  <text class="gcd-chrome-label" x="98" y="118" text-anchor="middle">flags · words</text>

  <line class="gcd-arrow" x1="168" y1="100" x2="220" y2="100" marker-end="url(#cli-arrow)" />

  <rect class="gcd-panel gcd-panel-accent" x="232" y="48" width="200" height="104" rx="14" />
  <text class="gcd-label gcd-label-accent" x="332" y="84" text-anchor="middle">Command</text>
  <text class="gcd-chrome-label" x="332" y="108" text-anchor="middle">parse · coerce</text>
  <text class="gcd-chrome-label" x="332" y="128" text-anchor="middle">help · route</text>

  <line class="gcd-arrow" x1="432" y1="80" x2="488" y2="60" marker-end="url(#cli-arrow)" />
  <line class="gcd-arrow" x1="432" y1="120" x2="488" y2="140" marker-end="url(#cli-arrow)" />

  <rect class="gcd-window" x="500" y="36" width="192" height="56" rx="10" />
  <text class="gcd-chrome-label" x="596" y="68" text-anchor="middle">root callback</text>

  <rect class="gcd-window" x="500" y="116" width="192" height="56" rx="10" />
  <text class="gcd-chrome-label" x="596" y="148" text-anchor="middle">subcommand</text>
</svg>
</div>

## A root command

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

1. `@cli` registers the function as the main callback. Also valid:
   `cli(greet)` or `cli.register_callback(greet)`.
2. `run()` parses `sys.argv[1:]` by default. Pass a list in tests:
   `cli.run(["--name", "hammad"])`.

```bash title="Usage"
uv run python tool.py
# hello, world

uv run python tool.py --name hammad
# hello, hammad

uv run python tool.py --help
```

Types on the signature drive coercion when values are parseable. Set
`Command(strict=True)` to raise on bad values instead of leaving the raw string.

## Options and flags

```python title="Options and Flags" hl_lines="6 7 8 9"
from xnano.cli import Command

cli = Command(name="build", description="Compile the project")

@cli
@Command.option("--count", default=1, help="How many times")
@Command.option(["--verbose", "-v"], is_flag=True, help="Verbose output")
def main(count: int = 1, verbose: bool = False) -> None: # (1)!
    mode = "verbose" if verbose else "quiet"
    print(f"building ×{count} ({mode})")
```

1. `--count` takes a value; `-v` / `--verbose` is a bare flag. Parameter names
   match the long flag form (`count`, `verbose`).

```bash title="Usage"
uv run python build.py --count 3 -v
# building ×3 (verbose)
```

Parameters without an explicit `@Command.option` still appear as
`--param-name` flags derived from the signature.

??? note "Flags vs. values"

    - `is_flag=True` (or a `bool` annotation / default) treats presence as `True`.
    - Otherwise the next argument is the value (`--count 3` or `--count=3`).

## Subcommands

<div class="grid-concept-diagram grid-concept-diagram--compact" role="img" aria-label="Diagram: root command branches to nested subcommands">
<svg viewBox="0 0 400 110" xmlns="http://www.w3.org/2000/svg" fill="none">
  <defs>
    <marker id="sc-arr" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" class="gcd-arrow-fill" />
    </marker>
  </defs>
  <rect class="gcd-panel gcd-panel-accent" x="20" y="32" width="100" height="48" rx="10" />
  <text class="gcd-label gcd-label-accent" x="70" y="60" text-anchor="middle">ship</text>
  <line class="gcd-arrow" x1="120" y1="46" x2="180" y2="32" marker-end="url(#sc-arr)" />
  <line class="gcd-arrow" x1="120" y1="66" x2="180" y2="80" marker-end="url(#sc-arr)" />
  <rect class="gcd-window" x="192" y="12" width="160" height="40" rx="8" />
  <text class="gcd-chrome-label" x="272" y="36" text-anchor="middle">greet</text>
  <rect class="gcd-window" x="192" y="60" width="160" height="40" rx="8" />
  <text class="gcd-chrome-label" x="272" y="84" text-anchor="middle">bump</text>
</svg>
</div>

```python title="Subcommands" hl_lines="5 6 7 8 10 11 12 13 14"
from xnano.cli import Command

cli = Command(name="ship", description="Release helpers")

@cli.command(name="greet", description="Print a greeting")
@Command.option("--name", default="world", help="Who to greet")
def greet(name: str = "world") -> None:
    print(f"hello, {name}")

@cli.command(name="bump")
@Command.option("--major", is_flag=True, help="Bump the major version")
def bump(major: bool = False) -> None:
    kind = "major" if major else "patch"
    print(f"bumping {kind}")

if __name__ == "__main__":
    cli.run()
```

```bash title="Usage"
uv run python ship.py greet --name crew
# hello, crew

uv run python ship.py bump --major
# bumping major

uv run python ship.py --help
uv run python ship.py bump --help
```

Subcommand names default from the function name (`dry_run` → `dry-run`) when
`name=` is omitted. You can also use `add_subcommand(Command(...))`.

## Help

With `help=True` (the default), `--help` / `-h` print usage and exit.
`get_help()` returns the same text as a string.

```python title="Help Text" hl_lines="8"
from xnano.cli import Command

cli = Command(name="tool", description="A small utility")

@cli
@Command.option("--name", default="world", help="Who to greet")
def greet(name: str = "world") -> None:
    print(f"hello, {name}")

print(cli.get_help())
```

```text title="Example help"
Usage: tool [OPTIONS]

A small utility

Options:
  --name               Who to greet [default: world]
  --help, -h           Show this message and exit.
```

## Strict mode

```python title="Strict Mode" hl_lines="3 6"
from xnano.cli import Command

cli = Command(name="count", strict=True)

@cli
def main(n: int) -> None:
    print(n * 2)

cli.run(["--n", "21"])   # prints 42
# cli.run(["--n", "nope"])  # Error: Invalid value for parameter 'n': ...
```

## Parsing without running

```python title="Parse Only" hl_lines="8 9"
from xnano.cli import Command

cli = Command(name="tool")

@cli
@Command.option("--name", default="world")
def greet(name: str = "world") -> None:
    ...

target, values = cli.parse_arguments(["--name", "hammad"])
assert values["name"] == "hammad"
assert target is cli
```

## Next

- [Command API](../api/xnano/cli/command.md){data-preview}
- [Terminal](terminal.md) when you need a live UI session

??? abstract "API"

    [`Command`](../api/xnano/cli/command.md){data-preview} ·
    [`xnano.cli`](../api/xnano/cli.md){data-preview}

[Command]: ../api/xnano/cli/command.md
