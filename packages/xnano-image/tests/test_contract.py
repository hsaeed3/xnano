"""
Stub-driven contract tests: the ``.pyi`` is the documented surface.

Every name exists both ways, every call returns the type its annotation
promises (a ``str`` is a ``str``, never a dict or a Rust debug dump), every
public item is documented, and the signatures match the stub, including which
arguments are keyword-only.
"""

from __future__ import annotations

import builtins
import inspect
from typing import Any, cast

import pytest
from helpers import CLASSES, FUNCTIONS, STUB, animation, gradient, matches, solid

import xnano_image
import xnano_image._xnano_image as native
from xnano_image import (
    TerminalGraphics,
    TerminalImage,
    cell_grid_size,
    cell_grid_to_ansi,
    cell_grid_to_text,
)

ERRORS = ('TerminalImageError', 'TerminalQueryError')


def test_every_stubbed_name_exists_at_runtime():
    for name in (*CLASSES, *FUNCTIONS):
        assert hasattr(native, name), name
    for name, stub_class in CLASSES.items():
        for method in stub_class.methods:
            if method.startswith('__') and method != '__init__':
                continue
            assert hasattr(getattr(native, name), method), f'{name}.{method}'


def test_every_runtime_name_is_stubbed():
    stubbed = {*CLASSES, *FUNCTIONS}
    for name in dir(native):
        if name.startswith('_'):
            continue
        value = getattr(native, name)
        if inspect.isclass(value) or inspect.isroutine(value):
            assert name in stubbed, f'{name} has no stub'
    for name, stub_class in CLASSES.items():
        if name in ERRORS:
            continue
        for method in vars(getattr(native, name)):
            if not method.startswith('_'):
                assert method in stub_class.methods, f'{name}.{method} has no stub'


def test_runtime_signatures_match_the_stub():
    def runtime_parameters(function):
        signature = inspect.signature(function)
        positional = [
            parameter.name
            for parameter in signature.parameters.values()
            if parameter.kind
            in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
            and parameter.name != 'self'
        ]
        keyword_only = [
            parameter.name
            for parameter in signature.parameters.values()
            if parameter.kind == parameter.KEYWORD_ONLY
        ]
        return positional, keyword_only

    checked = 0
    for name, stub_class in CLASSES.items():
        if name in ERRORS:
            continue
        for method_name, stub in stub_class.methods.items():
            if method_name.startswith('__') or stub.is_property:
                continue
            function = getattr(getattr(native, name), method_name)
            assert runtime_parameters(function) == (
                stub.positional_parameters,
                stub.keyword_only_parameters,
            ), f'{name}.{method_name}'
            checked += 1
    for name, stub in FUNCTIONS.items():
        assert runtime_parameters(getattr(native, name)) == (
            stub.positional_parameters,
            stub.keyword_only_parameters,
        ), name
        checked += 1
    assert checked > 30


def test_package_exports_match_the_stub():
    assert set(xnano_image.__all__) == {
        *CLASSES,
        *FUNCTIONS,
        '__version__',
    }
    for name in xnano_image.__all__:
        assert getattr(xnano_image, name) is getattr(native, name)


def test_package_docstring_lists_every_public_name():
    for name in xnano_image.__all__:
        if name != '__version__':
            assert name in (xnano_image.__doc__ or ''), name


def test_classes_report_the_public_module():
    for name in CLASSES:
        assert getattr(native, name).__module__ == 'xnano_image._xnano_image', name


def test_error_hierarchy():
    assert issubclass(native.TerminalImageError, ValueError)
    assert issubclass(native.TerminalQueryError, OSError)
    assert not issubclass(native.TerminalQueryError, ValueError)


def test_every_public_item_is_documented():
    missing = [name for name, stub_class in CLASSES.items() if not stub_class.doc]
    for name, stub_class in CLASSES.items():
        missing += [
            f'{name}.{method.name}'
            for method in stub_class.methods.values()
            if not method.name.startswith('__') and not method.doc
        ]
    missing += [name for name, function in FUNCTIONS.items() if not function.doc]
    assert missing == []


def test_raises_sections_name_real_exception_types():
    for stub_class in CLASSES.values():
        for method in stub_class.methods.values():
            for line in (method.doc or '').splitlines():
                token = line.strip().split(':')[0]
                if token.endswith('Error') and token[:1].isupper() and ' ' not in token:
                    assert hasattr(native, token) or hasattr(builtins, token), (
                        f'{stub_class.name}.{method.name} documents unknown {token}'
                    )


def test_docstrings_use_mkdocs_cross_references_only():
    text = STUB.read_text(encoding='utf-8') + (xnano_image.__doc__ or '')
    for role in (':class:', ':meth:', ':func:', ':mod:', ':attr:'):
        assert role not in text, role


# ------------------------------------------------------ return types vs stub


def check(value, name: str, owner: str | None = None):
    stub = CLASSES[owner].methods[name] if owner else FUNCTIONS[name]
    assert stub.returns, f'{owner}.{name} has no return annotation'
    assert matches(value, stub.returns), (
        f'{owner or "module"}.{name} returned {value!r} ({type(value).__name__}); '
        f'stub says {stub.returns}'
    )


@pytest.fixture(scope='module')
def clip():
    return animation(3, 6, 4)


def test_image_properties_have_stub_types(clip):
    for name in (
        'width',
        'height',
        'frame_count',
        'duration_milliseconds',
        'is_animated',
        'is_opaque',
    ):
        check(getattr(clip, name), name, 'TerminalImage')
    for name in ('width', 'height', 'frame_count', 'duration_milliseconds'):
        assert type(getattr(clip, name)) is int, name
    assert type(clip.is_animated) is bool and type(clip.is_opaque) is bool


def test_image_methods_have_stub_types(clip):
    check(clip.frame_durations(), 'frame_durations', 'TerminalImage')
    check(clip.frame_index_at(10.0), 'frame_index_at', 'TerminalImage')
    check(clip.to_rgba(1), 'to_rgba', 'TerminalImage')
    check(len(clip), '__len__', 'TerminalImage')
    check(repr(clip), '__repr__', 'TerminalImage')
    check(clip.encode('gif'), 'encode', 'TerminalImage')
    check(clip.to_xni(), 'to_xni', 'TerminalImage')
    check(clip.to_cell_grid(4, 2), 'to_cell_grid', 'TerminalImage')
    check(clip.to_cell_grids(4, 2), 'to_cell_grids', 'TerminalImage')
    check(clip.to_cell_animation(4, 2), 'to_cell_animation', 'TerminalImage')
    check(clip.to_ansi(4, 2), 'to_ansi', 'TerminalImage')


TRANSFORMS = {
    'resize': lambda image: image.resize(3, 3),
    'scale': lambda image: image.scale(0.5),
    'crop': lambda image: image.crop(0, 0, 2, 2),
    'fit_to_canvas': lambda image: image.fit_to_canvas(8, 8),
    'focal_crop': lambda image: image.focal_crop(3, 3),
    'flatten': lambda image: image.flatten((1, 2, 3)),
    'quantize': lambda image: image.quantize(8),
    'first_frames': lambda image: image.first_frames(2),
    'still_frame': lambda image: image.still_frame(1),
    'with_frames_per_second': lambda image: image.with_frames_per_second(10.0),
    'with_speed': lambda image: image.with_speed(2.0),
}


def test_every_stubbed_transform_is_covered_here():
    transforms = {
        name
        for name, method in CLASSES['TerminalImage'].methods.items()
        if method.returns == 'TerminalImage' and not name.startswith('__')
    }
    assert transforms - {
        'open',
        'from_bytes',
        'from_rgba',
        'from_xni',
        'from_frames',
    } == set(TRANSFORMS)


@pytest.mark.parametrize('name', TRANSFORMS)
def test_transforms_return_images(clip, name):
    check(TRANSFORMS[name](clip), name, 'TerminalImage')


def test_constructors_return_images(clip, tmp_path):
    path = tmp_path / 'a.png'
    clip.save(str(path))
    check(TerminalImage.open(str(path)), 'open', 'TerminalImage')
    check(TerminalImage.open(path), 'open', 'TerminalImage')
    check(TerminalImage.from_bytes(clip.encode('png')), 'from_bytes', 'TerminalImage')
    check(TerminalImage.from_rgba(1, 1, b'\0\0\0\xff'), 'from_rgba', 'TerminalImage')
    check(TerminalImage.from_xni(clip.to_xni()), 'from_xni', 'TerminalImage')
    check(TerminalImage.from_frames([clip, clip]), 'from_frames', 'TerminalImage')
    assert clip.save(str(tmp_path / 'b.gif')) is None


def test_cell_grid_helpers_return_stub_types(clip):
    grid = clip.to_cell_grid(4, 2)
    check(cell_grid_size(grid), 'cell_grid_size')
    check(cell_grid_to_text(grid), 'cell_grid_to_text')
    check(cell_grid_to_ansi(grid), 'cell_grid_to_ansi')
    assert cell_grid_size(grid) == (4, 2)
    assert all(type(side) is int for side in cell_grid_size(grid))


def test_terminal_graphics_have_stub_types():
    graphics = TerminalGraphics.half_blocks()
    check(graphics, 'half_blocks', 'TerminalGraphics')
    check(graphics.protocol, 'protocol', 'TerminalGraphics')
    check(graphics.cell_size_in_pixels, 'cell_size_in_pixels', 'TerminalGraphics')
    check(graphics.capabilities, 'capabilities', 'TerminalGraphics')
    check(repr(graphics), '__repr__', 'TerminalGraphics')
    check(graphics.with_protocol('sixel'), 'with_protocol', 'TerminalGraphics')
    check(
        TerminalGraphics.from_capabilities(protocol='kitty', cell_size_in_pixels=(8, 16)),
        'from_capabilities',
        'TerminalGraphics',
    )
    for protocol in ('half_blocks', 'sixel', 'kitty', 'iterm2'):
        check(graphics.with_protocol(protocol).protocol, 'protocol', 'TerminalGraphics')


def test_signatures_accept_every_stub_keyword():
    image = gradient(8, 8)
    image.resize(width=4, height=4, resampling_filter='nearest')
    image.scale(factor=0.5, resampling_filter='bilinear')
    image.crop(left=0, top=0, width=2, height=2)
    image.fit_to_canvas(width=4, height=4, background=(1, 2, 3), left=0, top=0)
    image.focal_crop(
        width=4,
        height=4,
        scale=2.0,
        left=1,
        top=1,
        background=(0, 0, 0),
        resampling_filter='catmull_rom',
    )
    image.flatten(background=(0, 0, 0))
    image.quantize(colors=4, should_dither=True)
    image.frame_index_at(elapsed_milliseconds=5.0, should_loop=False)
    image.to_cell_grid(
        columns=4,
        rows=2,
        fit='stretch',
        horizontal_pixels_per_cell=2,
        should_correct_aspect_ratio=True,
        background=(1, 2, 3),
        resampling_filter='catmull_rom',
        frame_index=0,
        graphics=TerminalGraphics.half_blocks(),
    )
    image.to_cell_animation(
        columns=4,
        rows=2,
        should_loop=False,
        fit='cover',
        horizontal_pixels_per_cell=1,
        should_correct_aspect_ratio=False,
        background=(0, 0, 0),
        resampling_filter='nearest',
        graphics=None,
    )
    image.to_xni(colors=4)
    image.to_ansi(columns=4, rows=2, fit='cover', frame_index=0)
    image.to_cell_grids(columns=4, rows=2)
    image.first_frames(count=1)
    image.still_frame(frame_index=0)
    image.with_frames_per_second(frames_per_second=5.0)
    image.with_speed(factor=2.0)
    image.to_rgba(frame_index=0)
    image.encode(image_format='gif')
    TerminalImage.from_rgba(1, 1, b'\0\0\0\xff', duration_milliseconds=40)


def test_options_after_the_subject_are_keyword_only():
    image = gradient(8, 8)
    calls = [
        lambda: image.resize(4, 4, 'nearest'),
        lambda: image.scale(0.5, 'nearest'),
        lambda: image.fit_to_canvas(4, 4, (0, 0, 0)),
        lambda: image.focal_crop(4, 4, 2.0),
        lambda: image.quantize(8, True),
        lambda: image.frame_index_at(5.0, False),
        lambda: image.to_cell_grid(4, 2, 'stretch'),
        lambda: image.to_cell_animation(4, 2, False),
        lambda: cast(Any, TerminalImage).from_rgba(1, 1, b'\0\0\0\xff', 40),
        lambda: cast(Any, TerminalGraphics).from_capabilities('kitty', (8, 16)),
    ]
    for call in calls:
        with pytest.raises(TypeError):
            call()


def test_resampling_filter_names_in_the_docs_are_real():
    image = gradient(8, 8)
    for name in ('nearest', 'bilinear', 'catmull_rom', 'lanczos3'):
        image.resize(4, 4, resampling_filter=name)
    with pytest.raises(native.TerminalImageError, match='resampling_filter'):
        image.resize(4, 4, resampling_filter='bogus')


def test_solid_helper_sanity():
    assert solid(2, 2).is_opaque and not solid(2, 2, alpha=0).is_opaque
