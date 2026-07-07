#!/usr/bin/env python3
"""Fail when an exact package version is already published on PyPI."""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: confirm_not_on_pypi.py <package-name>", file=sys.stderr)
        return 1

    package = sys.argv[1]
    version = os.environ.get("TAG_VERSION", "")
    if not version:
        print("TAG_VERSION environment variable is required.", file=sys.stderr)
        return 1

    url = f"https://pypi.org/pypi/{package}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            response.read(1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            print(f"✓ {package} {version} is not on PyPI yet.")
            return 0
        raise

    print(f"✖ {package} {version} is already on PyPI.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())