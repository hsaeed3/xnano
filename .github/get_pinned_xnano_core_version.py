#!/usr/bin/env python3
"""Print the pinned ``xnano-core`` version from the root ``pyproject.toml``."""

import sys
import tomllib
from pathlib import Path


def main() -> int:
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.is_file():
        print("✖ pyproject.toml not found", file=sys.stderr)
        return 1

    data = tomllib.loads(pyproject_path.read_text())
    for dependency in data["project"]["dependencies"]:
        if dependency.startswith("xnano-core=="):
            print(dependency.removeprefix("xnano-core=="))
            return 0

    print("✖ xnano-core pin not found in pyproject.toml", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())