"""Package surface and re-export tests."""

from __future__ import annotations

import xnano_core
import xnano_core.rust.native as rust
import xnano_core.rust.engine as engine


def test_engine_submodule_exports() -> None:
    expected = {
        "CoreEvent",
        "CoreRenderContent",
        "CoreRenderNode",
        "CoreSession",
        "CoreTerminalEventKind",
        "CoreTerminalRef",
        "CoreTickEvent",
        "CoreRenderIR",
        "IrLine",
        "CoreKeyBinding",
    }
    assert expected.issubset(set(dir(engine)))


def test_event_types_reexported_at_rust_root() -> None:
    assert rust.CoreEvent is engine.CoreEvent
    assert rust.CoreTickEvent is engine.CoreTickEvent
    assert rust.CoreTerminalEventKind is engine.CoreTerminalEventKind


def test_event_types_reexported_at_package_root() -> None:
    assert xnano_core.CoreEvent is engine.CoreEvent
    assert xnano_core.CoreTickEvent is engine.CoreTickEvent
    assert xnano_core.CoreTerminalEventKind is engine.CoreTerminalEventKind


def test_old_event_names_not_importable_at_package_root() -> None:
    assert not hasattr(xnano_core, "Event")
    assert not hasattr(xnano_core, "TickEvent")
    assert not hasattr(xnano_core, "TerminalEventKind")
    assert not hasattr(xnano_core, "Session")
    assert not hasattr(xnano_core, "RenderNode")
    assert not hasattr(xnano_core, "RenderContent")
    assert not hasattr(xnano_core, "TerminalRef")


def test_old_engine_names_not_importable_from_engine_submodule() -> None:
    old_names = (
        "Event",
        "TickEvent",
        "TerminalEventKind",
        "Session",
        "RenderNode",
        "RenderContent",
        "TerminalRef",
    )
    for name in old_names:
        assert not hasattr(engine, name), name


def test_rust_primitives_still_exposed() -> None:
    for name in (
        "Paragraph",
        "Block",
        "Buffer",
        "Constraint",
        "Rect",
        "Effect",
        "poll_event",
        "read_event",
    ):
        assert hasattr(rust, name), name


def test_terminal_event_kind_includes_tick() -> None:
    assert hasattr(engine.CoreTerminalEventKind, "Tick")


def test_rust_engine_submodule_exposed() -> None:
    assert hasattr(rust, "engine")


def test_package_root_all_matches_exports() -> None:
    assert set(xnano_core.__all__) == {
        "CoreEvent",
        "CoreTickEvent",
        "CoreTerminalEventKind",
        "__version__",
    }


def test_python_shim_modules_importable() -> None:
    import xnano_core.core
    import xnano_core.rust.engine as engine_shim

    assert engine_shim.__doc__ is not None
    assert xnano_core.core.__doc__ is not None
