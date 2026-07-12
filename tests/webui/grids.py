"""Shared BaseGrid fixtures for beta web tests."""

from __future__ import annotations

from xnano.components.text import Text
from xnano.webui.requests import on_get_request, on_post_request
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.events import on_click, on_field, on_keyboard, on_tick


class SimpleGrid(BaseGrid, direction="horizontal", gap=1):
    """BaseGrid with two string fields side by side."""

    left: str = Field(default="left", height=1)
    right: str = Field(default="right", height=1)


class StyledGrid(BaseGrid):
    """BaseGrid with styled fields."""

    title: str = Field(default="Title", color="cyan", modifiers=("bold",))
    body: str = Field(
        default="Content", color="red", border="rounded", title="Panel"
    )


class FrameGrid(BaseGrid):
    """BaseGrid with frame chrome."""

    framed: str = Field(
        default="framed",
        border="rounded",
        title="My Panel",
    )


class NestedGrid(BaseGrid):
    """BaseGrid that contains another grid."""

    inner: SimpleGrid = Field(default_factory=SimpleGrid)


class ClickableGrid(BaseGrid, direction="vertical", gap=1):
    """BaseGrid with a clickable field and state."""

    label: str = Field(default="Count: 0", height=1)
    body: str = Field(default="Click me", border="rounded")
    count: int = Field(default=0, state=True)

    @on_click("body")
    def _bump(self) -> None:
        self.count += 1
        self.label = f"Count: {self.count}"


class TextGrid(BaseGrid):
    """BaseGrid using beta Text component."""

    title: Text = Field(
        default=Text("Title", color="cyan", modifiers=("bold",))
    )
    body: str = Field(default="Body text")


class InteractiveGrid(BaseGrid, direction="vertical", gap=1):
    """BaseGrid exercising keyboard, tick, field-expression, and input hooks."""

    name: Text = Field(
        default_factory=lambda: Text("", input=True, placeholder="name…")
    )
    label: str = Field(default="Count: 0", height=1)
    body: str = Field(default="Click me", border="rounded")
    note: str = Field(default="", height=1)
    count: int = Field(default=0, state=True)
    ticks: int = Field(default=0, state=True)

    @on_click("body")
    def _bump(self) -> None:
        self.count += 1
        self.label = f"Count: {self.count}"

    @on_keyboard("up", "ctrl+k")
    def _key_bump(self) -> None:
        self.count += 10
        self.label = f"Count: {self.count}"

    @on_tick(50)
    def _tick(self) -> None:
        self.ticks += 1

    @on_field("count >= 10")
    def _milestone(self) -> None:
        self.note = "double digits"


class RequestHookGrid(BaseGrid, direction="vertical", gap=1):
    """BaseGrid with custom HTTP request hooks and a reactive field hook."""

    label: str = Field(default="Count: 0", height=1)
    body: str = Field(default="bump", border="rounded")
    note: str = Field(default="", height=1)
    count: int = Field(default=0, state=True)
    visits: int = Field(default=0, state=True)

    @on_post_request("/increment")
    def _increment(self) -> None:
        self.count += 1
        self.label = f"Count: {self.count}"

    @on_get_request("/status")
    def _status(self) -> None:
        self.label = f"status:{self.count}"

    @on_get_request("/")
    def _visit(self) -> None:
        self.visits += 1

    @on_field("count >= 2")
    def _milestone(self) -> None:
        self.note = "double"
