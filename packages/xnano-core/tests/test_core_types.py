"""The Python objects and aliases that live next to the compiled module."""

from __future__ import annotations

import typing

import pytest

from xnano_core._xnano_core import Buffer, Runtime, Write
from xnano_core._xnano_core import _core_types as core_types


def test_hook_signals_share_one_base():
    for signal in (
        core_types.Skip,
        core_types.Invalidate,
        core_types.Stop,
        core_types.Propagate,
    ):
        assert issubclass(signal, core_types.HookSignal)


def test_literal_aliases_list_their_values():
    assert typing.get_args(core_types.MouseButton) == ('left', 'right', 'middle')
    assert 'light_blue' in typing.get_args(core_types.ColorName)
    assert {'enter', 'escape', 'page_up', 'f12', 'q'} <= set(
        typing.get_args(core_types.KeyName)
    )
    assert typing.get_args(core_types.BorderKind) == (
        'plain',
        'rounded',
        'double',
        'thick',
    )


def test_every_color_and_key_name_is_accepted_by_the_native_parsers():
    from xnano_core._xnano_core import Color, KeyBinding

    for name in typing.get_args(core_types.ColorName):
        Color(name)
    for name in typing.get_args(core_types.KeyName):
        KeyBinding.parse(name)
    KeyBinding.parse('ctrl+shift+z')


def test_registry_copies_are_independent():
    registry = core_types.Registry()
    registry.register(Write, lambda context, operation: None)
    duplicate = registry.copy()
    duplicate.register(core_types.Registry, lambda context, operation: None)
    assert registry.supports(Write) and duplicate.supports(Write)
    assert not registry.supports(core_types.Registry)


def test_the_default_registry_is_shared():
    assert core_types.default_registry() is core_types.default_registry()


def test_rendering_serializes_without_a_runtime():
    buffer = Buffer(width=4, height=1)
    buffer.update(Write('hi'))
    assert 'hi' in str(buffer())


def test_rendering_mounts_and_unmounts_on_a_given_runtime():
    with Runtime.offscreen(width=10, height=3) as runtime:
        buffer = Buffer(width=4, height=1)
        with buffer(runtime=runtime) as context:
            assert isinstance(context, core_types.CoreContext)
            assert context.runtime is runtime
        assert not runtime.is_closed


def test_evaluation_contexts_work_offline():
    context = core_types.EvaluationContext(buffer=Buffer(width=3, height=1))
    context.update(Write('ab'))
    assert context.buffer.text == 'ab'
    assert context.runtime is None and context.device is None


def test_core_context_rejects_a_missing_runtime():
    context = core_types.CoreContext(
        buffer=Buffer(width=1, height=1), runtime=typing.cast(Runtime, None)
    )

    with pytest.raises(RuntimeError, match='EvaluationContext'):
        assert context.runtime is not None


def test_event_context_rejects_a_missing_event():
    context = core_types.EventContext(
        buffer=Buffer(width=1, height=1), runtime=typing.cast(Runtime, None)
    )

    with pytest.raises(RuntimeError, match='active event hook'):
        assert context.event is not None


def test_unsupported_operations_name_the_recovery():
    from xnano_core._xnano_core import UnsupportedOperationError

    with pytest.raises(UnsupportedOperationError, match='registry.install'):
        core_types.Registry().resolve(Write('x'))
