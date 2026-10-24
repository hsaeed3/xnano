"""
tests.test_optional_packages

`xnano` works without `xnano-audio` and `xnano-image`, and says how to install them.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

PRELUDE = """
import sys
sys.modules['xnano_audio'] = None
sys.modules['xnano_image'] = None
import xnano
"""


def run(body: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, '-c', PRELUDE + textwrap.dedent(body)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_xnano_imports_and_draws_without_the_optional_packages():
    result = run(
        """
        with xnano.new(width=8, height=1) as canvas:
            canvas.screen.write('ok')
            canvas.screen.output.render()
            print(canvas.screen.output.lines()[0])
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'ok'


@pytest.mark.parametrize(
    ('statement', 'extra'),
    [
        ('from xnano.audio import Microphone', 'audio'),
        ('xnano.audio.instrument_names()', 'audio'),
    ],
)
def test_using_a_module_of_a_missing_package_says_how_to_install_it(statement, extra):
    result = run(f'{statement}\n')
    assert result.returncode != 0
    assert f'pip install "xnano[{extra}]"' in result.stderr
    assert 'ImportError' in result.stderr


def test_the_directory_of_the_audio_module_lists_only_its_public_names():
    result = run(
        """
        import xnano.audio
        print(dir(xnano.audio) == sorted(xnano.audio.__all__))
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'True'


def test_the_audio_package_imports_without_the_audio_package():
    result = run(
        """
        import xnano.audio
        print(xnano.audio.Note('C4').pitch)
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'C4'


def test_a_note_can_be_defined_without_the_audio_package():
    result = run(
        """
        note = xnano.Note(['C4', 'E4'], beats=2.0, symbol='tone_extra')
        print(note.pitch, xnano.symbols.lookup('tone_extra') is note)
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "('C4', 'E4') True"


def test_playing_without_the_audio_package_says_how_to_install_it():
    result = run(
        """
        xnano.play(xnano.Note('C4'))
        """
    )
    assert result.returncode != 0
    assert 'pip install "xnano[audio]"' in result.stderr


def test_load_audio_says_how_to_install_it_and_load_image_too():
    result = run(
        """
        xnano.load_audio(b'RIFF')
        """
    )
    assert result.returncode != 0
    assert 'xnano.load_audio needs' in result.stderr
    assert 'pip install "xnano[audio]"' in result.stderr
    result = run(
        """
        xnano.load_image(b'x')
        """
    )
    assert result.returncode != 0
    assert 'xnano.load_image needs' in result.stderr
    assert 'xnano.Image' not in result.stderr
    assert 'pip install "xnano[image]"' in result.stderr


def test_the_region_of_a_note_works_without_the_audio_package():
    result = run(
        """
        region = xnano.Note(('C4', 'E4')).region
        print(region.height, region.milliseconds.width)
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ['5', '500.0']


def test_the_audio_of_a_canvas_says_how_to_install_it():
    result = run(
        """
        with xnano.new(width=8, height=1) as canvas:
            canvas.speaker.play('C4')
        """
    )
    assert result.returncode != 0
    assert (
        'The sound of a canvas (its speaker, microphone and beats) needs sound'
        in result.stderr
    )
    assert 'pip install "xnano[audio]"' in result.stderr


def test_showing_an_image_file_says_how_to_install_it(tmp_path):
    result = run(
        f"""
        import pathlib
        with xnano.new(width=8, height=1) as canvas:
            xnano.Image(pathlib.Path({str(tmp_path / 'x.png')!r}))
        """
    )
    assert result.returncode != 0
    assert 'pip install "xnano[image]"' in result.stderr


def test_everything_works_when_the_packages_are_installed():
    result = subprocess.run(
        [
            sys.executable,
            '-c',
            'import xnano; import xnano.audio, xnano_image; print(len(xnano.audio.instrument_names()) > 0, type(xnano.Image(xnano_image.TerminalImage.from_rgba(1, 1, bytes(4))).decoded).__name__)',
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert 'True' in result.stdout
    assert 'TerminalImage' in result.stdout
