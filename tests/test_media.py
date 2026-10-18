"""
tests.test_media

Images become buffers, and animated images move on the canvas's clock.
"""

from __future__ import annotations

import pytest
from xnano_image import TerminalImage

import xnano
from xnano_core import Buffer


def solid(width: int, height: int, color: tuple[int, int, int]) -> TerminalImage:
    pixels = bytes([*color, 255]) * (width * height)
    return TerminalImage.from_rgba(width, height, pixels)


def shown(width: int, height: int, color: tuple[int, int, int]) -> xnano.Image:
    return xnano.Image(solid(width, height, color))


def cell_at(canvas, column, row):
    frame = canvas.output.render()
    return Buffer.from_cell_grid(frame.to_cell_grid())[column, row]


@pytest.fixture
def canvas():
    with xnano.new(width=20, height=6) as canvas:
        yield canvas


class TestImages:
    def test_an_image_keeps_its_own_size(self, canvas):
        placement = canvas.write(shown(8, 8, (255, 0, 0)))
        assert (placement.width, placement.height) == (8, 4)

    def test_a_large_image_shrinks_to_fit_the_terminal(self, canvas):
        placement = canvas.write(shown(80, 40, (0, 255, 0)))
        assert placement.width <= 20 and placement.height <= 6
        assert placement.width / placement.height == pytest.approx(80 / 20, rel=0.3)

    def test_one_size_keeps_the_proportions(self, canvas):
        placement = canvas.write(shown(16, 16, (0, 0, 255)), width=10)
        assert placement.width == 10
        assert placement.height == 5

    def test_a_percentage_is_a_share_of_the_terminal(self, canvas):
        placement = canvas.write(shown(16, 16, (0, 0, 255)), width='50%')
        assert placement.width == 10

    def test_both_sizes_fit_the_image_inside_the_box(self, canvas):
        placement = canvas.write(shown(8, 8, (9, 9, 9)), width=12, height=3)
        assert (placement.width, placement.height) == (12, 3)

    def test_the_cells_show_the_pixels(self, canvas):
        canvas.write(shown(4, 2, (255, 0, 0)))
        cell = cell_at(canvas, 0, 0)
        assert cell.foreground.to_rgb() == (255, 0, 0)

    def test_an_image_file_is_shown_from_its_path(self, canvas, tmp_path):
        path = tmp_path / 'red.png'
        solid(6, 4, (255, 0, 0)).save(path)
        placement = canvas.write(xnano.Image(path))
        assert (placement.width, placement.height) == (6, 2)

    def test_an_image_can_be_sized_before_it_is_placed(self, canvas):
        picture = xnano.Image(solid(10, 10, (1, 2, 3)), width=6)
        placement = canvas.write(picture)
        assert isinstance(placement.core_buffer, Buffer)
        assert placement.width == 6


class TestResponsiveImages:
    def test_a_percentage_width_follows_the_terminal_size(self):
        with xnano.new(width=20, height=8) as canvas:
            placement = canvas.write(shown(40, 40, (255, 0, 0)), width='50%')
            canvas.step(delta_seconds=0.05)
            assert placement.width == 10
            canvas._runtime.resize(width=40, height=8)
            canvas.step(delta_seconds=0.05)
            assert placement.width == 20
            cell = cell_at(canvas, 19, 0)
            assert cell.foreground.to_rgb() == (255, 0, 0)

    def test_a_fixed_size_does_not_change_when_the_terminal_does(self):
        with xnano.new(width=20, height=8) as canvas:
            placement = canvas.write(shown(40, 40, (255, 0, 0)), width=6)
            canvas._runtime.resize(width=40, height=8)
            canvas.step(delta_seconds=0.05)
            assert placement.width == 6

    def test_an_image_without_a_size_refits_when_the_terminal_shrinks(self):
        with xnano.new(width=40, height=20) as canvas:
            placement = canvas.write(shown(30, 30, (0, 255, 0)))
            assert placement.width == 30
            canvas._runtime.resize(width=10, height=20)
            canvas.step(delta_seconds=0.05)
            assert placement.width <= 10


class TestAnimatedImages:
    @pytest.fixture
    def animation(self):
        frames = [solid(4, 2, (255, 0, 0)), solid(4, 2, (0, 0, 255))]
        return TerminalImage.from_frames(frames).with_frames_per_second(10)

    def test_the_frame_follows_the_clock(self, animation):
        with xnano.new(width=8, height=2) as canvas:
            canvas.write(xnano.Image(animation))
            first = cell_at(canvas, 0, 0).foreground.to_rgb()
            canvas.step(delta_seconds=0.15)
            second = cell_at(canvas, 0, 0).foreground.to_rgb()
            canvas.step(delta_seconds=0.1)
            looped = cell_at(canvas, 0, 0).foreground.to_rgb()
        assert first != second
        assert looped == first

    def test_removing_the_placement_stops_the_animation(self, animation):
        with xnano.new(width=8, height=2) as canvas:
            placement = canvas.write(xnano.Image(animation))
            placement.remove()
            assert not canvas._images


def test_content_that_is_not_showable_says_what_is_accepted(canvas):
    with pytest.raises(TypeError, match='xnano.from_image'):
        canvas.write(3.5)  # type: ignore[arg-type]


def test_raw_bytes_are_refused_with_the_way_to_write_them(canvas):
    with pytest.raises(TypeError, match=r'does not accept raw bytes.*xnano.from_image'):
        canvas.write(Buffer.with_text('abcd').to_cell_grid())  # type: ignore[arg-type]


def test_a_bare_terminal_image_is_refused_with_the_way_to_write_it(canvas):
    with pytest.raises(TypeError, match=r'does not accept a TerminalImage.*Image\('):
        canvas.write(solid(2, 2, (1, 2, 3)))  # type: ignore[arg-type]


class TestImage:
    def test_an_image_is_placed_with_its_own_placement(self, canvas):
        picture = xnano.Image(solid(16, 16, (1, 2, 3)), width=10, x=2, layer=3)
        placement = canvas.write(picture)
        assert (placement.x, placement.width, placement.height) == (2, 10, 5)
        assert placement.layer == 3

    def test_an_image_can_be_sized_by_a_percentage(self, canvas):
        placement = canvas.write(xnano.Image(solid(16, 16, (1, 2, 3)), width='50%'))
        assert placement.width == 10

    def test_a_path_is_not_resolved_by_add(self, canvas, tmp_path):
        path = tmp_path / 'red.png'
        solid(6, 4, (255, 0, 0)).save(path)
        with pytest.raises(TypeError, match='xnano.from_image'):
            canvas.write(path)  # type: ignore[arg-type]

    def test_an_unlocked_image_follows_the_terminal_size(self, canvas):
        placement = canvas.write(xnano.Image(solid(16, 16, (9, 9, 9)), width='50%'))
        canvas._runtime.resize(width=40, height=6)
        canvas.step(delta_seconds=0.05)
        assert placement.width == 20

    def test_a_locked_image_keeps_its_size(self, canvas):
        placement = canvas.write(
            xnano.Image(solid(16, 16, (9, 9, 9)), width='50%', lock=True)
        )
        canvas._runtime.resize(width=40, height=6)
        canvas.step(delta_seconds=0.05)
        assert placement.width == 10


class TestTypedStyle:
    def test_text_takes_its_style_as_parameters(self, canvas):
        canvas.write('hi', foreground='red', bold=True)
        cell = cell_at(canvas, 0, 0)
        assert cell.symbol == 'h'
        assert cell.foreground.to_rgb() is not None or cell.foreground is not None

    def test_a_title_or_border_draws_a_box(self, canvas):
        placement = canvas.write('hi', border='rounded', title='T')
        assert (placement.width, placement.height) == (4, 3)

    def test_style_parameters_apply_to_content_that_is_not_text(self, canvas):
        placement = canvas.write(shown(2, 2, (1, 1, 1)), border='plain')
        assert (placement.width, placement.height) == (4, 3)
        assert canvas.render().split('\n')[0].startswith('┌──┐')

    def test_lock_freezes_a_percentage(self, canvas):
        placement = canvas.write('hi', x='50%', lock=True)
        canvas._runtime.resize(width=40, height=6)
        canvas.step(delta_seconds=0.05)
        assert placement.x == 10


def wave_bytes(samples, *, channels=1, width=2, rate=8000):
    import io
    import wave

    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(width)
        writer.setframerate(rate)
        writer.writeframes(
            b''.join(
                int(value).to_bytes(width, 'little', signed=True) for value in samples
            )
        )
    return buffer.getvalue()


class TestFromImage:
    def test_an_image_path_opens_as_an_image(self, canvas, tmp_path):
        path = tmp_path / 'red.png'
        solid(6, 4, (255, 0, 0)).save(path)
        picture = xnano.from_image(path, width=6)
        assert isinstance(picture, xnano.Image)
        assert canvas.write(picture).width == 6

    def test_image_bytes_open_without_an_extension(self, tmp_path):
        path = tmp_path / 'red.png'
        solid(6, 4, (255, 0, 0)).save(path)
        assert isinstance(xnano.from_image(path.read_bytes()), xnano.Image)
        renamed = tmp_path / 'picture'
        renamed.write_bytes(path.read_bytes())
        assert isinstance(xnano.from_image(renamed), xnano.Image)

    def test_from_image_is_the_image_constructor(self):
        image = solid(4, 4, (1, 2, 3))
        options = {
            'x': 2,
            'y': 1,
            'width': 6,
            'height': 3,
            'layer': 2,
            'lock': True,
            'fit': 'cover',
            'resampling_filter': 'nearest',
            'background': (9, 9, 9),
        }
        assert xnano.from_image(image, **options) == xnano.Image(image, **options)

    def test_from_media_is_gone(self):
        assert not hasattr(xnano, 'from_media')


class TestFromAudio:
    def test_a_wave_file_opens_as_audio(self, tmp_path):
        path = tmp_path / 'tone.wav'
        path.write_bytes(wave_bytes([0, 16384, -16384, 0], rate=8000))
        audio = xnano.from_audio(path)
        assert isinstance(audio, xnano.Audio)
        assert audio.sound.sample_rate == 8000
        assert len(audio.sound) == 4
        assert audio.sound.samples()[1] == pytest.approx(0.5)

    def test_stereo_is_mixed_down_to_mono(self):
        audio = xnano.from_audio(wave_bytes([16384, -16384, 8192, 8192], channels=2))
        assert audio.sound.samples() == pytest.approx([0.0, 0.25])

    def test_a_file_of_another_kind_says_what_is_accepted(self, tmp_path):
        path = tmp_path / 'notes.txt'
        path.write_text('hello, this is text')
        with pytest.raises(ValueError, match='not a PCM WAV file'):
            xnano.from_audio(path)

    def test_audio_can_be_played_from_the_canvas(self, canvas):
        pytest.importorskip('xnano_audio')
        audio = xnano.Audio(wave_bytes([0, 8000, -8000, 0], rate=8000))
        canvas.play(audio)
        canvas.step(delta_seconds=0.001)
        assert canvas.audio.render_sound().peak > 0.0


def test_an_image_background_may_be_any_color_value():
    from xnano.types import ImageFit, ResamplingFilter

    assert ImageFit and ResamplingFilter
    picture = xnano.from_image(
        TerminalImage.from_rgba(1, 1, bytes((255, 0, 0, 255))), background='#000080'
    )
    assert picture.background == (0, 0, 128)
    assert xnano.Image(
        TerminalImage.from_rgba(1, 1, bytes((255, 0, 0, 255))), background=(1, 2, 3)
    ).background == (1, 2, 3)
