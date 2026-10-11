"""Private v1 effect lowering to current native effect specifications."""

from types import SimpleNamespace

from xnano import _xnano_core as core

TachyonFxEffect = core.Effect
TachyonFxMotion = SimpleNamespace(
    UpToDown='up_to_down',
    DownToUp='down_to_up',
    LeftToRight='left_to_right',
    RightToLeft='right_to_left',
)
TachyonFxColorSpace = SimpleNamespace(Rgb='rgb', Hsl='hsl', Hsv='hsv')
TachyonFxInterpolation = SimpleNamespace(
    Linear='linear',
    SmoothStep='smooth_step',
    Spring='spring',
    SineIn='sine_in',
    SineOut='sine_out',
    SineInOut='sine_in_out',
    QuadraticIn='quad_in',
    QuadraticOut='quad_out',
    QuadraticInOut='quad_in_out',
    CubicIn='cubic_in',
    CubicOut='cubic_out',
    CubicInOut='cubic_in_out',
    ExponentialIn='expo_in',
    ExponentialOut='expo_out',
    ExponentialInOut='expo_in_out',
    BounceIn='bounce_in',
    BounceOut='bounce_out',
    BounceInOut='bounce_in_out',
    ElasticIn='elastic_in',
    ElasticOut='elastic_out',
    ElasticInOut='elastic_in_out',
    BackIn='back_in',
    BackOut='back_out',
    BackInOut='back_in_out',
)
TachyonFxCellFilter = SimpleNamespace(
    All=core.CellFilter.all(),
    Text=core.CellFilter.text(),
    NonEmpty=core.CellFilter.non_empty(),
    Background=core.CellFilter.background(),
    BackgroundOnly=core.CellFilter.background_only(),
)


def tachyonfx_fade_to_foreground(foreground, duration, interpolation=None):
    return core.Effect.fade_to(
        foreground=foreground, duration_milliseconds=duration, interpolation=interpolation
    )


def tachyonfx_fade_to_background(background, duration, interpolation=None):
    return core.Effect.fade_to(
        background=background, duration_milliseconds=duration, interpolation=interpolation
    )


def tachyonfx_fade_to(foreground, background, duration, interpolation=None):
    return core.Effect.fade_to(
        foreground=foreground,
        background=background,
        duration_milliseconds=duration,
        interpolation=interpolation,
    )


def tachyonfx_fade_from_foreground(foreground, duration, interpolation=None):
    return core.Effect.fade_from(
        foreground=foreground, duration_milliseconds=duration, interpolation=interpolation
    )


def tachyonfx_fade_from_background(background, duration, interpolation=None):
    return core.Effect.fade_from(
        background=background, duration_milliseconds=duration, interpolation=interpolation
    )


def tachyonfx_fade_from(foreground, background, duration, interpolation=None):
    return core.Effect.fade_from(
        foreground=foreground,
        background=background,
        duration_milliseconds=duration,
        interpolation=interpolation,
    )


def tachyonfx_paint_foreground(foreground, duration, interpolation=None):
    return core.Effect.paint(
        foreground=foreground, duration_milliseconds=duration, interpolation=interpolation
    )


def tachyonfx_paint_background(background, duration, interpolation=None):
    return core.Effect.paint(
        background=background, duration_milliseconds=duration, interpolation=interpolation
    )


def tachyonfx_paint(foreground, background, duration, interpolation=None):
    return core.Effect.paint(
        foreground=foreground,
        background=background,
        duration_milliseconds=duration,
        interpolation=interpolation,
    )


def tachyonfx_dissolve(duration, interpolation=None):
    return core.Effect.dissolve(
        duration_milliseconds=duration, interpolation=interpolation
    )


def tachyonfx_coalesce(duration, interpolation=None):
    return core.Effect.coalesce(
        duration_milliseconds=duration, interpolation=interpolation
    )


def tachyonfx_sweep_in(
    direction, gradient_length, randomness, color, duration, interpolation=None
):
    return core.Effect.sweep_in(
        direction,
        gradient_length=gradient_length,
        randomness=randomness,
        color=color,
        duration_milliseconds=duration,
        interpolation=interpolation,
    )


def tachyonfx_sweep_out(
    direction, gradient_length, randomness, color, duration, interpolation=None
):
    return core.Effect.sweep_out(
        direction,
        gradient_length=gradient_length,
        randomness=randomness,
        color=color,
        duration_milliseconds=duration,
        interpolation=interpolation,
    )


def tachyonfx_slide_in(
    direction, gradient_length, randomness, color, duration, interpolation=None
):
    return core.Effect.slide_in(
        direction,
        gradient_length=gradient_length,
        randomness=randomness,
        color=color,
        duration_milliseconds=duration,
        interpolation=interpolation,
    )


def tachyonfx_slide_out(
    direction, gradient_length, randomness, color, duration, interpolation=None
):
    return core.Effect.slide_out(
        direction,
        gradient_length=gradient_length,
        randomness=randomness,
        color=color,
        duration_milliseconds=duration,
        interpolation=interpolation,
    )


def tachyonfx_sleep(duration):
    return core.Effect.sleep(duration)


def tachyonfx_sequence(effects):
    return core.Effect.sequence(effects)


def tachyonfx_parallel(effects):
    return core.Effect.parallel(effects)


def tachyonfx_repeat(effect, *, times=None, duration_milliseconds=None):
    return effect.repeated(times, milliseconds=duration_milliseconds)


def tachyonfx_delay(duration, effect):
    return effect.delayed(duration)
