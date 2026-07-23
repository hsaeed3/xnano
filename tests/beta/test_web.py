"""tests.beta.test_web"""

from __future__ import annotations


def test_browser_events_use_public_beta_events() -> None:
    from xnano.beta.server.native import _browser_event

    keyboard = _browser_event(
        {
            "type": "keyboard",
            "binding": "ctrl+s",
            "kind": "press",
            "character": None,
        }
    )
    mouse = _browser_event(
        {
            "type": "mouse",
            "kind": "press",
            "button": "left",
            "x": 3,
            "y": 2,
        }
    )

    assert keyboard.keyboard_event is not None
    assert keyboard.keyboard_event.matches("ctrl+s")
    assert mouse.mouse_position == (3, 2)


from xnano.beta.fields import Field
from xnano.beta.grids import BaseGrid
from xnano.beta.web import Web, grid_factory


class _Counter(BaseGrid):
    label: str = Field(default="ok")


def test_web_construction() -> None:
    web = Web(title="demo", width=60, height=20)
    assert web.title == "demo"
    assert web.width == 60
    assert web.surface == "web"
    web.close()


def test_grid_factory_shared_instance() -> None:
    instance = _Counter()
    factory, shared, grid_class = grid_factory(instance)
    assert shared is True
    assert factory() is instance


def test_grid_factory_class() -> None:
    factory, shared, grid_class = grid_factory(_Counter)
    assert shared is False
    assert grid_class is _Counter
    first = factory()
    second = factory()
    assert isinstance(first, _Counter)
    assert first is not second
