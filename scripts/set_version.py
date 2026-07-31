"""scripts.set_version

---

Synchronize ``xnano`` and ``xnano-core`` version strings across the
release files in this repository.

Authoritative sources:

- ``xnano``: ``pyproject.toml`` ``[project].version``
- ``xnano-core``: ``xnano-core/Cargo.toml`` ``[package].version``

Files updated by this script:

- ``pyproject.toml`` — xnano version + ``xnano-core==…`` dependency pin
- ``xnano-core/Cargo.toml`` — xnano-core package version (also feeds the
  compiled ``xnano_core.rust.native.__version__`` via
  ``env!("CARGO_PKG_VERSION")``)
- ``xnano/__init__.py`` — ``__version__`` constant
- ``README.md`` — install pins (``xnano>=…``)
- every ``docs/**/*.md`` file that embeds ``xnano>=…`` — install examples
  and runnable pyodide fences (`` ```pyodide install="xnano>=…" ``)

``xnano-core/python/xnano_core/rust/native.pyi`` only declares
``__version__: str`` (no literal to keep in sync). The runtime value is
set from Cargo at build time.
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import re
import subprocess
import sys

DEFAULT_XNANO_VERSION = "0.99.9"
"""Default ``xnano`` version when the package is named without an
explicit value."""

DEFAULT_XNANO_CORE_VERSION = "0.0.2"
"""Default ``xnano-core`` version when the package is named without an
explicit value."""

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

DOCS_DIR = REPO_ROOT / "docs"
"""Documentation root scanned for install / pyodide version pins."""

MANIFEST_FILES: tuple[str, ...] = (
    "pyproject.toml",
    "xnano-core/Cargo.toml",
    "xnano/__init__.py",
)
"""Package-manifest paths always synchronized by this script."""

ROOT_MARKDOWN_PIN_FILES: tuple[str, ...] = ("README.md",)
"""Markdown outside ``docs/`` that embed ``xnano>=…`` install examples."""

VERSION_PATTERN = re.compile(r"^v?(\d+\.\d+\.\d+(?:[a-zA-Z]+\d+)?)$")
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
_INIT_PY_VERSION = re.compile(
    r'^(?P<indent>[ \t]*)__version__ = "(?P<version>[^"]+)"$',
    re.MULTILINE,
)
_MARKDOWN_XNANO_PIN = re.compile(r'(["\'])xnano>=([^"\']+)\1')
"""Install pin in markdown: ``\"xnano>=…\"`` / ``'xnano>=…'``.

Covers pip/uv install examples and fence attributes such as
`` ```pyodide install="xnano>=…" ``.
"""


@dataclasses.dataclass(frozen=True)
class VersionState:
    """Resolved package versions used for synchronization."""

    xnano: str
    """The ``xnano`` package version."""
    xnano_core: str
    """The ``xnano-core`` package version."""


class VersionSyncError(RuntimeError):
    """Raised when version files cannot be read, validated, or updated
    safely."""


def validate_version_string(version: str, label: str) -> str:
    """Validate a version string before writing it to disk.

    Args:
        version: Candidate version value.
        label: Human-readable field name for error messages.

    Returns:
        The validated version string.

    Raises:
        VersionSyncError: If ``version`` is not a supported release
            string.
    """
    if not VERSION_PATTERN.fullmatch(version):
        message = (
            f'Invalid {label} version "{version}". '
            "Expected a PEP 440-style value like 0.99.9 or 1.0.0b1."
        )
        raise VersionSyncError(message)
    return version


def is_allowed_edit_path(relative_path: str) -> bool:
    """Return whether this script may modify ``relative_path``.

    Args:
        relative_path: Path relative to the repository root.

    Returns:
        ``True`` for manifests, root markdown pins, or any markdown under
        ``docs/``.
    """
    if relative_path in MANIFEST_FILES:
        return True
    if relative_path in ROOT_MARKDOWN_PIN_FILES:
        return True
    path = pathlib.PurePosixPath(relative_path.replace("\\", "/"))
    return (
        len(path.parts) >= 2
        and path.parts[0] == "docs"
        and path.suffix == ".md"
    )


def ensure_editable_path(relative_path: str) -> None:
    """Ensure a path may be edited by this script.

    Args:
        relative_path: Path relative to the repository root.

    Raises:
        VersionSyncError: If editing the path is not allowed.
    """
    if not is_allowed_edit_path(relative_path):
        message = (
            f'Refusing to edit "{relative_path}". '
            "Allowed: package manifests, README.md, and docs/**/*.md."
        )
        raise VersionSyncError(message)


def read_text_file(relative_path: str) -> str:
    """Read an editable repository file as text.

    Args:
        relative_path: Path relative to the repository root.

    Returns:
        The file contents.

    Raises:
        VersionSyncError: If the path is not allowed or cannot be read.
    """
    ensure_editable_path(relative_path)
    path = REPO_ROOT / relative_path
    if not path.is_file():
        raise VersionSyncError(
            f'Editable file "{relative_path}" does not exist.'
        )
    return path.read_text(encoding="utf-8")


def write_text_file(relative_path: str, content: str) -> bool:
    """Write an editable repository file when content changed.

    Args:
        relative_path: Path relative to the repository root.
        content: Replacement file contents.

    Returns:
        ``True`` when the file was updated.

    Raises:
        VersionSyncError: If the path is not allowed.
    """
    ensure_editable_path(relative_path)
    path = REPO_ROOT / relative_path
    original = path.read_text(encoding="utf-8") if path.is_file() else ""
    if original == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


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
        raise VersionSyncError(f"Could not find {label} in repository files.")
    groups = match.groupdict()
    if "version" in groups and groups["version"] is not None:
        return groups["version"]
    return match.group(1)


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
            f"Expected exactly one replacement for {label}, found {count}."
        )
        raise VersionSyncError(message)
    return updated, count


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


def sync_xnano_init(state: VersionState) -> bool:
    """Synchronize ``xnano/__init__.py``.

    The package prefers ``importlib.metadata.version("xnano")`` and keeps a
    fallback ``__version__`` literal (often indented under
    ``PackageNotFoundError``). Preserve that indent when rewriting.

    Args:
        state: Target versions to write.

    Returns:
        ``True`` when the file changed.
    """
    content = read_text_file("xnano/__init__.py")
    match = _INIT_PY_VERSION.search(content)
    if match is None:
        raise VersionSyncError(
            "Could not find xnano __version__ constant in xnano/__init__.py"
        )
    replacement = f'{match.group("indent")}__version__ = "{state.xnano}"'
    content, _ = apply_single_replacement(
        content,
        _INIT_PY_VERSION,
        replacement,
        "xnano __version__ constant",
    )
    return write_text_file("xnano/__init__.py", content)


def collect_markdown_install_pin_versions(content: str) -> list[str]:
    """Collect unique ``xnano>=…`` versions from markdown content.

    Args:
        content: Markdown file contents.

    Returns:
        Distinct version strings found in install pins, in order.
    """
    found: list[str] = []
    for match in _MARKDOWN_XNANO_PIN.finditer(content):
        version = match.group(2)
        if version not in found:
            found.append(version)
    return found


def markdown_has_xnano_pins(content: str) -> bool:
    """Return whether ``content`` contains any ``xnano>=…`` pins."""
    return _MARKDOWN_XNANO_PIN.search(content) is not None


def iter_docs_markdown_paths() -> list[str]:
    """Return repo-relative paths for every markdown file under ``docs/``.

    Returns:
        Sorted relative paths using POSIX separators.
    """
    if not DOCS_DIR.is_dir():
        return []
    paths: list[str] = []
    for path in sorted(DOCS_DIR.rglob("*.md")):
        if not path.is_file():
            continue
        relative = path.relative_to(REPO_ROOT).as_posix()
        paths.append(relative)
    return paths


def discover_markdown_pin_files() -> list[str]:
    """Discover markdown files that embed ``xnano>=…`` pins.

    Scans ``README.md`` (when present) and every ``docs/**/*.md`` file.
    Files without pins are omitted so empty docs pages do not fail sync.

    Returns:
        Sorted unique relative paths that contain at least one pin.
    """
    discovered: list[str] = []
    for relative_path in ROOT_MARKDOWN_PIN_FILES:
        path = REPO_ROOT / relative_path
        if path.is_file() and markdown_has_xnano_pins(
            path.read_text(encoding="utf-8")
        ):
            discovered.append(relative_path)
    for relative_path in iter_docs_markdown_paths():
        path = REPO_ROOT / relative_path
        if markdown_has_xnano_pins(path.read_text(encoding="utf-8")):
            discovered.append(relative_path)
    return discovered


def sync_markdown_install_pins(
    relative_path: str,
    state: VersionState,
    *,
    require_pins: bool = True,
) -> bool:
    """Synchronize ``xnano>=…`` install pins in a markdown file.

    Args:
        relative_path: Markdown path relative to the repo root.
        state: Target versions to write.
        require_pins: When ``True``, raise if the file has no pins.

    Returns:
        ``True`` when the file changed.

    Raises:
        VersionSyncError: If ``require_pins`` is set and no pins exist.
    """
    content = read_text_file(relative_path)
    updated, count = _MARKDOWN_XNANO_PIN.subn(
        rf"\1xnano>={state.xnano}\1",
        content,
    )
    if count == 0:
        if require_pins:
            raise VersionSyncError(
                f'Could not find xnano>= install pins in "{relative_path}".'
            )
        return False
    return write_text_file(relative_path, updated)


def collect_markdown_install_pin_drift(
    relative_path: str,
    state: VersionState,
    *,
    require_pins: bool = False,
) -> list[str]:
    """Return drift messages for one markdown install-pin file.

    Args:
        relative_path: Markdown path relative to the repo root.
        state: Expected versions.
        require_pins: When ``True``, missing pins are reported as drift.

    Returns:
        Drift descriptions for mismatched or (optionally) missing pins.
    """
    drift: list[str] = []
    content = read_text_file(relative_path)
    versions = collect_markdown_install_pin_versions(content)
    label = relative_path
    if not versions:
        if require_pins:
            drift.append(
                f"{label} xnano>= pins: expected {state.xnano}, found none"
            )
        return drift
    for version in versions:
        if version != state.xnano:
            drift.append(
                f"{label} xnano>= pin: expected {state.xnano}, found {version}"
            )
    return drift


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
    xnano_init = read_text_file("xnano/__init__.py")

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
            "__init__.py __version__",
            extract_first_match(
                _INIT_PY_VERSION,
                xnano_init,
                "xnano __version__ constant",
            ),
            state.xnano,
        ),
    )

    for label, actual, expected in checks:
        if actual != expected:
            drift.append(f"{label}: expected {expected}, found {actual}")

    for relative_path in ROOT_MARKDOWN_PIN_FILES:
        path = REPO_ROOT / relative_path
        if path.is_file():
            drift.extend(
                collect_markdown_install_pin_drift(
                    relative_path,
                    state,
                    require_pins=True,
                )
            )

    for relative_path in discover_markdown_pin_files():
        if relative_path in ROOT_MARKDOWN_PIN_FILES:
            continue
        drift.extend(
            collect_markdown_install_pin_drift(
                relative_path,
                state,
                require_pins=False,
            )
        )

    return drift


def sync_version_files(state: VersionState) -> list[str]:
    """Write target versions to manifests and discovered markdown pins.

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
    if sync_xnano_init(state):
        changed.append("xnano/__init__.py")

    for relative_path in ROOT_MARKDOWN_PIN_FILES:
        path = REPO_ROOT / relative_path
        if path.is_file() and sync_markdown_install_pins(
            relative_path,
            state,
            require_pins=True,
        ):
            changed.append(relative_path)

    for relative_path in discover_markdown_pin_files():
        if relative_path in ROOT_MARKDOWN_PIN_FILES:
            continue
        if sync_markdown_install_pins(
            relative_path,
            state,
            require_pins=False,
        ):
            changed.append(relative_path)

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
            "Synchronize xnano and xnano-core versions across package "
            "manifests, README install pins, and every docs/**/*.md file "
            "that embeds xnano>= pins (including pyodide fences)."
        ),
    )
    parser.add_argument(
        "package",
        nargs="?",
        choices=("xnano", "xnano-core"),
        help=(
            "Optional package to bump. When omitted, versions are read "
            "from the authoritative manifests and propagated everywhere."
        ),
    )
    parser.add_argument(
        "version",
        nargs="?",
        help=(
            "Explicit version for the selected package. When omitted "
            "with a package argument, the script uses the cached "
            "default for that package."
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
            pin_files = discover_markdown_pin_files()
            print(
                "All version files match "
                f"xnano={target.xnano}, xnano-core={target.xnano_core}."
            )
            print(
                f"Markdown pin files scanned: {len(pin_files)} "
                f"({', '.join(pin_files) if pin_files else 'none'})"
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
