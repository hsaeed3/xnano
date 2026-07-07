#!/usr/bin/env python3
"""Print the pinned ``xnano-core`` version from the root ``pyproject.toml``."""

import re
import sys
from pathlib import Path


_PINNED_CORE_VERSION = re.compile(r"""["']xnano-core==([^"']+)["']""")


def main() -> int:
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.is_file():
        print("✖ pyproject.toml not found", file=sys.stderr)
        return 1

    match = _PINNED_CORE_VERSION.search(pyproject_path.read_text())
    if match is None:
        print("✖ xnano-core pin not found in pyproject.toml", file=sys.stderr)
        return 1

    print(match.group(1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
