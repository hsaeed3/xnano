"""
tests.test_monty

`xnano.monty` runs sandboxed Python against a canvas through Monty.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import textwrap

import pytest

import xnano

pydantic_monty = pytest.importorskip('pydantic_monty')

from xnano.monty import DEFAULT_LIMITS, SANDBOX_STUBS, Sandbox, run  # noqa: E402
from xnano.placement import Placement  # noqa: E402


@pytest.fixture
def canvas():
    with xnano.new(width=20, height=4) as canvas:
        yield canvas


@pytest.fixture
def sandbox(canvas):
    with Sandbox(canvas) as sandbox:
        yield sandbox


def test_run_draws_text_on_the_canvas(canvas):
    run("canvas.write('hello', x='center', y=1)", canvas)
    assert canvas.render().splitlines()[1] == '       hello'


def test_run_returns_the_last_expression(canvas):
    assert run('canvas.width * 2', canvas) == 40


def test_code_can_import_the_xnano_module(canvas):
    run("import xnano\nxnano.canvas.write('imported')", canvas)
    assert canvas.render().splitlines()[0] == 'imported'


def test_a_sandbox_keeps_names_between_runs(canvas, sandbox):
    sandbox.run("label = canvas.write('hello', x=1)")
    sandbox.run("label.set_text('bye')")
    assert canvas.render().splitlines()[0] == ' bye'
    sandbox.run('label.move(x=2, y=1)')
    assert canvas.render().splitlines()[1] == '   bye'
    sandbox.run("label.set_position(x='right', y=0)")
    assert canvas.render().splitlines()[0] == '                 bye'
    assert sandbox.run('(label.x, label.y, label.width, label.height, label.text)') == (
        17,
        0,
        3,
        1,
        'bye',
    )
    sandbox.run('label.remove()')
    assert canvas.render().strip() == ''


def test_a_returned_placement_is_the_placement_itself(canvas, sandbox):
    placement = sandbox.run("canvas.write('hi', y=2)")
    assert isinstance(placement, Placement)
    assert (placement.y, placement.text) == (2, 'hi')
    pair = sandbox.run("(canvas.write('a'), canvas.write('b', x=5))")
    assert [item.text for item in pair] == ['a', 'b']


def test_written_text_takes_its_look(canvas):
    run("canvas.write('ok', foreground='green', bold=True, border='rounded')", canvas)
    assert canvas.render().splitlines()[:3] == ['╭──╮', '│ok│', '╰──╯']
    assert '\x1b[' in canvas.render(format='ansi')


def test_pixel_art_is_drawn_and_written(canvas, sandbox):
    size = sandbox.run(
        "heart = draw(['R.R', 'RRR'], 'R=red')\n"
        'placement = canvas.write(heart, y=1)\n'
        '(heart.width, heart.height, placement.width, placement.height)'
    )
    assert size == (3, 2, 3, 1)
    # Full pixels are cells painted with the color; the half pixel is a lower half block.
    assert canvas.render().splitlines()[1] == ' ▄'


def test_a_single_row_of_art_is_a_picture_not_a_symbol_name(canvas):
    assert run("draw('RR', {'R': 'red'}).width", canvas) == 2


def test_step_moves_the_clock_of_a_canvas_from_new(canvas, sandbox):
    sandbox.run('canvas.step(0.5)\ncanvas.step(0.25)')
    assert sandbox.run('canvas.time.elapsed') == 0.75
    assert canvas.time.elapsed == 0.75


def test_print_goes_to_this_programs_output(canvas, capsys):
    run("print('from the sandbox')", canvas)
    assert capsys.readouterr().out == 'from the sandbox\n'


def test_play_records_sound_on_a_canvas_from_new(canvas, sandbox):
    pytest.importorskip('xnano_audio')
    sandbox.run("canvas.play('C4 E4', instrument='piano', volume=0.5)")
    canvas.step(delta_seconds=1.0)
    assert canvas.audio.render_sound().peak > 0.0


def test_assigning_to_a_placement_attribute_is_refused_before_running(canvas, sandbox):
    sandbox.run("label = canvas.write('hello')")
    with pytest.raises(
        pydantic_monty.MontyTypingError, match='read-only property `text`'
    ):
        sandbox.run("label.text = 'changed'")
    assert canvas.render().splitlines()[0] == 'hello'


def test_an_unknown_keyword_is_refused_before_running(canvas):
    with pytest.raises(pydantic_monty.MontyTypingError, match='colour'):
        run("canvas.write('a', colour='red')", canvas)
    assert canvas.render().strip() == ''


def test_an_error_on_the_canvas_reaches_the_code_and_the_sandbox_stays_usable(
    canvas, sandbox
):
    with pytest.raises(pydantic_monty.MontyRuntimeError) as raised:
        sandbox.run("canvas.write('a', x='middle')")
    assert 'middle' in raised.value.display('msg')
    caught = sandbox.run(
        "try:\n    canvas.write('a', x='middle')\nexcept ValueError:\n    caught = True\ncaught"
    )
    assert caught is True
    sandbox.run("canvas.write('still here')")
    assert canvas.render().splitlines()[0] == 'still here'


def test_writing_something_that_is_not_text_or_art_is_explained(canvas):
    with pytest.raises(pydantic_monty.MontyRuntimeError) as raised:
        run("label = canvas.write('a')\ncanvas.write(label)  # type: ignore", canvas)
    assert 'text, a list of lines, or pixel art from draw()' in raised.value.display(
        'msg'
    )


def test_the_sandbox_cannot_reach_the_files_of_this_computer(canvas):
    with pytest.raises(pydantic_monty.MontyRuntimeError, match='PermissionError'):
        run("from pathlib import Path\nPath('/etc/hosts').read_text()", canvas)


def test_limits_replace_the_defaults(canvas):
    with pytest.raises(pydantic_monty.MontyRuntimeError, match='TimeoutError'):
        run('while True:\n    pass', canvas, limits={'max_feed_duration_secs': 0.2})
    assert DEFAULT_LIMITS.get('max_feed_duration_secs') == 10.0


def test_a_sandbox_needs_a_canvas():
    with pytest.raises(TypeError, match=r'xnano\.new\('):
        Sandbox('not a canvas')  # type: ignore[arg-type]


def test_a_program_must_be_a_string(sandbox):
    with pytest.raises(TypeError, match='takes the program as a string'):
        sandbox.run(42)  # type: ignore[arg-type]


def test_closing_twice_is_harmless(canvas):
    sandbox = Sandbox(canvas)
    sandbox.close()
    sandbox.close()


def test_the_sandbox_stubs_are_valid_python():
    tree = ast.parse(SANDBOX_STUBS)
    names = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef))
    }
    assert {'Canvas', 'Placement', 'Art', 'Time', 'draw'} <= names


def _run_without_monty(body: str) -> subprocess.CompletedProcess[str]:
    prelude = "import sys\nsys.modules['pydantic_monty'] = None\n"
    return subprocess.run(
        [sys.executable, '-c', prelude + textwrap.dedent(body)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_xnano_does_not_import_monty():
    result = subprocess.run(
        [
            sys.executable,
            '-c',
            "import sys, xnano\nprint('pydantic_monty' in sys.modules)",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'False'


def test_running_code_without_the_extra_says_how_to_install_it():
    result = _run_without_monty(
        """
        import xnano
        import xnano.monty

        with xnano.new(width=4, height=1) as canvas:
            xnano.monty.run("canvas.write('a')", canvas)
        """
    )
    assert result.returncode != 0
    assert 'ImportError' in result.stderr
    assert 'pydantic-monty' in result.stderr
    assert 'pip install "xnano[monty]"' in result.stderr
