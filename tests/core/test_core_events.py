"""CoreEvent model tests."""

from __future__ import annotations

import xnano_core.rust.native as rust
from conftest import requires_input
from xnano_core.rust.engine import (
    CoreEvent,
    CoreTerminalEventKind,
    CoreTickEvent,
)


def test_tick_event_type_exposes_elapsed_ms() -> None:
    # Instances are synthesized by CoreSession.poll_event; verify runtime attribute.
    assert hasattr(CoreTickEvent, "elapsed_ms")


def test_event_fields_exist() -> None:
    for field in (
        "kind",
        "key",
        "width",
        "height",
        "paste",
        "mouse",
        "tick",
    ):
        assert hasattr(CoreEvent, field)


def test_terminal_event_kind_variants() -> None:
    for variant in (
        "Key",
        "Resize",
        "Paste",
        "Mouse",
        "FocusGained",
        "FocusLost",
        "Tick",
    ):
        assert hasattr(CoreTerminalEventKind, variant)


def test_core_terminal_event_kind_variants_are_distinct() -> None:
    variants = (
        CoreTerminalEventKind.Key,
        CoreTerminalEventKind.Resize,
        CoreTerminalEventKind.Paste,
        CoreTerminalEventKind.Mouse,
        CoreTerminalEventKind.FocusGained,
        CoreTerminalEventKind.FocusLost,
        CoreTerminalEventKind.Tick,
    )
    for index, left in enumerate(variants):
        for right in variants[index + 1 :]:
            assert left != right


@requires_input
def test_root_poll_event_signature() -> None:
    # Module-level poll should accept a timeout and return Optional[CoreEvent].
    result = rust.poll_event(0)
    assert result is None
