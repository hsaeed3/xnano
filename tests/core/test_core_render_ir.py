"""CoreRenderIR and IrLine tests — Stage 1 render pipeline."""

from __future__ import annotations

import pytest

from xnano_core.core import CoreRenderContent, CoreRenderIR, IrLine
from xnano_core.rust.engine import CoreRenderNode, CoreSession


# ── helpers ───────────────────────────────────────────────────────────────────

def _offscreen() -> CoreSession:
    return CoreSession.offscreen(40, 12)


def _render(ir: CoreRenderIR) -> list[str]:
    sess = _offscreen()
    sess.render(CoreRenderNode.leaf(CoreRenderContent.ir(ir)))
    return sess.buffer_snapshot().to_string_lines()


def _text(lines: list[str]) -> str:
    return "\n".join(lines)


# ── IrLine factory methods ────────────────────────────────────────────────────

class TestIrLine:
    def test_raw_constructs(self) -> None:
        line = IrLine.raw("hello")
        assert line is not None

    def test_styled_constructs(self) -> None:
        line = IrLine.styled("styled", None, None, [])
        assert line is not None

    def test_from_spans_constructs(self) -> None:
        line = IrLine.from_spans([("span-a", None, None, []), ("span-b", None, None, [])])
        assert line is not None

    def test_raw_renders_text(self) -> None:
        ir = CoreRenderIR.line(IrLine.raw("ir-line-raw"))
        assert "ir-line-raw" in _text(_render(ir))

    def test_styled_renders_text(self) -> None:
        ir = CoreRenderIR.line(IrLine.styled("ir-line-styled", None, None, []))
        assert "ir-line-styled" in _text(_render(ir))

    def test_from_spans_renders_text(self) -> None:
        line = IrLine.from_spans([("span-content", None, None, [])])
        ir = CoreRenderIR.line(line)
        assert "span-content" in _text(_render(ir))


# ── CoreRenderIR.measure ──────────────────────────────────────────────────────

class TestCoreRenderIRMeasure:
    def test_clear_measure(self) -> None:
        assert CoreRenderIR.clear().measure() == (0, 0)

    def test_span_measure_width_equals_content_len(self) -> None:
        w, h = CoreRenderIR.span("hello", None, None, []).measure()
        assert w == 5
        assert h == 1

    def test_span_measure_empty_string(self) -> None:
        w, h = CoreRenderIR.span("", None, None, []).measure()
        assert w == 0
        assert h == 1

    def test_line_measure(self) -> None:
        w, h = CoreRenderIR.line(IrLine.raw("abc")).measure()
        assert w == 3
        assert h == 1

    def test_paragraph_raw_measure(self) -> None:
        w, h = CoreRenderIR.paragraph_raw("para-text", None, None, [], None, False).measure()
        assert w == 9
        assert h == 1

    def test_progress_bar_measure(self) -> None:
        w, h = CoreRenderIR.progress_bar(0.5, None, None, None).measure()
        assert w == 0
        assert h == 1

    def test_sparkline_measure(self) -> None:
        w, h = CoreRenderIR.sparkline([1, 2, 3], None, None, None, None, None).measure()
        assert w == 0
        assert h == 1

    def test_line_gauge_measure(self) -> None:
        w, h = CoreRenderIR.line_gauge(0.5, None, None, None, None, None).measure()
        assert w == 0
        assert h == 1

    def test_scrollbar_vertical_measure(self) -> None:
        w, h = CoreRenderIR.scrollbar(0, 100, 0, None, None, None, None, None, None).measure()
        assert w == 1
        assert h == 0

    def test_scrollbar_horizontal_measure(self) -> None:
        w, h = CoreRenderIR.scrollbar(2, 100, 0, None, None, None, None, None, None).measure()
        assert w == 0
        assert h == 1

    def test_tabs_measure(self) -> None:
        titles = [IrLine.raw("Tab1"), IrLine.raw("Tab2")]
        w, h = CoreRenderIR.tabs(titles, 0, None, None, None, None, None, " ", " ").measure()
        assert h == 1

    def test_canvas_measure(self) -> None:
        w, h = CoreRenderIR.canvas([], (0.0, 1.0), (0.0, 1.0), None, None).measure()
        assert w == 0
        assert h == 0

    def test_list_empty_measure(self) -> None:
        w, h = CoreRenderIR.list([], None, None, None, None, None, ">> ").measure()
        assert w == 0
        assert h == 1

    def test_list_nonempty_measure_height(self) -> None:
        items = [IrLine.raw("a"), IrLine.raw("b"), IrLine.raw("c")]
        w, h = CoreRenderIR.list(items, None, None, None, None, None, "").measure()
        assert h == 3

    def test_table_measure_row_count(self) -> None:
        row = ([( IrLine.raw("cell"), None, None, [])], None, None, 1)
        _w, h = CoreRenderIR.table(
            [row, row],
            None, None,
            [(2, 1.0)],
            0,
            None, None,
            None, None, None,
        ).measure()
        assert h == 2

    def test_table_measure_with_header(self) -> None:
        row = ([(IrLine.raw("h"), None, None, [])], None, None, 1)
        _w, h = CoreRenderIR.table(
            [row],
            row,
            None,
            [(2, 1.0)],
            0,
            None, None,
            None, None, None,
        ).measure()
        assert h == 2  # 1 header + 1 body row

    def test_text_raw_measure(self) -> None:
        w, h = CoreRenderIR.text_raw("hi", None, None, [], None).measure()
        assert w == 2
        assert h == 1

    def test_text_lines_measure(self) -> None:
        lines = [IrLine.raw("abc"), IrLine.raw("de")]
        w, h = CoreRenderIR.text_lines(lines, None, None, [], None).measure()
        assert w == 3
        assert h == 2

    def test_bar_chart_measure(self) -> None:
        bar = (5, "bar", None, None, None, None, None)
        group = (None, [bar])
        w, h = CoreRenderIR.bar_chart([group], 1, 0, 0, None, False, None, None, None).measure()
        assert w == 0
        assert h == 0


# ── CoreRenderContent.ir predicate ───────────────────────────────────────────

class TestCoreRenderContentIr:
    def test_is_ir_true_for_ir_content(self) -> None:
        content = CoreRenderContent.ir(CoreRenderIR.clear())
        assert content.is_ir()

    def test_is_ir_false_for_empty(self) -> None:
        assert not CoreRenderContent.empty().is_ir()

    def test_is_ir_false_for_widget(self) -> None:
        from xnano_core.rust.native import Paragraph
        assert not CoreRenderContent.widget(Paragraph.new("x")).is_ir()

    def test_is_empty_false_for_ir(self) -> None:
        assert not CoreRenderContent.ir(CoreRenderIR.clear()).is_empty()

    def test_is_stateful_false_for_ir(self) -> None:
        assert not CoreRenderContent.ir(CoreRenderIR.clear()).is_stateful()

    def test_is_drawable_false_for_ir(self) -> None:
        assert not CoreRenderContent.ir(CoreRenderIR.clear()).is_drawable()


# ── CoreRenderIR render-to-buffer correctness ─────────────────────────────────

class TestCoreRenderIRRenders:
    def test_span_renders(self) -> None:
        ir = CoreRenderIR.span("span-text", None, None, [])
        assert "span-text" in _text(_render(ir))

    def test_line_renders(self) -> None:
        ir = CoreRenderIR.line(IrLine.raw("line-text"))
        assert "line-text" in _text(_render(ir))

    def test_paragraph_raw_renders(self) -> None:
        ir = CoreRenderIR.paragraph_raw("para-raw", None, None, [], None, False)
        assert "para-raw" in _text(_render(ir))

    def test_paragraph_lines_renders(self) -> None:
        ir = CoreRenderIR.paragraph_lines([IrLine.raw("para-line")], None, None, [], None, False)
        assert "para-line" in _text(_render(ir))

    def test_text_raw_renders(self) -> None:
        ir = CoreRenderIR.text_raw("text-raw", None, None, [], None)
        assert "text-raw" in _text(_render(ir))

    def test_text_lines_renders(self) -> None:
        ir = CoreRenderIR.text_lines([IrLine.raw("text-line")], None, None, [], None)
        assert "text-line" in _text(_render(ir))

    def test_list_renders_items(self) -> None:
        items = [IrLine.raw("item-alpha"), IrLine.raw("item-beta")]
        ir = CoreRenderIR.list(items, None, None, None, None, None, "")
        text = _text(_render(ir))
        assert "item-alpha" in text
        assert "item-beta" in text

    def test_list_empty_renders_without_error(self) -> None:
        ir = CoreRenderIR.list([], None, None, None, None, None, "")
        _render(ir)  # must not raise

    def test_clear_renders_without_error(self) -> None:
        ir = CoreRenderIR.clear()
        _render(ir)  # must not raise

    def test_progress_bar_renders(self) -> None:
        ir = CoreRenderIR.progress_bar(0.5, "50%", None, None)
        _render(ir)  # must not raise

    def test_sparkline_renders(self) -> None:
        ir = CoreRenderIR.sparkline([1, 2, 3, 4, 5], None, None, None, None, None)
        _render(ir)  # must not raise

    def test_line_gauge_renders(self) -> None:
        ir = CoreRenderIR.line_gauge(0.75, None, None, None, None, None)
        _render(ir)

    def test_scrollbar_renders(self) -> None:
        ir = CoreRenderIR.scrollbar(0, 100, 10, None, None, None, None, None, None)
        _render(ir)

    def test_tabs_renders_titles(self) -> None:
        titles = [IrLine.raw("Tab-A"), IrLine.raw("Tab-B")]
        ir = CoreRenderIR.tabs(titles, 0, None, None, None, None, None, " ", " ")
        text = _text(_render(ir))
        assert "Tab-A" in text
        assert "Tab-B" in text

    def test_table_renders_cells(self) -> None:
        cell = (IrLine.raw("cell-data"), None, None, [])
        row = ([cell], None, None, 1)
        ir = CoreRenderIR.table(
            [row],
            None, None,
            [(2, 1.0)],
            0,
            None, None,
            None, None, None,
        )
        assert "cell-data" in _text(_render(ir))

    def test_canvas_renders_without_error(self) -> None:
        ir = CoreRenderIR.canvas([], (0.0, 40.0), (0.0, 12.0), None, None)
        _render(ir)

    def test_bar_chart_renders_without_error(self) -> None:
        # bar tuple: (value, label, text_value, bar_fg, bar_bg, value_fg, value_bg)
        bar = (5, "bar", None, None, None, None, None)
        group = (None, [bar])
        ir = CoreRenderIR.bar_chart([group], 1, 0, 0, None, False, None, None, None)
        _render(ir)

    def test_ir_content_via_leaf_node(self) -> None:
        ir = CoreRenderIR.span("via-leaf", None, None, [])
        content = CoreRenderContent.ir(ir)
        node = CoreRenderNode.leaf(content)
        sess = _offscreen()
        sess.render(node)
        text = _text(sess.buffer_snapshot().to_string_lines())
        assert "via-leaf" in text


# ── Engine module exports Stage 1 types ───────────────────────────────────────

def test_engine_exports_core_render_ir() -> None:
    import xnano_core.rust.engine as engine
    assert hasattr(engine, "CoreRenderIR")


def test_engine_exports_ir_line() -> None:
    import xnano_core.rust.engine as engine
    assert hasattr(engine, "IrLine")


def test_core_module_exports_core_render_ir() -> None:
    import xnano_core.core as core
    assert hasattr(core, "CoreRenderIR")


def test_core_module_exports_ir_line() -> None:
    import xnano_core.core as core
    assert hasattr(core, "IrLine")
