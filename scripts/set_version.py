#!/usr/bin/env python3
"""
Bump a workspace package and synchronize generated version pins.

The Rust workspace manifests are authoritative. ``xnano`` and ``xnano-core`` share the
workspace version; audio and image use their binding-crate versions. This script updates
the root metapackage metadata in the same way as the runtime build script.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_MANIFEST = ROOT / "Cargo.toml"
ROOT_PYPROJECT = ROOT / "pyproject.toml"
DOCS_DIR = ROOT / "docs"
CRATES = {
    "xnano-core": ROOT / "crates/xnano-terminal-core/Cargo.toml",
    "xnano-audio": ROOT / "crates/xnano-terminal-audio/Cargo.toml",
    "xnano-image": ROOT / "crates/xnano-terminal-image/Cargo.toml",
}
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?$")
MARKDOWN_PIN_RE = re.compile(r"(?P<quote>['\"])xnano>=[^'\"]+(?P=quote)")
AUTO_START = "# [! AUTO-VERSIONING - DO NOT EDIT THIS BY HAND]"
AUTO_END = "# [! END AUTO-VERSIONING]"


class VersionError(ValueError):
    """A package version or generated version pin is invalid."""


def pep440(version: str) -> str:
    """Convert supported Cargo prerelease versions to their Python spelling."""
    release, separator, pre = version.partition("-")
    if not separator:
        return release
    label, _, number = pre.partition(".")
    suffix = {"alpha": "a", "beta": "b", "rc": "rc"}.get(label)
    if suffix is None or not number.isdigit():
        raise VersionError(f"Unsupported Cargo prerelease version: {version}")
    return f"{release}{suffix}{number}"


def pin_specifier(version: str) -> str:
    """Match the range policy used by ``crates/xnano-terminal-runtime/build.rs``."""
    python_version = pep440(version)
    major, minor, _patch = (int(part) for part in version.split("-", 1)[0].split("."))
    if major == 0:
        return f">={python_version},<0.{minor + 1}"
    return f">={python_version}"


def package_manifests() -> dict[str, Path]:
    """Map each distribution name to its authoritative Cargo manifest."""
    return {"xnano": WORKSPACE_MANIFEST, **CRATES}


def read_version(path: Path, package: str) -> str:
    """Read a package version from its Cargo table."""
    content = path.read_text(encoding="utf-8")
    section = "workspace.package" if package == "xnano" else "package"
    in_section = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = stripped[1:-1] == section
        elif in_section and (
            match := re.fullmatch(r'version\s*=\s*"([^"]+)"', stripped)
        ):
            return match.group(1)
    raise VersionError(
        f"Could not find [{section}].version in {path.relative_to(ROOT)}"
    )


def replace_version(path: Path, package: str, version: str) -> str:
    """Replace the version in the selected Cargo table, leaving other tables intact."""
    section = "workspace.package" if package == "xnano" else "package"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    in_section = False
    replaced = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = stripped[1:-1] == section
        elif in_section and re.match(r"^\s*version\s*=", line):
            ending = "\n" if line.endswith("\n") else ""
            indent = line[: len(line) - len(line.lstrip())]
            lines[index] = f'{indent}version = "{version}"{ending}'
            replaced = True
            break
    if not replaced:
        raise VersionError(
            f"Could not find [{section}].version in {path.relative_to(ROOT)}"
        )
    return "".join(lines)


def build_pyproject(xnano_version: str, versions: dict[str, str]) -> str:
    """Regenerate the root project's marked version block."""
    original = ROOT_PYPROJECT.read_text(encoding="utf-8")
    output: list[str] = []
    inside = False
    dependencies = False
    wrote_dependencies = False
    pins = [
        f'    "{name}{pin_specifier(version)}",' for name, version in versions.items()
    ]
    for line in original.splitlines(keepends=True):
        stripped = line.strip()
        if AUTO_START in line:
            inside = True
            output.append(line)
            continue
        if AUTO_END in line:
            inside = False
        if inside and re.match(r"^\s*version\s*=", line):
            output.append(f"version = '{pep440(xnano_version)}'\n")
        elif inside and re.match(r"^\s*dependencies\s*=\s*\[", line):
            output.append("dependencies = [\n")
            output.extend(f"{pin}\n" for pin in pins)
            dependencies = True
            wrote_dependencies = True
        elif dependencies:
            if stripped == "]":
                output.append("]\n")
                dependencies = False
        else:
            output.append(line)
    if not wrote_dependencies or dependencies or inside:
        raise VersionError("Root pyproject.toml has malformed AUTO-VERSIONING markers.")
    return "".join(output)


def expected_pyproject() -> str:
    """Return the root pyproject with generated versions from Cargo manifests."""
    versions = {name: read_version(path, name) for name, path in CRATES.items()}
    xnano_version = read_version(WORKSPACE_MANIFEST, "xnano")
    if versions["xnano-core"] != xnano_version:
        raise VersionError(
            "xnano and xnano-core must share a version; update both Cargo manifests."
        )
    return build_pyproject(xnano_version, versions)


def markdown_pin_paths() -> list[Path]:
    """Return README/docs Markdown files containing an xnano install pin."""
    candidates = [ROOT / "README.md", *DOCS_DIR.rglob("*.md")]
    return [
        path
        for path in candidates
        if path.is_file() and MARKDOWN_PIN_RE.search(path.read_text(encoding="utf-8"))
    ]


def synchronize_markdown_pins(version: str, *, check: bool) -> list[Path]:
    """Update or validate versioned xnano install examples in Markdown."""
    changed: list[Path] = []
    pin = f"xnano>={pep440(version)}"
    for path in markdown_pin_paths():
        original = path.read_text(encoding="utf-8")
        updated = MARKDOWN_PIN_RE.sub(
            lambda match: f"{match['quote']}{pin}{match['quote']}", original
        )
        if original == updated:
            continue
        if check:
            raise VersionError(
                f"{path.relative_to(ROOT)} contains an outdated xnano install pin; "
                "run scripts/set_version.py xnano <version>."
            )
        path.write_text(updated, encoding="utf-8")
        changed.append(path)
    return changed


def bump(package: str, version: str, *, update_locks: bool) -> None:
    """Update one authoritative version and regenerate root pins and lockfiles."""
    if not VERSION_RE.fullmatch(version):
        raise VersionError(
            "Use a Cargo version like 1.2.3, 1.2.3-beta.1 or 1.2.3-rc.1."
        )
    if package in {"xnano", "xnano-core"}:
        for shared_package in ("xnano", "xnano-core"):
            manifest = package_manifests()[shared_package]
            content = replace_version(manifest, shared_package, version)
            manifest.write_text(content, encoding="utf-8")
    else:
        manifest = package_manifests()[package]
        content = replace_version(manifest, package, version)
        manifest.write_text(content, encoding="utf-8")
    ROOT_PYPROJECT.write_text(expected_pyproject(), encoding="utf-8")
    if package in {"xnano", "xnano-core"}:
        synchronize_markdown_pins(version, check=False)
    if update_locks:
        subprocess.run(["cargo", "update", "--workspace"], cwd=ROOT, check=True)
        subprocess.run(["uv", "lock", "--offline"], cwd=ROOT, check=True)


def main(argv: list[str] | None = None) -> int:
    """Run the version bump or generated-version consistency check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "package",
        nargs="?",
        choices=tuple(package_manifests()),
        help="package to bump; omit with --check to validate the whole workspace",
    )
    parser.add_argument("version", nargs="?", help="new Cargo-style package version")
    parser.add_argument(
        "--check", action="store_true", help="check generated root version pins"
    )
    parser.add_argument(
        "--no-lock", action="store_true", help="do not update Cargo.lock and uv.lock"
    )
    args = parser.parse_args(argv)
    try:
        if args.check:
            if args.version is not None:
                parser.error("--check cannot be combined with a version")
            expected = expected_pyproject()
            actual = ROOT_PYPROJECT.read_text(encoding="utf-8")
            if actual != expected:
                raise VersionError(
                    "Generated version values in pyproject.toml are out of date."
                )
            synchronize_markdown_pins(
                read_version(WORKSPACE_MANIFEST, "xnano"), check=True
            )
            sys.stdout.write(
                "Cargo versions and generated root pins are synchronized.\n"
            )
            return 0
        if args.package is None:
            parser.error("a package and version are required unless --check is used")
        if args.version is None:
            parser.error("a version is required unless --check is used")
        bump(args.package, args.version, update_locks=not args.no_lock)
        sys.stdout.write(f"Updated {args.package} to {args.version}.\n")
        return 0
    except (OSError, subprocess.CalledProcessError, VersionError) as error:
        sys.stderr.write(f"error: {error}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
