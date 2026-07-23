"""xnano web counter example.

Demonstrates the same BaseGrid working on both terminal and web
interfaces: click the box (or press the up arrow) to count, type into
the name input, and watch the tick counter advance once per second.

Custom HTTP routes (``POST /increment``, ``GET /reset``) are declared
with request hooks from ``xnano.hooks`` and work under both hosts.

Usage:
    uv run python examples/web_counter.py          # terminal mode
    uv run python examples/web_counter.py --web    # web server at
                                                   # http://127.0.0.1:8000
"""

from __future__ import annotations

import sys

from xnano.components.text import Text
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.hooks import (
    on_click,
    on_keyboard,
    on_tick,
)
from xnano.requests import (
    on_get_request,
    on_post_request,
)


class Counter(BaseGrid, direction="vertical", gap=1):
    """A counter with click, keyboard, tick, text-input, and HTTP hooks."""

    title: Text = Field(
        default=Text("xnano counter", color="cyan", modifiers=("bold",)),
        height=1,
    )
    name: Text = Field(
        default_factory=lambda: Text(
            "", input=True, placeholder="type your name…"
        ),
        height=1,
    )
    label: str = Field(default="Count: 0", height=1)
    body: str = Field(
        default="Click me (or press ↑)", border="rounded", title="counter"
    )
    clock: str = Field(default="uptime: 0s", height=1, color="gray")
    count: int = Field(default=0, state=True)
    seconds: int = Field(default=0, state=True)

    @on_click("body")
    def _click_bump(self) -> None:
        self._bump()

    @on_keyboard("up")
    def _key_bump(self) -> None:
        self._bump()

    @on_post_request("/increment")
    def _http_bump(self) -> None:
        self._bump()

    @on_get_request("/reset")
    def _http_reset(self) -> None:
        self.count = 0
        self.label = "Count: 0"

    def _bump(self) -> None:
        self.count += 1
        greeting = ""
        if isinstance(self.name.content, str) and self.name.content:
            greeting = f" — hi {self.name.content}!"
        self.label = f"Count: {self.count}{greeting}"

    @on_tick(1000)
    def _clock(self) -> None:
        self.seconds += 1
        self.clock = f"uptime: {self.seconds}s"


def main() -> None:
    """Run counter on terminal or web based on --web flag."""
    use_web = "--web" in sys.argv

    if use_web:
        from xnano.web import Web

        # Pass the class itself for a fresh grid per browser session;
        # pass an instance (``Counter()``) to share one across visitors.
        Web(title="xnano web counter").run(Counter)
    else:
        from xnano.terminal import Terminal

        with Terminal() as terminal:
            terminal.run(Counter())


if __name__ == "__main__":
    main()
