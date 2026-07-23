"""xnano.__main__

Entrypoint for ``python -m xnano`` and the installed ``xnano`` script.

- no args → feature demo
- path to a Markdown file → document runner
- ``--help`` → short usage
"""

from __future__ import annotations

import sys


def run_demo() -> None:
    """Dispatch the installed ``xnano`` entrypoint."""
    arguments = sys.argv[1:]
    if not arguments:
        from xnano.beta.core.demo import run_demo as _run_feature_demo

        _run_feature_demo()
        return

    if arguments[0] in {"-h", "--help", "help"}:
        print(
            "Usage: xnano [PATH.md]\n"
            "\n"
            "  xnano              Run the feature showcase demo\n"
            "  xnano PATH.md      Page through a Markdown document\n"
            "  xnano --help       Show this help\n"
        )
        return

    path = arguments[0]
    from xnano.beta.markdown import is_markdown_path, run_markdown

    if is_markdown_path(path):
        run_markdown(path)
        return

    print(
        f"Error: unknown input {path!r}.\n"
        "Pass an existing Markdown file (.md) or run with no arguments "
        "for the demo.",
        file=sys.stderr,
    )
    raise SystemExit(2)


if __name__ == "__main__":
    run_demo()
