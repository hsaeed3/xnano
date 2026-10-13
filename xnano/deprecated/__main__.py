"""
xnano.deprecated.__main__

Entrypoint for ``python -m xnano.deprecated`` and the installed ``xnano`` script.

- no args → feature demo
- path to a Markdown file → document runner
- ``--help`` → short usage
"""

from __future__ import annotations

import sys

USAGE = """Usage: xnano [PATH.md]

  (no arguments)  open the feature demo
  PATH.md         open a Markdown document
  -h, --help      show this message
"""


def run_demo() -> None:
    """Dispatch the installed ``xnano`` entrypoint."""
    arguments = sys.argv[1:]
    if not arguments:
        from xnano.deprecated.core.demo import run_demo as _run_feature_demo

        _run_feature_demo()
        return

    if arguments[0] in {'-h', '--help', 'help'}:
        sys.stdout.write(USAGE)
        return

    path = arguments[0]
    from xnano.deprecated.markdown import is_markdown_path, run_markdown

    if is_markdown_path(path):
        run_markdown(path)
        return

    sys.stderr.write(
        f'xnano: unknown input {path!r}; pass a Markdown file (.md) or no '
        f'arguments for the demo\n\n{USAGE}'
    )
    raise SystemExit(2)


if __name__ == '__main__':
    run_demo()
