"""
xnano.__main__

The ``xnano`` command, and ``python -m xnano``.

Without an argument it runs the feature demo. With the path of a file it shows the file:
``xnano README.md``, ``xnano data.json``, ``xnano photo.png``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import get_args

from xnano.themes import ThemeName

__all__ = ['main']


def _parser() -> argparse.ArgumentParser:
    """The parser of the words after ``xnano`` on the command line."""
    parser = argparse.ArgumentParser(
        prog='xnano',
        description=(
            'Without a file, run the xnano demo. With a file, show it: Markdown, text, '
            'JSON, a table, a PDF, a picture or a sound.'
        ),
        epilog=(
            'On a terminal the file opens in a viewer: scroll with the arrow keys, the '
            'wheel or a drag, find text with /, and leave with q. Without a terminal '
            '(a pipe, a file) the document is printed.'
        ),
    )
    parser.add_argument('file', nargs='?', help='the file to show')
    parser.add_argument(
        '-p',
        '--print',
        action='store_true',
        dest='should_print',
        help='print the document and leave, also on a terminal',
    )
    parser.add_argument(
        '-w',
        '--width',
        type=int,
        metavar='CELLS',
        help='the width of the printed document (the width of the terminal by default)',
    )
    parser.add_argument(
        '-t',
        '--theme',
        choices=get_args(ThemeName),
        metavar='NAME',
        help=(
            'the colors of the document (the colors of the terminal by default): '
            + ', '.join(get_args(ThemeName))
        ),
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """
    Run the ``xnano`` command.

    Args:
        arguments: The words after ``xnano`` on the command line. By default the ones that
            the program was started with.

    Returns:
        ``0`` when the command worked, and ``1`` when the file could not be shown.
    """
    options = _parser().parse_args(arguments)
    if options.file is None:
        from xnano.demo import main as run_demo

        run_demo()
        return 0
    from xnano.reader import view

    try:
        view(
            options.file,
            interactive=False if options.should_print else None,
            width=options.width,
            theme=options.theme,
        )
    except BrokenPipeError:
        return 0
    except (OSError, ImportError) as error:
        sys.stderr.write(f'xnano: {error}\n')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
