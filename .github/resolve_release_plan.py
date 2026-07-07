#!/usr/bin/env python3
"""Resolve CI pipeline mode and PyPI release eligibility for xnano packages."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


_PACKAGE_VERSION = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)
_PINNED_CORE_VERSION = re.compile(r'"xnano-core==([^"]+)"')
_TAG_PATTERN = re.compile(
    r"^refs/tags/(xnano-core|xnano)/v?(.+)$",
    re.IGNORECASE,
)


def read_repo_version(path: Path, label: str) -> str:
    """Read a ``version = "..."`` field from a manifest file."""
    if not path.is_file():
        raise RuntimeError(f'Could not read {label}: "{path}" does not exist.')

    match = _PACKAGE_VERSION.search(path.read_text(encoding="utf-8"))
    if match is None:
        raise RuntimeError(f"Could not find version in {label} ({path}).")

    return match.group(1)


def read_pinned_core_version(pyproject_path: Path) -> str:
    """Read the pinned ``xnano-core`` dependency from ``pyproject.toml``."""
    match = _PINNED_CORE_VERSION.search(
        pyproject_path.read_text(encoding="utf-8")
    )
    if match is None:
        raise RuntimeError("Could not find xnano-core pin in pyproject.toml.")
    return match.group(1)


def normalize_tag_version(version: str) -> str:
    """Normalize git tag versions to manifest-style PEP 440 strings."""
    version = version.lower()
    return version.replace("a", "-alpha").replace("b", "-beta")


def parse_release_tag(ref: str) -> tuple[str, str] | None:
    """Parse ``refs/tags/<package>/v<version>`` release tags."""
    match = _TAG_PATTERN.match(ref)
    if match is None:
        return None
    package = match.group(1).lower()
    version = normalize_tag_version(match.group(2))
    return package, version


def fetch_pypi_latest(package: str) -> str | None:
    """Return the latest published version for ``package``, if any."""
    url = f"https://pypi.org/pypi/{package}/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError:
        return None
    return payload.get("info", {}).get("version")


def fetch_pypi_has_version(package: str, version: str) -> bool:
    """Return whether an exact ``version`` of ``package`` exists on PyPI."""
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            response.read(1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return False
        raise
    return True


def write_github_output(name: str, value: str | bool) -> None:
    """Append a single-line value to ``GITHUB_OUTPUT`` when present."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def resolve_plan(
    github_ref: str,
    event_name: str,
    full_build_label: bool,
) -> dict[str, str | bool]:
    """Compute workflow routing and publish decisions for the current event."""
    repo_root = Path.cwd()
    manifest_xnano = read_repo_version(repo_root / "pyproject.toml", "xnano")
    manifest_core = read_repo_version(
        repo_root / "xnano-core" / "Cargo.toml",
        "xnano-core",
    )
    pinned_core = read_pinned_core_version(repo_root / "pyproject.toml")

    if manifest_core != pinned_core:
        raise RuntimeError(
            "xnano-core version mismatch: "
            f"Cargo.toml has {manifest_core}, pyproject.toml pins {pinned_core}."
        )

    parsed_tag = parse_release_tag(github_ref)
    tag_package = parsed_tag[0] if parsed_tag else ""
    tag_version = parsed_tag[1] if parsed_tag else ""

    pypi_xnano_latest = fetch_pypi_latest("xnano") or ""
    pypi_core_latest = fetch_pypi_latest("xnano-core") or ""
    pinned_core_on_pypi = fetch_pypi_has_version("xnano-core", pinned_core)

    is_core_tag = tag_package == "xnano-core"
    is_xnano_tag = tag_package == "xnano"
    is_pull_request = event_name == "pull_request"

    if is_core_tag and tag_version != manifest_core:
        raise RuntimeError(
            f'xnano-core tag "{tag_version}" does not match '
            f'Cargo.toml version "{manifest_core}".'
        )

    if is_xnano_tag and tag_version != manifest_xnano:
        raise RuntimeError(
            f'xnano tag "{tag_version}" does not match '
            f'pyproject.toml version "{manifest_xnano}".'
        )

    if is_xnano_tag and not pinned_core_on_pypi:
        raise RuntimeError(
            f"xnano tag workflow requires xnano-core=={pinned_core} on PyPI, "
            "but that exact version is not published yet. "
            f"Push and release xnano-core/v{pinned_core} first."
        )

    tag_core_on_pypi = (
        fetch_pypi_has_version("xnano-core", tag_version)
        if is_core_tag
        else False
    )
    tag_xnano_on_pypi = (
        fetch_pypi_has_version("xnano", tag_version) if is_xnano_tag else False
    )

    manifest_core_on_pypi = fetch_pypi_has_version("xnano-core", manifest_core)
    manifest_xnano_on_pypi = fetch_pypi_has_version("xnano", manifest_xnano)
    versions_unchanged = manifest_core_on_pypi and manifest_xnano_on_pypi

    has_release_tag = is_core_tag or is_xnano_tag
    tag_already_published = (
        (is_core_tag and tag_core_on_pypi)
        or (is_xnano_tag and tag_xnano_on_pypi)
    )

    if tag_already_published:
        run_workflow = False
    elif has_release_tag:
        run_workflow = True
    elif is_pull_request and (full_build_label or not versions_unchanged):
        run_workflow = True
    else:
        # Plain main pushes and PRs with unchanged published versions skip CI.
        run_workflow = False

    run_tests = run_workflow
    run_core_pipeline = run_workflow and (
        is_core_tag or (is_pull_request and full_build_label)
    )
    run_xnano_pipeline = run_workflow and (
        (is_xnano_tag and pinned_core_on_pypi)
        or (is_pull_request and full_build_label)
    )

    use_workspace_core = not is_xnano_tag
    use_pypi_core = is_xnano_tag

    should_publish_core = (
        run_workflow
        and is_core_tag
        and not tag_core_on_pypi
        and tag_version == manifest_core
    )
    should_publish_xnano = (
        run_workflow
        and is_xnano_tag
        and pinned_core_on_pypi
        and not tag_xnano_on_pypi
        and tag_version == manifest_xnano
    )

    return {
        "event_name": event_name,
        "github_ref": github_ref,
        "tag_package": tag_package,
        "tag_version": tag_version,
        "manifest_xnano_version": manifest_xnano,
        "manifest_core_version": manifest_core,
        "pinned_core_version": pinned_core,
        "pypi_xnano_latest": pypi_xnano_latest,
        "pypi_core_latest": pypi_core_latest,
        "pinned_core_on_pypi": pinned_core_on_pypi,
        "manifest_core_on_pypi": manifest_core_on_pypi,
        "manifest_xnano_on_pypi": manifest_xnano_on_pypi,
        "versions_unchanged": versions_unchanged,
        "tag_core_on_pypi": tag_core_on_pypi,
        "tag_xnano_on_pypi": tag_xnano_on_pypi,
        "run_workflow": run_workflow,
        "run_tests": run_tests,
        "run_core_pipeline": run_core_pipeline,
        "run_xnano_pipeline": run_xnano_pipeline,
        "use_workspace_core": use_workspace_core,
        "use_pypi_core": use_pypi_core,
        "should_publish_core": should_publish_core,
        "should_publish_xnano": should_publish_xnano,
    }


def print_plan_summary(plan: dict[str, str | bool]) -> None:
    """Print a human-readable release plan summary."""
    print("Release plan:")
    for key, value in plan.items():
        print(f"  {key}={value}")


def main() -> int:
    """Entry point for GitHub Actions and local debugging."""
    github_ref = os.environ.get("GITHUB_REF", "")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    full_build_label = (
        os.environ.get("FULL_BUILD_LABEL", "false").lower() == "true"
    )

    try:
        plan = resolve_plan(github_ref, event_name, full_build_label)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print_plan_summary(plan)

    for key, value in plan.items():
        if isinstance(value, bool):
            write_github_output(key, str(value).lower())
        else:
            write_github_output(key, value)

    return 0


if __name__ == "__main__":
    sys.exit(main())
