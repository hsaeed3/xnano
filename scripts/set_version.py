"""scripts.set_version

---

Synchronize ``xnano`` and ``xnano-core`` version strings across the whitelisted
release files in this repository.

Authoritative sources:

- ``xnano``: ``pyproject.toml`` ``[project].version``
- ``xnano-core``: ``xnano-core/Cargo.toml`` ``[package].version``

When only one package is bumped, every file that references the other package
is reconciled so pins and compatibility checks stay aligned.
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import re
import subprocess
import sys


DEFAULT_XNANO_VERSION = "0.99.9"
"""Default ``xnano`` version when the package is named without an explicit value."""

DEFAULT_XNANO_CORE_VERSION = "0.0.2"
"""Default ``xnano-core`` version when the package is named without an explicit value."""

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

EDITABLE_FILES: tuple[str, ...] = (
    "pyproject.toml",
    "xnano-core/Cargo.toml",
    "xnano/beta/core/version.py",
    "README.md",
)
"""Paths this script is allowed to modify, relative to the repository root."""

VERSION_PATTERN = re.compile(
    r"^v?(\d+\.\d+\.\d+(?:[a-zA-Z]+\d+)?)$"
)
"""PEP 440-style release versions accepted by this script."""

_XNANO_PROJECT_VERSION = re.compile(
    r'^version = "([^"]+)"$',
    re.MULTILINE,
)
_XNANO_CORE_PIN = re.compile(r'"xnano-core==([^"]+)"')
_CARGO_PACKAGE_VERSION = re.compile(
    r'^version = "([^"]+)"$',
    re.MULTILINE,
)
_VERSION_PY_XNANO = re.compile(r'^VERSION = "(?P<version>[^"]+)"$', re.MULTILINE)
_VERSION_PY_CORE = re.compile(
    r'^_COMPATIBLE_XNANO_CORE_VERSION = "(?P<version>[^"]+)"$',
    re.MULTILINE,
)
_README_MIN_VERSION = re.compile(r"``(\d+\.\d+\.\d+)``\+ version")
_README_PIP_INSTALL = re.compile(r'pip install "xnano>=(\d+\.\d+\.\d+)"')
_README_UV_ADD = re.compile(r'uv add "xnano>=(\d+\.\d+\.\d+)"')


@dataclasses.dataclass(frozen=True)
class VersionState:
    """Resolved package versions used for synchronization."""

    xnano: str
    """The ``xnano`` package version."""
    xnano_core: str
    """The ``xnano-core`` package version."""


class VersionSyncError(RuntimeError):
    """Raised when version files cannot be read, validated, or updated safely."""


def validate_version_string(version: str, label: str) -> str:
    """Validate a version string before writing it to disk.

    Args:
        version: Candidate version value.
        label: Human-readable field name for error messages.

    Returns:
        The validated version string.

    Raises:
        VersionSyncError: If ``version`` is not a supported release string.
    """
    if not VERSION_PATTERN.fullmatch(version):
        message = (
            f'Invalid {label} version "{version}". '
            "Expected a PEP 440-style value like 0.99.9 or 1.0.0b1."
        )
        raise VersionSyncError(message)
    return version


def read_text_file(relative_path: str) -> str:
    """Read a whitelisted repository file as text.

    Args:
        relative_path: Path relative to the repository root.

    Returns:
        The file contents.

    Raises:
        VersionSyncError: If the path is not editable or cannot be read.
    """
    ensure_editable_path(relative_path)
    path = REPO_ROOT / relative_path
    if not path.is_file():
        raise VersionSyncError(f'Editable file "{relative_path}" does not exist.')
    return path.read_text(encoding="utf-8")


def write_text_file(relative_path: str, content: str) -> bool:
    """Write a whitelisted repository file when content changed.

    Args:
        relative_path: Path relative to the repository root.
        content: Replacement file contents.

    Returns:
        ``True`` when the file was updated.

    Raises:
        VersionSyncError: If the path is not editable.
    """
    ensure_editable_path(relative_path)
    path = REPO_ROOT / relative_path
    original = path.read_text(encoding="utf-8") if path.is_file() else ""
    if original == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def ensure_editable_path(relative_path: str) -> None:
    """Ensure a path is on the edit whitelist.

    Args:
        relative_path: Path relative to the repository root.

    Raises:
        VersionSyncError: If editing the path is not allowed.
    """
    if relative_path not in EDITABLE_FILES:
        message = (
            f'Refusing to edit "{relative_path}". '
            f"Allowed paths: {', '.join(EDITABLE_FILES)}"
        )
        raise VersionSyncError(message)


def extract_first_match(
    pattern: re.Pattern[str],
    content: str,
    label: str,
) -> str:
    """Extract the first regex match from ``content``.

    Args:
        pattern: Compiled regular expression with one capture group.
        content: File contents to search.
        label: Human-readable label used in error messages.

    Returns:
        The first captured value.

    Raises:
        VersionSyncError: If no match is found.
    """
    match = pattern.search(content)
    if match is None:
        raise VersionSyncError(f'Could not find {label} in repository files.')
    return match.group(1)


def read_version_state() -> VersionState:
    """Read authoritative versions from package manifests.

    Returns:
        The versions declared in ``pyproject.toml`` and ``Cargo.toml``.
    """
    pyproject = read_text_file("pyproject.toml")
    cargo = read_text_file("xnano-core/Cargo.toml")

    xnano = extract_first_match(
        _XNANO_PROJECT_VERSION,
        pyproject,
        "xnano project version",
    )
    xnano_core = extract_first_match(
        _CARGO_PACKAGE_VERSION,
        cargo,
        "xnano-core Cargo package version",
    )

    return VersionState(
        xnano=validate_version_string(xnano, "xnano"),
        xnano_core=validate_version_string(xnano_core, "xnano-core"),
    )


def apply_single_replacement(
    content: str,
    pattern: re.Pattern[str],
    replacement: str,
    label: str,
) -> tuple[str, int]:
    """Replace exactly one pattern occurrence in ``content``.

    Args:
        content: Original file contents.
        pattern: Regular expression to replace.
        replacement: Replacement string or template.
        label: Human-readable label used in error messages.

    Returns:
        A tuple of updated content and replacement count.

    Raises:
        VersionSyncError: If zero or multiple replacements would occur.
    """
    updated, count = pattern.subn(replacement, content, count=1)
    if count != 1:
        message = (
            f'Expected exactly one replacement for {label}, found {count}.'
        )
        raise VersionSyncError(message)
    return updated, count


def sync_pyproject_toml(state: VersionState) -> bool:
    """Synchronize the root ``pyproject.toml`` version fields.

    Args:
        state: Target versions to write.

    Returns:
        ``True`` when the file changed.
    """
    content = read_text_file("pyproject.toml")

    content, _ = apply_single_replacement(
        content,
        _XNANO_PROJECT_VERSION,
        f'version = "{state.xnano}"',
        "xnano project version",
    )
    content, _ = apply_single_replacement(
        content,
        _XNANO_CORE_PIN,
        f'"xnano-core=={state.xnano_core}"',
        "xnano-core dependency pin",
    )

    return write_text_file("pyproject.toml", content)


def sync_cargo_toml(state: VersionState) -> bool:
    """Synchronize ``xnano-core/Cargo.toml``.

    Args:
        state: Target versions to write.

    Returns:
        ``True`` when the file changed.
    """
    content = read_text_file("xnano-core/Cargo.toml")
    content, _ = apply_single_replacement(
        content,
        _CARGO_PACKAGE_VERSION,
        f'version = "{state.xnano_core}"',
        "xnano-core Cargo package version",
    )
    return write_text_file("xnano-core/Cargo.toml", content)


def sync_version_module(state: VersionState) -> bool:
    """Synchronize ``xnano/beta/core/version.py``.

    Args:
        state: Target versions to write.

    Returns:
        ``True`` when the file changed.
    """
    content = read_text_file("xnano/beta/core/version.py")

    content, _ = apply_single_replacement(
        content,
        _VERSION_PY_XNANO,
        f'VERSION = "{state.xnano}"',
        "xnano VERSION constant",
    )
    content, _ = apply_single_replacement(
        content,
        _VERSION_PY_CORE,
        f'_COMPATIBLE_XNANO_CORE_VERSION = "{state.xnano_core}"',
        "xnano-core compatibility constant",
    )

    return write_text_file("xnano/beta/core/version.py", content)


def sync_readme(state: VersionState) -> bool:
    """Synchronize install examples in ``README.md``.

    Args:
        state: Target versions to write.

    Returns:
        ``True`` when the file changed.
    """
    content = read_text_file("README.md")

    content, _ = apply_single_replacement(
        content,
        _README_MIN_VERSION,
        f"``{state.xnano}``+ version",
        "README minimum version warning",
    )
    content, _ = apply_single_replacement(
        content,
        _README_PIP_INSTALL,
        f'pip install "xnano>={state.xnano}"',
        "README pip install example",
    )
    content, _ = apply_single_replacement(
        content,
        _README_UV_ADD,
        f'uv add "xnano>={state.xnano}"',
        "README uv add example",
    )

    return write_text_file("README.md", content)


def collect_drift(state: VersionState) -> list[str]:
    """Return human-readable drift messages for the current tree.

    Args:
        state: Expected versions.

    Returns:
        A list of mismatch descriptions. Empty when everything matches.
    """
    drift: list[str] = []

    pyproject = read_text_file("pyproject.toml")
    cargo = read_text_file("xnano-core/Cargo.toml")
    version_py = read_text_file("xnano/beta/core/version.py")
    readme = read_text_file("README.md")

    checks = (
        (
            "pyproject.toml project version",
            extract_first_match(
                _XNANO_PROJECT_VERSION,
                pyproject,
                "xnano project version",
            ),
            state.xnano,
        ),
        (
            "pyproject.toml xnano-core pin",
            extract_first_match(
                _XNANO_CORE_PIN,
                pyproject,
                "xnano-core dependency pin",
            ),
            state.xnano_core,
        ),
        (
            "Cargo.toml package version",
            extract_first_match(
                _CARGO_PACKAGE_VERSION,
                cargo,
                "xnano-core Cargo package version",
            ),
            state.xnano_core,
        ),
        (
            "version.py VERSION",
            extract_first_match(
                _VERSION_PY_XNANO,
                version_py,
                "xnano VERSION constant",
            ),
            state.xnano,
        ),
        (
            "version.py core compatibility",
            extract_first_match(
                _VERSION_PY_CORE,
                version_py,
                "xnano-core compatibility constant",
            ),
            state.xnano_core,
        ),
        (
            "README minimum version",
            extract_first_match(
                _README_MIN_VERSION,
                readme,
                "README minimum version warning",
            ),
            state.xnano,
        ),
        (
            "README pip install",
            extract_first_match(
                _README_PIP_INSTALL,
                readme,
                "README pip install example",
            ),
            state.xnano,
        ),
        (
            "README uv add",
            extract_first_match(
                _README_UV_ADD,
                readme,
                "README uv add example",
            ),
            state.xnano,
        ),
    )

    for label, actual, expected in checks:
        if actual != expected:
            drift.append(f"{label}: expected {expected}, found {actual}")

    return drift


def sync_version_files(state: VersionState) -> list[str]:
    """Write target versions to every whitelisted file.

    Args:
        state: Target versions to write.

    Returns:
        Relative paths that were modified.
    """
    changed: list[str] = []

    if sync_pyproject_toml(state):
        changed.append("pyproject.toml")
    if sync_cargo_toml(state):
        changed.append("xnano-core/Cargo.toml")
    if sync_version_module(state):
        changed.append("xnano/beta/core/version.py")
    if sync_readme(state):
        changed.append("README.md")

    return changed


def run_uv_lock() -> None:
    """Refresh ``uv.lock`` after manifest edits."""
    subprocess.run(
        ["uv", "lock"],
        cwd=REPO_ROOT,
        check=True,
    )


def resolve_target_state(
    package: str | None,
    version: str | None,
) -> VersionState:
    """Resolve the target version state for this invocation.

    Args:
        package: Optional package name to bump.
        version: Optional explicit version for ``package``.

    Returns:
        The target versions that should be written.

    Raises:
        VersionSyncError: If arguments are invalid.
    """
    current = read_version_state()

    if package is None:
        return current

    if package == "xnano":
        target_xnano = version or DEFAULT_XNANO_VERSION
        validate_version_string(target_xnano, "xnano")
        return VersionState(xnano=target_xnano, xnano_core=current.xnano_core)

    if package == "xnano-core":
        target_core = version or DEFAULT_XNANO_CORE_VERSION
        validate_version_string(target_core, "xnano-core")
        return VersionState(xnano=current.xnano, xnano_core=target_core)

    raise VersionSyncError(f'Unsupported package "{package}".')


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Synchronize xnano and xnano-core versions across the whitelisted "
            "release files."
        ),
    )
    parser.add_argument(
        "package",
        nargs="?",
        choices=("xnano", "xnano-core"),
        help=(
            "Optional package to bump. When omitted, versions are read from "
            "the authoritative manifests and propagated everywhere."
        ),
    )
    parser.add_argument(
        "version",
        nargs="?",
        help=(
            "Explicit version for the selected package. When omitted with a "
            "package argument, the script uses the cached default for that "
            "package."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report drift without writing files.",
    )
    parser.add_argument(
        "--no-lock",
        action="store_true",
        help="Skip running `uv lock` after successful updates.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the version synchronization script.

    Args:
        argv: Optional command-line arguments.

    Returns:
        Process exit code.
    """
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    if args.package is None and args.version is not None:
        parser.error("a version argument requires a package name.")

    try:
        target = resolve_target_state(args.package, args.version)
        drift = collect_drift(target)

        if args.check:
            if drift:
                print("Version drift detected:")
                for item in drift:
                    print(f"  - {item}")
                return 1
            print(
                "All whitelisted version files match "
                f"xnano={target.xnano}, xnano-core={target.xnano_core}."
            )
            return 0

        if args.package is None:
            print(
                "Using manifest versions: "
                f"xnano={target.xnano}, xnano-core={target.xnano_core}"
            )
        else:
            print(
                "Target versions: "
                f"xnano={target.xnano}, xnano-core={target.xnano_core}"
            )

        if not drift:
            print("No changes required.")
            return 0

        print("Planned updates:")
        for item in drift:
            print(f"  - {item}")

        changed = sync_version_files(target)
        for path in changed:
            print(f"updated {path}")

        if changed and not args.no_lock:
            print("running uv lock")
            run_uv_lock()

        remaining = collect_drift(target)
        if remaining:
            raise VersionSyncError(
                "Version sync completed with remaining drift: "
                + "; ".join(remaining)
            )

        print("Version sync complete.")
        return 0
    except VersionSyncError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        print(f"error: command failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())