"""tests.beta.test_decoupling"""

from __future__ import annotations

import ast
import pathlib

from xnano.beta import hooks
from xnano.beta.actions import Action
from xnano.beta.core.runtime import Runtime
from xnano.beta.fields import Field
from xnano.beta.grids import BaseGrid


# The feature showcase deliberately reuses the stable ``xnano._demo``
# rather than maintaining a parallel copy; every other beta module stays
# fully decoupled from stable ``xnano``.
_DECOUPLING_EXEMPT = {"core/demo.py"}


def test_beta_has_no_stable_xnano_imports() -> None:
    """Beta may import itself and ``xnano_core``, never stable ``xnano``."""
    root = pathlib.Path(__file__).parents[2] / "xnano" / "beta"
    violations: list[str] = []
    for path in root.rglob("*.py"):
        if path.relative_to(root).as_posix() in _DECOUPLING_EXEMPT:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                names = [node.module]
            for name in names:
                if name == "xnano" or (
                    name.startswith("xnano.")
                    and not name.startswith("xnano.beta")
                ):
                    violations.append(
                        f"{path.relative_to(root)}:{getattr(node, 'lineno', 0)}"
                    )
    assert violations == []


def test_runtime_dispatches_beta_keyboard_hooks() -> None:
    """Synthetic actions and runtime input share beta hook dispatch."""

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
