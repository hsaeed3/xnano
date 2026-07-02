"""Tests for xnano.printing module - stdout formatting and printing."""

import io
import sys
from xnano.printing import print as xnano_print
from xnano.widgets import Paragraph


def test_printing_string():
    captured_output = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured_output
        xnano_print("hello world", height=1)
    finally:
        sys.stdout = old_stdout

    output = captured_output.getvalue()
    assert "hello world" in output


def test_printing_widget():
    captured_output = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured_output
        widget = Paragraph("styled text")
        xnano_print(widget, height=1)
    finally:
        sys.stdout = old_stdout

    output = captured_output.getvalue()
    assert "styled text" in output


def test_printing_multiple_args():
    captured_output = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured_output
        widget = Paragraph("widget text")
        xnano_print("hello", widget, "world", height=1)
    finally:
        sys.stdout = old_stdout

    output = captured_output.getvalue()
    assert output.startswith("hello ")
    assert "widget text" in output
    assert output.endswith("world\n")


def test_printing_custom_sep_end():
    captured_output = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured_output
        xnano_print("hello", "world", sep="---", end="!!!")
    finally:
        sys.stdout = old_stdout

    output = captured_output.getvalue()
    assert output == "hello---world!!!"


def test_printing_nested_block_sizing():
    import io
    import sys
    from xnano.widgets import Block, Paragraph

    captured_output = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = captured_output
        block = Block(borders="all", width=30, height=3)
        widget = Paragraph("hello", block=block)
        xnano_print(widget)
    finally:
        sys.stdout = old_stdout

    output = captured_output.getvalue()
    lines = output.splitlines()
    assert len(lines) == 3
    # Strip the trailing reset code to check exact visual column width
    assert len(lines[0].replace("\x1b[0m", "")) == 30
