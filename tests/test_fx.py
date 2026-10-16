"""Tests for typed customization, canvases, and operation piping."""

import dataclasses

import pytest

import xnano
import xnano_core
from xnano._hooks import HookHandle
from xnano.context import Context
from xnano.operations import fx
from xnano_core import Event


def render_text(buffer) -> str:
    return buffer.render(format='text')


def test_customize_returns_a_dataclass_operation() -> None:
    fill = fx('fill', cell='.')
    assert dataclasses.is_dataclass(fill)
    assert fill.cell == '.'
    assert isinstance(fill, xnano.operations.Customization)


def test_customize_rejects_unknown_parameters() -> None:
    with pytest.raises(TypeError):
        fx('fill', character='.')  # type: ignore[call-arg]


def test_a_customization_is_a_live_handle_on_the_canvas() -> None:
    with xnano.new('hello', width=6, height=1) as canvas:
        dots = fx('fill', cell='.')
        canvas.update(dots)
        assert isinstance(dots, xnano.operations.Customization)
        dots.cell = '#'
        assert '#' in canvas.render()
        dots.cell = '+'
        assert '+' in canvas.render()


def test_appearance_keywords_style_the_canvas_and_never_its_content() -> None:
    with pytest.raises(
        TypeError, match='style the canvas itself, not its content: border'
    ):
        xnano.new('hi', border='rounded')
    with xnano.new(width=6, height=3, border='rounded') as canvas:
        assert canvas.render().split('\n')[0] == '╭────╮'
        canvas.write('hi')
        assert canvas.render().split('\n')[1] == '│hi  │', (
            'content lives inside the border'
        )


def test_a_placement_changes_its_look_after_it_is_written() -> None:
    with xnano.new(width=20, height=8) as canvas:
        label = canvas.write('hi', border='rounded', padding={'horizontal': 1})
        assert (label.width, label.height) == (6, 3)
        label.border = 'double'
        label.padding = 2
        label.text = 'hello'
        assert (label.width, label.height) == (11, 7)
        canvas.iter(count=1).__next__()
        assert '╔' in canvas.core_buffer.render(format='text')
        assert label.border.kind == 'double'


def test_margin_adds_space_outside_the_box() -> None:
    with xnano.new(width=12, height=6) as canvas:
        label = canvas.write('hi', border='plain', margin={'left': 2, 'top': 1})
        assert (label.width, label.height) == (6, 4)


def test_a_widget_takes_a_border_like_text_does() -> None:
    with xnano.new(width=12, height=5) as canvas:
        gauge = canvas.write(
            xnano_core.Gauge(ratio=0.5, width=10, height=1), border='plain'
        )
        assert (gauge.width, gauge.height) == (12, 3)
        assert canvas.render().split('\n')[0] == '┌──────────┐'
        gauge.border.color = 'red'
        gauge.border = False
        assert (gauge.width, gauge.height) == (10, 1)
        assert '┌' not in canvas.render()


def test_a_widget_can_take_a_look_after_it_was_written() -> None:
    with xnano.new(width=12, height=3) as canvas:
        gauge = canvas.write(xnano_core.Gauge(ratio=0.5, width=10, height=1))
        gauge.border = 'plain'
        assert (gauge.width, gauge.height) == (12, 3)
        assert canvas.render().split('\n')[0] == '┌──────────┐'


def test_an_effect_handle_restarts_the_effect_with_new_values() -> None:
    with xnano.new(width=10, height=1) as canvas:
        label = canvas.write('abc')
        effect = fx('effect.dissolve', duration_milliseconds=100)
        label.update(effect)
        key = effect.key
        assert key is not None
        effect.duration_milliseconds = 400
        assert effect.key == key
        assert effect.duration_milliseconds == 400


def test_canvas_pipes_a_customization() -> None:
    with xnano.new('x', width=4, height=1) as canvas:
        assert (canvas | fx('fill', cell='.')) is canvas
        assert isinstance(canvas, xnano.canvas.Canvas)
        assert '.' in canvas.render()


def test_open_explains_the_keywords_it_refuses_before_taking_the_screen() -> None:
    with xnano.new('hi', width=10, height=2, deps={'name': 'app'}) as canvas:
        with pytest.raises(TypeError, match='takes no realtime'):
            xnano.open(canvas, realtime=True)  # type: ignore[call-overload]
        with pytest.raises(TypeError, match='deps was already given to xnano.new'):
            xnano.open(canvas, deps={'name': 'other'})
        with pytest.raises(ValueError, match='needs a height too'):
            xnano.open(canvas, width=10)
        assert not isinstance(canvas, xnano.Terminal)
        assert xnano.terminal._live_terminal_open is False


def test_open_given_content_styles_the_canvas_only_without_content() -> None:
    with pytest.raises(TypeError, match='style the canvas itself'):
        xnano.open('text', border='rounded')
    assert xnano.terminal._live_terminal_open is False


def test_a_canvas_has_no_fx_method_and_pipe_returns_the_canvas() -> None:
    with xnano.new(width=8, height=2) as canvas:
        assert not hasattr(canvas, 'fx')
        assert (canvas | fx('fill', cell='.')) is canvas
        label = canvas.write('hi')
        assert not hasattr(label, 'fx')


def test_nested_placement_follows_a_drag_hook() -> None:
    with xnano.new(width=20, height=3) as canvas:
        track = canvas.write(' ' * 10, y=1)
        thumb = track.write('█', x=(0, track.width - 1), y=0)

        @thumb.hook(on='drag')
        def slide(context: xnano.context.Context):
            while context.mouse.is_down:
                thumb.x = context.parent.local(context.mouse.position).x
                context = yield

        canvas.push(Event.mouse_event(column=0, row=1, kind='press', button='left'))
        canvas.push(Event.mouse_event(column=5, row=1, kind='drag', button='left'))
        canvas.deliver_events()
        assert thumb.x == 5


def test_expression_scopes_on_placements() -> None:
    with xnano.new(width=20, height=3) as canvas:
        ball = canvas.write('o')
        ball.x = (ball.parent.width - ball.width) * ((ball.root.time / 2.0) % 1.0)
        ball.x = (canvas.width - ball.width) * ((canvas.time / 2.0) % 1.0)


def test_a_frame_hook_runs_on_every_frame() -> None:
    calls: list[int] = []
    with xnano.new(width=8, height=2) as canvas:

        @canvas.hook(on='frame')
        def record(context: xnano.context.Context) -> None:
            calls.append(1)

        assert isinstance(record, HookHandle)
        for _ in canvas.iter(count=2):
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

    assert set(_CUSTOMIZATION_TYPES) <= set(xnano_core.Customization.kinds())
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
        ('layout', xnano_core.Layout, {}),
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


def test_customization_is_a_native_operation_that_sequences() -> None:
    fill = xnano_core.Customization('fill', cell='.')
    border = xnano_core.Customization('border', border_kind='rounded')
    buffer = xnano_core.Buffer(width=6, height=3)
    buffer.update(fill | border)
    text = buffer.render(format='text')
    assert '╭' in text
    assert '.' in text
    assert isinstance(fill | xnano_core.Style('red'), xnano_core.Operation)


def test_editing_a_field_changes_what_the_customization_does() -> None:
    fill = fx('fill', cell='.')
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
    shader = fx('pixels', shader=lambda column, row: (255, 0, 0))
    chained = shader | fx('fill', cell='.')
    assert isinstance(chained, xnano_core.OperationChain)
    buffer = xnano_core.Buffer(width=2, height=1)
    buffer.update(chained)


def test_triggers_decide_events_natively() -> None:
    press = xnano_core.Event.key_press('q')
    assert xnano_core.Trigger.key('q', 'escape').matches(press)
    assert not xnano_core.Trigger.key('x').matches(press)
    assert xnano_core.Trigger.key().matches(press)
    assert not xnano_core.Trigger.click().matches(press)
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
    shaped = sound | fx('audio.reverb', mix=0.3)
    assert isinstance(shaped, TerminalSound)


def test_xnano_hook_makes_a_reusable_operation() -> None:
    ticks: list[float] = []

    @xnano.hook(on='tick', every=0.1)
    def tick(context: Context) -> None:
        ticks.append(round(context.time.elapsed, 1))

    assert isinstance(tick, xnano.operations.ContextualOperation)
    assert (tick.on, tick.every) == ('tick', 0.1)
    with xnano.new(width=8, height=1) as first, xnano.new(width=8, height=1) as second:
        first | tick
        second | tick
        first.step(delta_seconds=0.25)
        second.step(delta_seconds=0.15)
    assert len(ticks) == 3
    assert not hasattr(xnano, 'operation')


def test_a_hook_returning_an_operation_applies_it() -> None:
    with xnano.new(width=8, height=1) as canvas:
        label = canvas.write('hi')

        @label.hook(on='tick', after=0.0)
        def tint(context: Context) -> xnano_core.Operation:
            return xnano_core.Fill('x')

        canvas.step(delta_seconds=0.1)
        assert canvas.render().startswith('xx')


def test_a_hook_returning_content_is_refused() -> None:
    with pytest.raises(xnano.errors.TerminalError, match='cannot return content'):
        with xnano.new(width=8, height=1) as canvas:

            @canvas.hook(on='tick', after=0.0)
            def draw(context: Context) -> str:
                return 'text'

            canvas.step(delta_seconds=0.1)
