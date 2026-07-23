"""Tests for the public xnano.types re-export module."""

from __future__ import annotations


def test_types_module_reexports_signature_facing_names() -> None:
    from xnano import _types
    from xnano import types as public_types

    for name in public_types.__all__:
        assert getattr(public_types, name) is getattr(_types, name)
