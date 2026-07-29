"""tests.test_decoupling"""

from __future__ import annotations

import ast
import pathlib

from xnano import hooks
from xnano.actions import Action
from xnano.core.runtime import Runtime
from xnano.fields import Field
from xnano.grids import BaseGrid

# Top-level packages that framework modules may import from.
_ALLOWED_ROOTS = frozenset(
    {
        "xnano",
        "xnano_core",
        "typing",
        "typing_extensions",
        "collections",
        "dataclasses",
        "enum",
        "functools",
        "itertools",
        "operator",
        "types",
        "abc",
        "argparse",
        "ast",
        "copy",
        "datetime",
        "re",
        "sys",
        "os",
        "io",
        "json",
        "math",
        "time",
        "random",
        "signal",
        "atexit",
        "contextlib",
        "contextvars",
        "threading",
        "queue",
        "http",
        "urllib",
        "html",
        "pathlib",
        "inspect",
        "importlib",
        "warnings",
        "weakref",
        "textwrap",
        "string",
        "struct",
        "hashlib",
        "base64",
        "colorsys",
        "unicodedata",
        "uuid",
        "zlib",
        "shutil",
        "tempfile",
        "traceback",
        "logging",
        "asyncio",
        "concurrent",
        "multiprocessing",
        "subprocess",
        "socket",
        "ssl",
        "email",
        "mimetypes",
        "wsgiref",
        "unittest",
        "pydantic_core",
        "markdown_it",
        "pygments",
        "PIL",
        "starlette",
        "uvicorn",
        "__future__",
        "builtins",
    }
)


def _root_name(module_name: str) -> str:
    return module_name.split(".", 1)[0]


def test_package_imports_only_allowed_dependencies() -> None:
    """Framework modules import only themselves, core, and known deps."""
    root = pathlib.Path(__file__).parents[1] / "xnano"
    violations: list[str] = []
    for path in root.rglob("*.py"):
        if path.name == "__main__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                names = [node.module]
            for name in names:
                if name.startswith("."):
                    continue
                root_name = _root_name(name)
                if root_name not in _ALLOWED_ROOTS:
                    violations.append(
                        f"{path.relative_to(root)}:"
                        f"{getattr(node, 'lineno', 0)}:{name}"
                    )
    assert violations == []


def test_runtime_dispatches_keyboard_hooks() -> None:
    """Synthetic actions and runtime input share hook dispatch."""

    class App(BaseGrid):
        count: int = Field(default=0, state=True)

        @hooks.on_keyboard("enter")
        def increment(self) -> None:
            self.count += 1

    app = App()
    runtime = Runtime.offscreen(20, 4)
    try:
        runtime.set_root(app)
        runtime.perform(Action.keyboard("enter"))
        assert app.count == 1
    finally:
        runtime.close()
