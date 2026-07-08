"""xnano.__main__

Entry point for ``python -m xnano`` and the ``xnano`` console script.
Launches the interactive framework showcase.
"""

from __future__ import annotations


def main() -> None:
    """Run the ``xnano`` demo application."""
    from xnano.beta.core import run_demo

    run_demo()


if __name__ == "__main__":
    main()
