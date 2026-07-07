#!/usr/bin/env python3
"""Check package versions match the git tag that triggered the release."""

import os
import re
import sys
from pathlib import Path


PackageConfig = dict[str, Path | str]

PACKAGES: dict[str, PackageConfig] = {
    "xnano-core": {
        "path": Path("xnano-core/Cargo.toml"),
        "pattern": r"""^version ?= ?(["'])(.+)\1""",
    },
    "xnano": {
        "path": Path("pyproject.toml"),
        "pattern": r"""^version ?= ?(["'])(.+)\1""",
    },
}


def parse_release_tag(ref: str) -> tuple[str, str] | None:
    """Parse ``refs/tags/<package>/v<version>`` release tags."""
    match = re.match(
        r"^refs/tags/(xnano-core|xnano)/v?(.+)$",
        ref,
        re.IGNORECASE,
    )
    if match is None:
        return None

    package = match.group(1).lower()
    version = match.group(2).lower()
    version = version.replace("a", "-alpha").replace("b", "-beta")
    return package, version


def get_declared_version(package: str) -> str | None:
    """Return the version declared in the package manifest."""
    config = PACKAGES[package]
    path = config["path"]
    if not path.is_file():
        print(f'✖ path "{path}" does not exist')
        return None

    content = path.read_text()
    version_regex = re.compile(str(config["pattern"]), re.M)
    match = version_regex.search(content)
    if match is None:
        print(f"✖ version not found in {path}")
        return None

    return match.group(2)


def main() -> int:
    version_ref = os.getenv("GITHUB_REF")
    if not version_ref:
        print('✖ "GITHUB_REF" environment variable not found')
        return 1

    parsed = parse_release_tag(version_ref)
    if parsed is None:
        print(f'✖ "{version_ref}" is not a supported release tag')
        print('  expected: refs/tags/xnano-core/v<version> or refs/tags/xnano/v<version>')
        return 1

    package, tag_version = parsed
    if package not in PACKAGES:
        print(f'✖ unknown package "{package}"')
        return 1

    declared_version = get_declared_version(package)
    if declared_version is None:
        return 1

    if declared_version == tag_version:
        print(
            f'✓ tag version "{tag_version}" matches '
            f'{PACKAGES[package]["path"]} version "{declared_version}"'
        )
        return 0

    print(
        f'✖ tag version "{tag_version}" does not match '
        f'{PACKAGES[package]["path"]} version "{declared_version}"'
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())