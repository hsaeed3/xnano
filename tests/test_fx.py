"""Tests for typed customization, canvases, and operation piping."""

import dataclasses

import pytest

import xnano
import xnano_core
from xnano.context import Context
from xnano.operations import draggable


def render_text(buffer) -> str:
    return buffer.render(format='text')


def test_customize_returns_a_dataclass_operation() -> None:
    style = xnano.fx('style', bold=True)
    assert dataclasses.is_dataclass(style)
    assert style.bold is True
    assert isinstance(style, xnano.operations.Customization)


def test_customize_rejects_unknown_parameters() -> None:
    with pytest.raises(TypeError):
        xnano.fx('fill', character='.')  # type: ignore[call-arg]


def test_canvas_customize_returns_the_canvas_and_draws_the_border() -> None:
    canvas = xnano.new('hello', width=12, height=3)
    assert canvas.fx('border', border_kind='rounded') is canvas
    assert '╭' in render_text(canvas.build())


def test_canvas_pipes_a_customization() -> None:
    canvas = xnano.new('x', width=4, height=1) | xnano.fx('fill', cell='.')
    assert isinstance(canvas, xnano.canvas.Canvas)
    assert '.' in render_text(canvas.build())


def test_open_mounts_a_canvas_and_uses_its_size() -> None:
    with xnano.iter(xnano.new('hi', width=10, height=2), offscreen=True) as terminal:
        assert terminal.size.width == 10
        assert terminal.size.height == 2


def test_open_rejects_something_that_is_not_a_canvas() -> None:
    with pytest.raises(TypeError):
        xnano.iter('text', offscreen=True)  # type: ignore[call-overload]


def test_terminal_customize_and_pipe_return_the_terminal() -> None:
    with xnano.iter(offscreen=True, width=8, height=2) as terminal:
        assert terminal.fx('style', foreground='cyan') is terminal
        assert (terminal | xnano.fx('fill', cell='.')) is terminal


def test_nested_placement_is_draggable() -> None:
    with xnano.iter(offscreen=True, width=20, height=3) as terminal:
        track = terminal.write(' ' * 10, y=1)
        thumb = track.write('█', x=(0, track.width - 1), y=0) | draggable()
        assert isinstance(thumb, xnano.placement.Placement)


def test_expression_scopes_on_placements() -> None:
    with xnano.iter(offscreen=True, width=20, height=3) as terminal:
        ball = terminal.write('o')
        ball.x = (ball.parent.width - ball.width) * ((ball.root.time / 2.0) % 1.0)
        ball.x = (terminal.width - ball.width) * ((terminal.time / 2.0) % 1.0)


def test_terminal_hook_with_a_trigger_mounts_a_contextual_operation() -> None:
    calls: list[int] = []
    with xnano.iter(offscreen=True, width=8, height=2) as terminal:

        @terminal.hook(on='frame')
        def record(context: xnano.context.Context) -> None:
            calls.append(1)

        assert isinstance(record, xnano.operations.ContextualOperation)
        for _ in terminal.loop.frames(count=2):
            pass
    assert calls


def signature_parameters(callable_object: object) -> list[str]:
    """The parameter names of a native constructor, read from its text signature."""
    text = getattr(callable_object, '__text_signature__', None)
    assert text, f'{callable_object!r} has no text signature'
    names = []
    for part in text.strip('()').split(','):
        name = part.split('=')[0].strip().lstrip('*')
        if name and name not in ('$self', '/'):
            names.append(name)
    return names


def test_every_kind_has_a_dataclass_with_matching_defaults() -> None:
    from xnano._customize import _CUSTOMIZATION_TYPES

    assert set(xnano_core.Customization.kinds()) == set(_CUSTOMIZATION_TYPES)
    for kind, customization_class in _CUSTOMIZATION_TYPES.items():
        native = xnano_core.Customization.defaults(kind)
        fields = {
            field.name: field.default for field in dataclasses.fields(customization_class)
        }
        assert set(native) == set(fields), kind
        for name, default in native.items():
            assert fields[name] == default, (kind, name)


@pytest.mark.parametrize(
    ('kind', 'target', 'renamed'),
    [
        ('style', xnano_core.Style, {}),
        ('block', xnano_core.Block, {}),
        ('border', xnano_core.Border, {'kind': 'border_kind'}),
        ('layout', xnano_core.Layout, {}),
        ('margin', xnano_core.Margin, {}),
        ('write', xnano_core.Write, {}),
        ('fill', xnano_core.Fill, {}),
        ('fuzz', xnano_core.Fuzz, {}),
        ('raster', xnano_core.Raster, {}),
        ('pixels', xnano_core.Pixels, {}),
    ],
)
def test_customize_reaches_every_parameter_of_the_core_constructor(
    kind: str, target: object, renamed: dict[str, str]
) -> None:
    reachable = set(xnano_core.Customization.defaults(kind))
    for name in signature_parameters(target):
        assert renamed.get(name, name) in reachable or name in reachable, (kind, name)


def test_customize_reaches_every_effect_constructor() -> None:
    combinators = {'consume_tick', 'term256_colors', 'parallel', 'sequence'}
    reachable = set(xnano_core.Customization.kinds())
    for name in dir(xnano_core.Effect):
        member = getattr(xnano_core.Effect, name)
        text = getattr(member, '__text_signature__', None)
        if name.startswith('_') or not text or '$self' in text or name in combinators:
            continue
        assert f'effect.{name}' in reachable, name
        parameters = xnano_core.Customization.defaults(f'effect.{name}')
        for parameter in signature_parameters(member):
            assert parameter in parameters, (name, parameter)


def test_style_accepts_every_modifier_without_prefixed_aliases() -> None:
    parameters = xnano_core.Customization.defaults('style')
    assert not [name for name in parameters if name.startswith('is_')]
    style = xnano.fx('style', rapid_blink=True, underline_color='red').build()
    assert 'rapid_blink' in style.modifiers
    assert style.underline_color is not None


def test_customization_is_a_native_operation_that_sequences() -> None:
    fill = xnano_core.Customization('fill', cell='.')
    border = xnano.fx('border', border_kind='rounded')
    buffer = xnano_core.Buffer(width=6, height=3)
    buffer.update(fill | border)
    text = buffer.render(format='text')
    assert '╭' in text
    assert '.' in text
    assert isinstance(fill | xnano_core.Style('red'), xnano_core.Operation)


def test_editing_a_field_changes_what_the_customization_does() -> None:
    fill = xnano.fx('fill', cell='.')
    fill.cell = '#'
    buffer = xnano_core.Buffer(width=3, height=1)
    buffer | fill
    assert buffer.text.startswith('###')


def test_customization_errors_say_how_to_recover() -> None:
    with pytest.raises(ValueError, match='Choose one of'):
        xnano_core.Customization('bogus').build()
    with pytest.raises(TypeError, match='Its parameters are'):
        xnano_core.Customization('style', bogus=1).build()
    with pytest.raises(AttributeError, match='provides: width, height, size'):
        xnano.expressions.Parent.depth  # noqa: B018


def test_mixed_operations_chain_in_order() -> None:
    shader = xnano.fx('pixels', shader=lambda column, row: (255, 0, 0))
    chained = shader | xnano.fx('fill', cell='.')
    assert isinstance(chained, xnano_core.OperationChain)
    buffer = xnano_core.Buffer(width=2, height=1)
    buffer.update(chained)


def test_triggers_decide_events_natively() -> None:
    press = xnano_core.Event.key_press('q')
    assert xnano_core.Trigger.key('q', 'escape').matches(press)
    assert not xnano_core.Trigger.key('x').matches(press)
    assert xnano_core.Trigger.key().matches(press)
    assert not xnano_core.Trigger.click().matches(press)
    assert xnano_core.Trigger.every(0.5).seconds == 0.5
    assert xnano_core.Trigger.named('click') == xnano_core.Trigger.click()
    with pytest.raises(ValueError, match='Use one of'):
        xnano_core.Trigger.named('sometimes')
    with pytest.raises(ValueError, match='key binding'):
        xnano_core.Trigger.key('ctrl+')


def test_scopes_are_native_expressions() -> None:
    assert xnano.expressions.Parent.width is xnano_core.ParentWidth
    assert xnano.expressions.Root.time is xnano_core.TimeElapsed
    assert xnano.expressions.BufferExpressions.size is xnano_core.BufferSize


def test_audio_customization_chains_onto_sounds() -> None:
    pytest.importorskip('xnano_audio')
    from xnano_audio import TerminalSound

    sound = TerminalSound.from_samples([0.0, 0.5, -0.5, 0.25] * 64, sample_rate=8000)
    shaped = sound | xnano.fx('audio.reverb', mix=0.3)
    assert isinstance(shaped, TerminalSound)


def test_xnano_hook_makes_a_reusable_operation() -> None:
    @xnano.hook(on='frame')
    def banner(context: Context) -> str:
        return f'w={context.width}'

    assert isinstance(banner, xnano.operations.ContextualOperation)
    with xnano.iter(offscreen=True, width=8, height=1) as terminal:
        assert terminal.write(banner).text == 'w=8'
    assert not hasattr(xnano, 'operation')


def test_a_hook_on_a_clock_returns_the_operation_and_an_event_hook_the_handle() -> None:
    ticks: list[float] = []
    with xnano.iter(offscreen=True, width=8, height=1) as terminal:

        @terminal.hook(every=0.1)
        def tick(context: Context) -> None:
            ticks.append(context.time.elapsed)

        handle = terminal.hook(lambda context: None, when=xnano_core.Trigger.key('q'))
        terminal.loop.advance(0.35)
    assert isinstance(tick, xnano.operations.ContextualOperation)
    assert ticks
    assert hasattr(handle, 'remove')
