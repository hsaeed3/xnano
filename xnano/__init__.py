"""xnano — A Pythonic TUI framework built on ratatui and tachyonfx.

``xnano`` provides a rich set of terminal UI primitives for building
interactive terminal applications in Python, powered by Rust bindings
to the ``ratatui`` rendering engine and ``tachyonfx`` effect system.

Quick Start::

    from xnano.events import EventHandler, poll_event, on_key
    from xnano.terminal import Terminal
    from xnano.layout import Layout, Constraint, Rectangle
    from xnano.widget import Paragraph, Block
    from xnano.style import Style

    handler = EventHandler()

    @handler.on_key("ctrl+c", "q")
    def quit(event):
        raise SystemExit

    with Terminal() as term:
        while True:
            event = poll_event(100)
            if event:
                handler.dispatch(event)

            term.draw(lambda frame: frame.render_widget(
                Paragraph("Hello, xnano!", block=Block(borders="all")),
                frame.area(),
            ))
"""

from __future__ import annotations

from xnano.events import (
    Event,
    on_key,
    on_mouse,
)
from xnano.terminal import Terminal