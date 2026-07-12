---
title: CLI
icon: lucide/terminal-square
---

# CLI

`Command` is a model-like CLI builder under `xnano.cli`. You declare a named
app, decorate a callback (or subcommands) with options and types, then
`run()` parses `sys.argv` — or an explicit argument list — and calls the
matching function.

The goal is the same shape as grids: typed parameters, defaults, and a small
surface for help and validation. Help text is generated automatically; strict
mode can coerce and reject values against annotations.

```python title="app.py"
from xnano.cli import Command

app = Command(name="my-app", description="Demo CLI", strict=True)

@app
@Command.option("--count", default=1, help="Number of repetitions")
@Command.option(["--verbose", "-v"], is_flag=True, help="Verbose output")
def main(count: int, verbose: bool, name: str) -> None:
    prefix = "verbose: " if verbose else ""
    print(prefix + (f"{name} " * count))

if __name__ == "__main__":
    app()
```

```bash
python app.py --count 3 -v Alice
python app.py --help
```

---

## Building a command

```python
from xnano.cli import Command

app = Command(
    name="my-app",
    description="Short summary for help output",
    strict=False,  # (1)!
    help=True,     # (2)!
)
```

1. When `strict=True`, failed type coercion raises; when `False`, invalid
   values fall back to the raw string.
2. When `help=True`, `--help` / `-h` print usage and exit.

Register the main callback by decorating with the command instance, or call
`register_callback` explicitly:

```python
@app
def main(...) -> None: ...

# equivalent
app.register_callback(main)
```

Parameters come from the function signature:

| Signature detail | CLI form |
|---|---|
| Annotated name without `@Command.option` | Auto flag `--param-name` (underscores → hyphens) |
| `bool` annotation or `bool` default | Treated as a flag |
| Required parameter (no default) | Required unless an option supplies a default |
| `@Command.option(...)` | Explicit flags, help text, flag mode |

Positional tokens fill parameters that still lack a value, in declaration
order. Explicit options can use long and short flags together:

```python
@Command.option(["--message", "-m"], help="Commit message")
@Command.option("--amend", is_flag=True, help="Amend previous commit")
def commit(message: str, amend: bool) -> None: ...
```

---

## Subcommands

Use `@app.command` to nest commands under a parent group:

```python title="gitish.py"
from xnano.cli import Command

cli = Command(name="git")

@cli.command(name="commit", description="Record changes to the repository")
@Command.option("--message", help="Commit message")
@Command.option("--amend", is_flag=True, help="Amend previous commit")
def commit(message: str, amend: bool) -> None:
    print("commit", message, amend)

@cli.command(name="push")
def push(remote: str = "origin", branch: str = "main") -> None:
    print("push", remote, branch)

if __name__ == "__main__":
    cli()
```

```bash
python gitish.py commit --message "Fix bug" --amend
python gitish.py push upstream dev
python gitish.py push
python gitish.py commit --help
```

Subcommand names default to the function name with underscores replaced by
hyphens. Descriptions default to the function docstring. You can also attach
a pre-built `Command` with `add_subcommand`.

---

## Parsing and running

| Method | Behavior |
|---|---|
| `parse_arguments(list[str])` | Returns `(target_command, values)` or raises |
| `run(arguments=None)` | Parses `sys.argv[1:]` by default, prints help/errors, calls the callback |
| `get_help()` | Builds the usage / options / commands string |
| `app()` | As a decorator: register callback; as a call: run the CLI |

`HelpException` is raised internally when help is requested during parse;
`run` catches it, prints help, and exits with status `0`. Argument errors
print to stderr with help and exit with status `2`.

```python
target, values = app.parse_arguments(["--count", "2", "Alice"])
# target is the Command that should execute; values is a dict of kwargs
```

Supports `--flag=value` and `--flag value` forms. Unknown options and extra
positionals raise `ValueError` with a short message.

---

## Types

| Name | Role |
|---|---|
| `Command` | Root or subcommand: options, callback, nested commands |
| `CommandLineParameter` | Parsed parameter metadata (flags, default, annotation, …) |
| `HelpException` | Carries the `Command` whose help should be shown |

Import from the module directly:

```python
from xnano.cli import Command
from xnano.cli.command import CommandLineParameter, HelpException
```

---

## Where this fits

Commands cover the path from shell arguments into Python. Grids and the
[Web UI](../webui/index.md) cover interactive surfaces. Together they share
one declarative style from one-shot CLI tools through full interfaces.
