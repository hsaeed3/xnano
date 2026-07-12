"""scripts.check_import_policy"""

from __future__ import annotations

import ast
import pathlib
import sys

_PACKAGE_ROOTS: dict[str, pathlib.Path] = {
    "xnano": pathlib.Path("xnano"),
    "xnano_core": pathlib.Path("xnano-core/python/xnano_core"),
}


def _get_package_path(module: str) -> pathlib.Path | None:
    """Return the repository path for an internal module."""
    root_name, *children = module.split(".")
    root = _PACKAGE_ROOTS.get(root_name)
    if root is None:
        return None
    return root.joinpath(*children)


def _check_imports(path: pathlib.Path) -> list[str]:
    """Return import-policy failures found in one Python source file."""
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except (OSError, SyntaxError) as error:
        return [f"{path}: {error}"]

    failures: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        module = node.module or ""
        root_name = module.split(".", 1)[0]
        if node.level:
            continue
        if root_name in sys.stdlib_module_names and module not in {
            "__future__",
            "typing",
        }:
            failures.append(
                f"{path}:{node.lineno}: import the stdlib module "
                f"directly (`import {module}`), not with `from {module} import`"
            )
            continue
        package_path = _get_package_path(module)
        if package_path is not None and package_path.is_dir():
            imports_concrete_modules = all(
                (package_path / f"{alias.name}.py").is_file()
                or (package_path / alias.name).is_dir()
                for alias in node.names
            )
            if imports_concrete_modules:
                continue
            failures.append(
                f"{path}:{node.lineno}: import from a concrete internal "
                f"module, not the `{module}` package barrel"
            )
    return failures


def check_import_policy(arguments: list[str] | None = None) -> int:
    """Check package sources supplied by pre-commit."""
    paths = [pathlib.Path(value) for value in (arguments or sys.argv[1:])]
    failures: list[str] = []
    for path in paths:
        if path.suffix not in {".py", ".pyi"}:
            continue
        if not (
            path.parts[:1] == ("xnano",)
            or path.parts[:3] == ("xnano-core", "python", "xnano_core")
        ):
            continue
        failures.extend(_check_imports(path))
    if failures:
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(check_import_policy())
