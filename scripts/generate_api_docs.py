"""scripts.generate_api_docs

---

Regenerate the mkdocstrings API reference and its Zensical navigation:

    uv run python scripts/generate_api_docs.py
"""

from __future__ import annotations

import argparse
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS_ROOT = ROOT / "docs" / "api"
CONFIG_PATH = ROOT / "zensical.toml"
START_MARKER = "    # API_REFERENCE_START"
END_MARKER = "    # API_REFERENCE_END"
PACKAGES = {
    "xnano": ROOT / "xnano",
    "xnano_core": ROOT / "xnano-core" / "python" / "xnano_core",
}


def get_modules(package: str, source_root: pathlib.Path) -> list[str]:
    """Return every documented module in a package.

    Args:
        package: Importable package name.
        source_root: Package source directory.

    Returns:
        Sorted importable module names.
    """
    modules = {package}
    for source_path in (
        *source_root.rglob("*.py"),
        *source_root.rglob("*.pyi"),
    ):
        if source_path.name == "__main__.py":
            continue
        relative_path = source_path.relative_to(source_root).with_suffix("")
        parts = (
            relative_path.parts[:-1]
            if relative_path.name == "__init__"
            else relative_path.parts
        )
        modules.add(".".join((package, *parts)))
    return sorted(modules)


def get_page_path(package: str, module: str) -> pathlib.Path:
    """Return a module's generated documentation path."""
    relative_parts = module.split(".")[1:]
    if not relative_parts:
        return pathlib.Path("index.md")
    return pathlib.Path(*relative_parts).with_suffix(".md")


def get_page_content(module: str) -> str:
    """Return a module's mkdocstrings page."""
    return f'---\ntitle: "{module}"\n---\n\n::: {module}\n'


def get_navigation(
    package: str,
    modules: list[str],
    docs_directory: str,
    indentation: int = 12,
) -> list[str]:
    """Return Zensical navigation lines for a package."""
    tree: dict[str, dict] = {}
    for module in modules:
        current = tree
        for part in module.split(".")[1:]:
            current = current.setdefault(part, {})

    lines = [" " * indentation + f'"api/{docs_directory}/index.md",']

    def add_items(
        branch: dict[str, dict], parts: tuple[str, ...], level: int
    ) -> None:
        for name, children in branch.items():
            page = pathlib.Path(
                "api", docs_directory, *parts, f"{name}.md"
            ).as_posix()
            if children:
                lines.append(" " * level + f'{{ "{name}" = [')
                lines.append(" " * (level + 4) + f'"{page}",')
                add_items(children, (*parts, name), level + 4)
                lines.append(" " * level + "]},")
            else:
                lines.append(" " * level + f'"{page}",')

    add_items(tree, (), indentation)
    return lines


def get_api_navigation(package_modules: dict[str, list[str]]) -> str:
    """Return the complete generated API navigation block."""
    lines = [START_MARKER, '    { "API Reference" = [']
    for package, modules in package_modules.items():
        label = package.replace("_", "-")
        directory = label
        lines.append(f'        {{ "{label}" = [')
        lines.extend(get_navigation(package, modules, directory))
        lines.append("        ]},")
    lines.extend(["    ]},", END_MARKER])
    return "\n".join(lines)


def get_generated_files(
    package_modules: dict[str, list[str]],
) -> dict[pathlib.Path, str]:
    """Return every generated path and its content."""
    generated_files: dict[pathlib.Path, str] = {}
    for package, modules in package_modules.items():
        docs_directory = package.replace("_", "-")
        for module in modules:
            page_path = (
                DOCS_ROOT / docs_directory / get_page_path(package, module)
            )
            generated_files[page_path] = get_page_content(module)
    return generated_files


def generate_api_docs(check_only: bool = False) -> None:
    """Generate or verify all API reference pages and navigation."""
    package_modules = {
        package: get_modules(package, source_root)
        for package, source_root in PACKAGES.items()
    }
    generated_files = get_generated_files(package_modules)
    config = CONFIG_PATH.read_text()
    start = config.index(START_MARKER)
    end = config.index(END_MARKER, start) + len(END_MARKER)
    generated_config = (
        config[:start] + get_api_navigation(package_modules) + config[end:]
    )

    if check_only:
        actual_files = {
            path
            for package in PACKAGES
            for path in (DOCS_ROOT / package.replace("_", "-")).rglob("*.md")
        }
        assert actual_files == generated_files.keys()
        assert all(
            path.read_text() == content
            for path, content in generated_files.items()
        )
        assert config == generated_config
        return

    for package in PACKAGES:
        shutil.rmtree(
            DOCS_ROOT / package.replace("_", "-"), ignore_errors=True
        )
    for path, content in generated_files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    CONFIG_PATH.write_text(generated_config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    generate_api_docs(arguments.check)
