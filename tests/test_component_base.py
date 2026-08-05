"""tests.test_component_base"""

from __future__ import annotations

import dataclasses

from xnano.components.component import Component, TextBlock
from xnano.core import Runtime
from xnano.types import is_component, is_focusable_component


@dataclasses.dataclass
class Badge(Component):
    text: str
    color: str = "cyan"

    def compose(self, ctx):
        return TextBlock.from_plain(self.text, foreground=self.color)


def test_minimum_custom_component() -> None:
    badge = Badge("ok")
    assert badge.visible is True
    assert badge.focused is False
    assert is_component(badge)
    assert not is_focusable_component(badge)

    runtime = Runtime.offscreen(20, 5)
    try:
        frame = runtime.render(badge)
        assert "ok" in frame.text
    finally:
        runtime.close()


def test_component_live_attributes() -> None:
    badge = Badge("one")
    badge.text = "two"
    badge.visible = False
    assert badge.text == "two"
    assert badge.visible is False


def test_component_post_init_hook() -> None:
    calls: list[str] = []

    @dataclasses.dataclass
    class Hooked(Component):
        def component_post_init(self) -> None:
            calls.append("post")

    Hooked()
    assert calls == ["post"]
