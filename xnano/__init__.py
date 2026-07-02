"""xnano — A Pythonic TUI framework built on ratatui and tachyonfx.

``xnano`` provides a rich set of terminal UI primitives for building
interactive terminal applications in Python, powered by Rust bindings
to the ``ratatui`` rendering engine and ``tachyonfx`` effect system.

Quick Start::

    import dataclasses
    from xnano import Component, Context, hooks, Terminal, poll_event, dispatch

    @dataclasses.dataclass
    class CounterState:
        count: int = 0

    class Counter(Component[CounterState]):
        @hooks.on_keyboard("up")
        def increment(self, ctx: Context[CounterState]) -> None:
            ctx.update(count=ctx.state.count + 1)

        @hooks.on_keyboard("ctrl+c")
        def quit(self, ctx: Context[CounterState]) -> None:
            raise SystemExit

        def render(self, area):
            return f"Count: {self.state.count}"

    def main():
        counter = Counter(state=CounterState())
        with Terminal() as term:
            while True:
                event = poll_event(16)
                if event:
                    dispatch(event, counter)
                term.draw(lambda frame: frame.render_widget(counter.render(frame.area()), frame.area()))
"""

from __future__ import annotations

from xnano import hooks
from xnano.component import Component
from xnano.context import Context
from xnano.events import (
    Event,
    dispatch,
    poll_event,
    read_event,
)
from xnano.printing import print
from xnano.terminal import Terminal

__all__ = (
    "Component",
    "Context",
    "hooks",
    "Event",
    "dispatch",
    "poll_event",
    "read_event",
    "print",
    "Terminal",
)
