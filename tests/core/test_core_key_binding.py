"""CoreKeyBinding tests — Stage 2 key binding pipeline."""

from __future__ import annotations

import pytest
import xnano_core.core as core
import xnano_core.rust.engine as engine
from xnano_core.core import CoreKeyBinding

# ── Exports ───────────────────────────────────────────────────────────────────


def test_engine_exports_core_key_binding() -> None:
    assert hasattr(engine, "CoreKeyBinding")


def test_core_module_exports_core_key_binding() -> None:
    assert hasattr(core, "CoreKeyBinding")


# ── CoreKeyBinding.parse — valid bindings ─────────────────────────────────────


class TestCoreKeyBindingParse:
    @pytest.mark.parametrize(
        "binding",
        [
            "q",
            "a",
            "z",
            "enter",
            "esc",
            "backspace",
            "tab",
            "backtab",
            "up",
            "down",
            "left",
            "right",
            "home",
            "end",
            "pageup",
            "pagedown",
            "insert",
            "delete",
            "space",
            "f1",
            "f5",
            "f12",
            "ctrl+q",
            "ctrl+c",
            "ctrl+s",
            "ctrl+a",
            "alt+f4",
            "shift+up",
            "shift+down",
            "ctrl+shift+t",
            "ctrl+alt+delete",
            "ctrl+enter",
            "ctrl+backspace",
            "ctrl+tab",
        ],
    )
    def test_parse_valid(self, binding: str) -> None:
        kb = CoreKeyBinding.parse(binding)
        assert kb is not None

    def test_parse_repr_contains_binding_info(self) -> None:
        kb = CoreKeyBinding.parse("ctrl+q")
        r = repr(kb)
        assert "ctrl" in r.lower() or "q" in r.lower()

    def test_parse_returns_core_key_binding_instance(self) -> None:
        kb = CoreKeyBinding.parse("enter")
        assert isinstance(kb, CoreKeyBinding)


# ── CoreKeyBinding.parse — invalid bindings ───────────────────────────────────


class TestCoreKeyBindingParseInvalid:
    @pytest.mark.parametrize(
        "binding",
        [
            "",
            "ctrl+",
            "super+q",
            "meta+q",
            "longwordthatisnotakey",
            "f0",
            "f13",
        ],
    )
    def test_parse_invalid_raises(self, binding: str) -> None:
        with pytest.raises(Exception):
            CoreKeyBinding.parse(binding)


# ── CoreKeyBinding.matches ────────────────────────────────────────────────────


class TestCoreKeyBindingMatches:
    def test_matches_method_exists(self) -> None:
        kb = CoreKeyBinding.parse("ctrl+q")
        assert callable(getattr(kb, "matches", None))

    def test_parse_is_idempotent(self) -> None:
        kb1 = CoreKeyBinding.parse("ctrl+q")
        kb2 = CoreKeyBinding.parse("ctrl+q")
        assert repr(kb1) == repr(kb2)

    def test_distinct_bindings_have_different_reprs(self) -> None:
        kb_q = CoreKeyBinding.parse("ctrl+q")
        kb_c = CoreKeyBinding.parse("ctrl+c")
        assert repr(kb_q) != repr(kb_c)


# ── Stage 3 — native event string method coverage ─────────────────────────────


class TestStage3NativeEventMethods:
    def test_key_event_has_keyboard_kind_str(self) -> None:
        from xnano_core.rust.native import KeyEvent

        assert callable(getattr(KeyEvent, "keyboard_kind_str", None))

    def test_mouse_event_has_xnano_kind_str(self) -> None:
        from xnano_core.rust.native import MouseEvent

        assert callable(getattr(MouseEvent, "xnano_kind_str", None))

    def test_mouse_event_has_xnano_button_str(self) -> None:
        from xnano_core.rust.native import MouseEvent

        assert callable(getattr(MouseEvent, "xnano_button_str", None))

    def test_core_event_has_kind_str(self) -> None:
        from xnano_core.rust.engine import CoreEvent

        assert callable(getattr(CoreEvent, "kind_str", None))
