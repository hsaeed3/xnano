"""
Tests for ``TerminalError``: its codes, its report, its pickling and the exception hook.
"""

from __future__ import annotations

import os
import pickle
import re
import subprocess
import sys
import textwrap

import pytest

import xnano
from xnano.errors import (
    TerminalAlreadyOpenError,
    TerminalClosedError,
    TerminalError,
)


class TestCodes:
    @pytest.mark.parametrize(
        ('code', 'builtin'),
        [
            ('validation.type', TypeError),
            ('validation.keyword', TypeError),
            ('validation.value', ValueError),
            ('validation.bounds', ValueError),
        ],
    )
    def test_a_validation_code_is_also_the_builtin_error_for_it(self, code, builtin):
        error = TerminalError('wrong', code=code)
        assert isinstance(error, builtin)
        assert isinstance(error, TerminalError)
        assert isinstance(error, RuntimeError)
        assert error.code == code
        assert type(error).__name__ == 'TerminalError'

    def test_other_codes_are_runtime_errors_only(self):
        error = TerminalError('stuck', code='canvas.timeout')
        assert not isinstance(error, (TypeError, ValueError))
        assert error.code == 'canvas.timeout'

    def test_each_class_has_its_own_default_code(self):
        assert TerminalError('a').code == 'canvas.state'
        assert TerminalClosedError('a').code == 'canvas.closed'
        assert TerminalAlreadyOpenError('a').code == 'screen.already_open'


class TestReport:
    def test_the_text_is_a_pydantic_style_report(self):
        error = TerminalError(
            'height must be at most 65535 cells.',
            code='validation.bounds',
            location=('write', 'height'),
            hint='Pass a smaller height.',
            title='canvas.screen.write()',
            input_value=70000,
        )
        assert str(error).splitlines() == [
            '1 error in canvas.screen.write()',
            'write.height',
            '  height must be at most 65535 cells. '
            '[code=validation.bounds, input_value=70000, input_type=int]',
            '    Pass a smaller height.',
        ]
        detail = error.details[0]
        assert (detail.location, detail.input_value) == (('write', 'height'), 70000)
        assert error.report.title == 'canvas.screen.write()'

    def test_a_long_input_value_is_cut_short(self):
        error = TerminalError('too long', code='validation.value', input_value='x' * 200)
        shown = str(error).split('input_value=')[1]
        assert '...' in shown and len(shown) < 120

    def test_an_error_survives_pickling(self):
        error = TerminalError(
            'bad', code='validation.bounds', location='layer', input_value=9
        )
        again = pickle.loads(pickle.dumps(error))
        assert isinstance(again, ValueError) and isinstance(again, TerminalError)
        assert str(again) == str(error)
        closed = pickle.loads(pickle.dumps(TerminalClosedError('closed')))
        assert type(closed) is TerminalClosedError


class TestLabelledRaises:
    def test_a_layer_out_of_range_is_a_bounds_error(self):
        with xnano.new(width=4, height=1) as canvas:
            with pytest.raises(ValueError) as caught:
                canvas.screen.write('x', layer=2**40)
        error = caught.value
        assert isinstance(error, TerminalError)
        assert error.code == 'validation.bounds'
        assert error.details[0].location == ('layer',)
        assert error.details[0].input_value == 2**40

    def test_a_modifier_that_is_not_a_boolean_is_a_type_error(self):
        with xnano.new(width=4, height=1) as canvas:
            with pytest.raises(TypeError) as caught:
                canvas.screen.write('x', bold='yes')  # type: ignore[arg-type]
        assert isinstance(caught.value, TerminalError)
        assert caught.value.code == 'validation.type'

    def test_writing_a_canvas_twice_is_a_composition_error(self):
        with xnano.new(width=8, height=2) as outer:
            inner = outer.screen.new(width=2, height=1)
            with pytest.raises(TerminalError) as caught:
                outer.screen.write(inner)
        assert caught.value.code == 'canvas.composition'

    def test_a_closed_canvas_raises_a_closed_error(self):
        canvas = xnano.new(width=4, height=1)
        canvas.close()
        with pytest.raises(TerminalClosedError) as caught:
            canvas.screen.write('x')
        assert caught.value.code == 'canvas.closed'


def run_uncaught(body: str, **environment: str) -> str:
    """Run a program that ends with an uncaught error and return what it wrote to stderr."""
    variables = {
        name: value
        for name, value in os.environ.items()
        if name not in {'NO_COLOR', 'FORCE_COLOR'}
    }
    variables.update(environment)
    completed = subprocess.run(
        [sys.executable, '-c', textwrap.dedent(body)],
        capture_output=True,
        text=True,
        env=variables,
        check=False,
    )
    assert completed.returncode == 1
    return completed.stderr


class TestExceptionHook:
    PROGRAM = """
        import xnano
        from xnano.errors import TerminalError
        raise TerminalError('layer must be a whole number.', code='validation.type', input_value='top')
    """

    def test_an_uncaught_error_is_printed_with_colors_when_asked(self):
        printed = run_uncaught(self.PROGRAM, FORCE_COLOR='1')
        assert 'Traceback (most recent call last)' in printed
        assert '\x1b[1;31m1 error\x1b[0m' in printed
        assert '\x1b[36mvalidation.type\x1b[0m' in printed

    def test_an_uncaught_error_is_plain_without_a_terminal_or_with_no_color(self):
        for environment in ({}, {'NO_COLOR': '1', 'FORCE_COLOR': '1'}):
            printed = run_uncaught(self.PROGRAM, **environment)
            assert '\x1b[' not in printed
            assert printed.rstrip().endswith(
                '  layer must be a whole number. '
                "[code=validation.type, input_value='top', input_type=str]"
            )

    def test_other_errors_are_printed_as_always(self):
        printed = run_uncaught("import xnano\n{}['missing']\n", FORCE_COLOR='1')
        last_line = re.sub(r'\x1b\[[0-9;]*m', '', printed.rstrip().splitlines()[-1])
        assert last_line == "KeyError: 'missing'"
        assert '1 error' not in printed
