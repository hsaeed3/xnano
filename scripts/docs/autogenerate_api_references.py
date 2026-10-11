"""
scripts.docs.autogenerate_api_references

Regenerate the API reference pages in ``docs/api-reference/`` and their navigation in ``zensical.toml``.

One page is generated for every public module of ``xnano``, ``xnano_audio`` and ``xnano_image``,
read from the sources under ``packages/*/src`` (Python files and ``.pyi`` stubs), so nothing needs
to be built. The compiled-module packages ``xnano._xnano_core`` and its ``_core_types`` module hold
the whole ``xnano`` API, so they are documented even though their names start with an underscore.
Each page holds a single ``mkdocstrings`` directive for its module. The navigation
is written between the ``API_REFERENCE_START`` and ``API_REFERENCE_END`` markers in ``zensical.toml``.
``docs/api-reference/index.md`` is written by hand and is never touched.

Examples:
    Regenerate the pages and the navigation::

        uv run python scripts/docs/autogenerate_api_references.py

    Fail when the generated files are out of date, without writing anything::

        uv run python scripts/docs/autogenerate_api_references.py --check
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import sys

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[2]
API_REFERENCE_DIRECTORY = REPOSITORY_ROOT / "docs" / "api-reference"
CONFIGURATION_PATH = REPOSITORY_ROOT / "zensical.toml"

START_MARKER = "        # API_REFERENCE_START"
END_MARKER = "        # API_REFERENCE_END"
NAVIGATION_INDENTATION = 8

# Importable package name -> directory that holds its source.
PACKAGE_SOURCE_DIRECTORIES: dict[str, pathlib.Path] = {
    "xnano": REPOSITORY_ROOT / "packages" / "xnano-core" / "src" / "xnano",
    "xnano_audio": REPOSITORY_ROOT / "packages" / "xnano-audio" / "src" / "xnano_audio",
    "xnano_image": REPOSITORY_ROOT / "packages" / "xnano-image" / "src" / "xnano_image",
}

# Modules whose names start with an underscore but that are part of the documented API.
DOCUMENTED_PRIVATE_MODULES: frozenset[str] = frozenset(
    {
        "xnano._xnano_core",
        "xnano._xnano_core._core_types",
    }
)


def get_documentation_directory_name(package: str) -> str:
    """Return the directory name under ``docs/api-reference/`` for a package."""
    return package.replace("_", "-")


def get_modules(package: str, source_directory: pathlib.Path) -> list[str]:
    """
    Return every documented module of a package.

    Python sources and type stubs both count, and a module that has both is listed once.
    Private modules (any path part starting with an underscore, such as ``__main__``) are
    skipped unless they are listed in ``DOCUMENTED_PRIVATE_MODULES``: the public modules
    re-export everything they define.

    Args:
        package: Importable package name.
        source_directory: Directory holding the package source.

    Returns:
        Sorted importable module names, starting with the package itself.
    """
    modules = {package}
    for source_path in (
        *source_directory.rglob("*.py"),
        *source_directory.rglob("*.pyi"),
    ):
        relative_path = source_path.relative_to(source_directory).with_suffix("")
        parts = (
            relative_path.parts[:-1]
            if relative_path.name == "__init__"
            else relative_path.parts
        )
        module = ".".join((package, *parts))
        if any(part.startswith("_") for part in parts) and (
            module not in DOCUMENTED_PRIVATE_MODULES
        ):
            continue
        modules.add(module)
    return sorted(modules)


def get_page_path(module: str) -> pathlib.Path:
    """Return a module's page path, relative to its package's documentation directory."""
    relative_parts = module.split(".")[1:]
    if not relative_parts:
        return pathlib.Path("index.md")
    return pathlib.Path(*relative_parts).with_suffix(".md")


def get_page_content(module: str) -> str:
    """Return the ``mkdocstrings`` page for a module."""
    return f'---\ntitle: "{module}"\n---\n\n::: {module}\n'


def get_generated_files(
    package_modules: dict[str, list[str]],
) -> dict[pathlib.Path, str]:
    """Return the path and content of every generated page."""
    generated_files: dict[pathlib.Path, str] = {}
    for package, modules in package_modules.items():
        package_directory = API_REFERENCE_DIRECTORY / get_documentation_directory_name(
            package
        )
        for module in modules:
            generated_files[package_directory / get_page_path(module)] = (
                get_page_content(module)
            )
    return generated_files


def get_package_navigation(
    package: str,
    modules: list[str],
    indentation: int,
) -> list[str]:
    """Return the navigation lines for one package: one entry per module, labelled with its full name."""
    directory_name = get_documentation_directory_name(package)
    return [
        " " * indentation
        + f'{{"{module}" = "{(pathlib.Path("api-reference", directory_name) / get_page_path(module)).as_posix()}"}},'
        for module in modules
    ]


def get_navigation(package_modules: dict[str, list[str]]) -> str:
    """Return the complete generated navigation block, markers included."""
    lines = [START_MARKER]
    for package, modules in package_modules.items():
        label = get_documentation_directory_name(package)
        lines.append(" " * NAVIGATION_INDENTATION + f'{{"{label}" = [')
        lines.extend(
            get_package_navigation(
                package, modules, indentation=NAVIGATION_INDENTATION + 4
            )
        )
        lines.append(" " * NAVIGATION_INDENTATION + "]},")
    lines.append(END_MARKER)
    return "\n".join(lines)


def get_updated_configuration(
    configuration: str, package_modules: dict[str, list[str]]
) -> str:
    """Return ``zensical.toml`` content with the generated navigation block replaced."""
    start = configuration.find(START_MARKER)
    end = configuration.find(END_MARKER, start)
    if start == -1 or end == -1:
        raise SystemExit(
            f"Could not find the navigation markers in {CONFIGURATION_PATH}. "
            f"Add the lines '{START_MARKER.strip()}' and '{END_MARKER.strip()}' inside "
            "the API Reference navigation list, then run this script again."
        )
    end += len(END_MARKER)
    return configuration[:start] + get_navigation(package_modules) + configuration[end:]


def get_stale_files(
    generated_files: dict[pathlib.Path, str],
    configuration: str,
    updated_configuration: str,
) -> list[str]:
    """Return a description of every generated file that is missing, extra or out of date."""
    stale_files: list[str] = []

    existing_paths = {
        path
        for package in PACKAGE_SOURCE_DIRECTORIES
        for path in (
            API_REFERENCE_DIRECTORY / get_documentation_directory_name(package)
        ).rglob("*.md")
    }
    stale_files.extend(
        f"missing: {path.relative_to(REPOSITORY_ROOT)}"
        for path in sorted(generated_files.keys() - existing_paths)
    )
    stale_files.extend(
        f"unexpected: {path.relative_to(REPOSITORY_ROOT)}"
        for path in sorted(existing_paths - generated_files.keys())
    )
    stale_files.extend(
        f"out of date: {path.relative_to(REPOSITORY_ROOT)}"
        for path in sorted(generated_files.keys() & existing_paths)
        if path.read_text() != generated_files[path]
    )

    if configuration != updated_configuration:
        stale_files.append(
            f"out of date: {CONFIGURATION_PATH.relative_to(REPOSITORY_ROOT)}"
        )
    return stale_files


def generate_api_references(should_check_only: bool = False) -> int:
    """
    Generate the API reference pages and navigation, or only verify them.

    Args:
        should_check_only: When ``True``, nothing is written and a non-zero exit code is
            returned if any generated file is missing or out of date.

    Returns:
        The process exit code.
    """
    package_modules = {
        package: get_modules(package, source_directory)
        for package, source_directory in PACKAGE_SOURCE_DIRECTORIES.items()
    }
    generated_files = get_generated_files(package_modules)
    configuration = CONFIGURATION_PATH.read_text()
    updated_configuration = get_updated_configuration(configuration, package_modules)

    if should_check_only:
        stale_files = get_stale_files(
            generated_files, configuration, updated_configuration
        )
        if stale_files:
            sys.stderr.write(
                "The API reference is out of date:\n"
                + "\n".join(f"  {description}" for description in stale_files)
                + "\nRun 'uv run python scripts/docs/autogenerate_api_references.py' to regenerate it.\n"
            )
            return 1
        return 0

    for package in PACKAGE_SOURCE_DIRECTORIES:
        shutil.rmtree(
            API_REFERENCE_DIRECTORY / get_documentation_directory_name(package),
            ignore_errors=True,
        )
    for path, content in generated_files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    CONFIGURATION_PATH.write_text(updated_configuration)
    return 0


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser(
        description="Regenerate the API reference pages and navigation."
    )
    argument_parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the generated files are up to date without writing anything.",
    )
    arguments = argument_parser.parse_args()
    sys.exit(generate_api_references(should_check_only=arguments.check))
