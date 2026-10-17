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
            canvas.write('ok')
            canvas.output.render()
            print(canvas.output.snapshot().lines()[0])
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'ok'


@pytest.mark.parametrize(
    ('statement', 'extra'),
    [
        ('import xnano.audio', 'audio'),
        ('import xnano.image', 'image'),
    ],
)
def test_using_a_module_of_a_missing_package_says_how_to_install_it(statement, extra):
    result = run(f'{statement}\n')
    assert result.returncode != 0
    assert f'pip install "xnano[{extra}]"' in result.stderr
    assert 'ImportError' in result.stderr


def test_a_note_can_be_defined_without_the_audio_package():
    result = run(
        """
        note = xnano.note(['C4', 'E4'], beats=2.0, symbol='tone_extra')
        print(note.pitch, xnano.symbols.lookup('tone_extra') is note)
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "('C4', 'E4') True"


def test_playing_without_the_audio_package_says_how_to_install_it():
    result = run(
        """
        xnano.play(xnano.note('C4'))
        """
    )
    assert result.returncode != 0
    assert 'pip install "xnano[audio]"' in result.stderr


def test_the_audio_value_says_how_to_install_it_and_from_image_too():
    result = run(
        """
        xnano.from_audio(b'RIFF')
        """
    )
    assert result.returncode != 0
    assert 'pip install "xnano[audio]"' in result.stderr
    result = run(
        """
        xnano.from_image(b'x')
        """
    )
    assert result.returncode != 0
    assert 'pip install "xnano[image]"' in result.stderr


def test_the_audio_of_a_canvas_says_how_to_install_it():
    result = run(
        """
        with xnano.new(width=8, height=1) as canvas:
            canvas.audio
        """
    )
    assert result.returncode != 0
    assert 'Canvas.audio needs sound, notes and melodies' in result.stderr
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
            'import xnano; import xnano.audio, xnano.image; print(xnano.audio.TerminalNote("C4") + 1, xnano.image.TerminalImage.__name__)',
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert 'TerminalImage' in result.stdout
