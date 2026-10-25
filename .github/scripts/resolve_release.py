# /// script
# requires-python = ">=3.11"
# dependencies = ["packaging>=24.0"]
# ///
"""
Decide what the CI workflow builds and whether it may publish a release.

Run from the repository root by the ``plan`` job of ``.github/workflows/ci.yml``.
Writes its decisions to ``GITHUB_OUTPUT`` and prints them for the job log.

Release tags look like ``<package>/v<version>`` and trigger a release of
exactly one package: ``xnano``, ``xnano-core``, ``xnano-audio`` or
``xnano-image``. Versions are compared as PEP 440 versions, so the tag
``xnano-core/v1.0.0-beta.1`` matches the Cargo version ``1.0.0-beta.1`` and
the published version ``1.0.0b1``.

The ``xnano`` version is the workspace version in ``Cargo.toml``; the version of every
other package is the version of its binding crate under ``crates/``.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import tomllib
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

# Each distribution and the Cargo manifest of the binding crate that sets its version.
CORE_CRATE_MANIFESTS = {
    "xnano-core": Path("crates/xnano-terminal-core/Cargo.toml"),
    "xnano-audio": Path("crates/xnano-terminal-audio/Cargo.toml"),
    "xnano-image": Path("crates/xnano-terminal-image/Cargo.toml"),
}
CORE_PACKAGES = tuple(CORE_CRATE_MANIFESTS)
ALL_PACKAGES = ("xnano", *CORE_PACKAGES)

# The `xnano` metapackage version is the workspace version; `crates/xnano-terminal-runtime/build.rs`
# copies it, and the pins on the other distributions, into the root `pyproject.toml`.
WORKSPACE_MANIFEST = Path("Cargo.toml")
TAG_PATTERN = re.compile(r"^refs/tags/(" + "|".join(ALL_PACKAGES) + r")/v?(.+)$")


class ReleasePlanError(Exception):
    """A problem the person preparing the release can fix."""


def parse_version(text: str, source: str) -> Version:
    """Parse a version and explain which source supplied an invalid value."""
    try:
        return Version(text)
    except InvalidVersion as error:
        raise ReleasePlanError(
            f'The version "{text}" from {source} is not a valid PEP 440 version. '
            'Use a version such as "1.0.0", "1.0.0b1" or "1.0.0-beta.1".'
        ) from error


def read_declared_version(package: str) -> Version:
    """Read the version a package declares in its source tree."""
    if package == "xnano":
        path = WORKSPACE_MANIFEST
        key = "workspace"
    else:
        path = CORE_CRATE_MANIFESTS[package]
        key = None
    if not path.is_file():
        raise ReleasePlanError(
            f'Could not read the {package} version: "{path}" does not exist.'
        )
    cargo = tomllib.loads(path.read_text(encoding="utf-8"))
    table = cargo["workspace"]["package"] if key else cargo["package"]
    return parse_version(table["version"], str(path))


def read_root_requirements() -> dict[str, Requirement]:
    """
    Read the distribution pins from the root ``pyproject.toml``.

    ``xnano-core`` is a dependency; ``xnano-audio`` and ``xnano-image`` are the pins of
    the ``audio`` and ``image`` extras, so every optional group is read too.
    """
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    requirements = [Requirement(text) for text in project.get("dependencies", [])]
    for group in project.get("optional-dependencies", {}).values():
        requirements.extend(Requirement(text) for text in group)
    return {
        canonicalize_name(requirement.name): requirement for requirement in requirements
    }


def is_published(package: str, version: Version) -> bool:
    """Return whether this exact version of ``package`` exists on PyPI."""
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            response.read(1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return False
        raise
    return True


def resolve_release(package: str, tag_version: str) -> dict[str, str]:
    """Validate a release tag against the source tree and PyPI."""
    declared = read_declared_version(package)
    if parse_version(tag_version, "the release tag") != declared:
        raise ReleasePlanError(
            f'The tag version "{tag_version}" does not match the {package} version "{declared}" '
            "declared in the source tree. Bump the version, or push a tag that matches it."
        )

    if package == "xnano":
        requirements = read_root_requirements()
        for core_package in CORE_PACKAGES:
            requirement = requirements.get(core_package)
            version = read_declared_version(core_package)
            if requirement is None:
                raise ReleasePlanError(
                    f"pyproject.toml does not require {core_package} as a dependency or an extra. Build the workspace so "
                    "crates/xnano-terminal-runtime/build.rs rewrites the pins, then commit the result."
                )
            if not requirement.specifier.contains(version, prereleases=True):
                raise ReleasePlanError(
                    f"pyproject.toml requires {requirement} but {core_package} is at {version}. "
                    "Build the workspace so build.rs rewrites the pins, then commit the result."
                )
            if not is_published(core_package, version):
                raise ReleasePlanError(
                    f"xnano requires {core_package} {version} on PyPI, but that version is not "
                    f'published. Release it first by pushing the tag "{core_package}/v{version}".'
                )

    return {
        "release": "true",
        "package": package,
        "version": str(declared),
        "is_prerelease": str(declared.is_prerelease).lower(),
        "already_published": str(is_published(package, declared)).lower(),
    }


def resolve_plan(
    ref: str, event_name: str, has_full_build_label: bool
) -> dict[str, str]:
    """Select build and release jobs for a GitHub ref and event."""
    tag = TAG_PATTERN.match(ref)
    is_main_push = event_name == "push" and ref == "refs/heads/main"

    plan = {
        "release": "false",
        "package": "",
        "version": "",
        "is_prerelease": "false",
        "already_published": "false",
        # Wheel, wasm and distribution builds are slow, so pull requests opt in
        # with the "full build" label. Main and release tags always run them.
        "full_build": str(
            tag is not None or is_main_push or has_full_build_label
        ).lower(),
        # A release tag builds only the package it releases.
        "core_packages": json.dumps(list(CORE_PACKAGES)),
        "build_xnano": "true",
    }

    if tag is None:
        if ref.startswith("refs/tags/"):
            raise ReleasePlanError(
                f'The tag "{ref}" is not a release tag. Release tags look like '
                f'"<package>/v<version>", where <package> is one of: {", ".join(ALL_PACKAGES)}.'
            )
        return plan

    package, tag_version = tag.groups()
    plan.update(resolve_release(package, tag_version))
    plan["core_packages"] = json.dumps([package] if package in CORE_PACKAGES else [])
    plan["build_xnano"] = str(package == "xnano").lower()
    return plan


def main() -> int:
    """Read the GitHub event context and emit the resolved plan."""
    ref = os.environ.get("GITHUB_REF", "")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    has_full_build_label = (
        os.environ.get("HAS_FULL_BUILD_LABEL", "false").lower() == "true"
    )

    try:
        plan = resolve_plan(ref, event_name, has_full_build_label)
    except ReleasePlanError as error:
        sys.stderr.write(f"::error::{error}\n")
        return 1

    for name, value in plan.items():
        sys.stdout.write(f"{name}={value}\n")

    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as output:
            for name, value in plan.items():
                output.write(f"{name}={value}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
