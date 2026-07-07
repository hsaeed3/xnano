use pyo3::prelude::*;
use ratatui::buffer::Buffer;
use ratatui::layout::{Alignment, Constraint, Direction, Rect};
use ratatui::style::{Color, Style};
use ratatui::symbols::Marker;
use ratatui::text::{Line, Span, Text};
use ratatui::widgets::canvas::{Circle, Line as CanvasLine, Points, Rectangle};
use ratatui::widgets::{
    Bar, BarChart, BarGroup, Cell, Clear, Gauge, LineGauge, List, ListItem,
    ListState, Paragraph, Row, Scrollbar, ScrollbarOrientation, ScrollbarState, Sparkline,
    StatefulWidget, Table, TableState, Tabs, Widget, Wrap,
};

use super::super::style::{PyColor, PyModifier};

// ── Style helpers ─────────────────────────────────────────────────────────────

fn build_style(fg: Option<PyColor>, bg: Option<PyColor>, modifiers: &[PyModifier]) -> Style {
    let mut style = Style::default();
    if let Some(c) = fg {
        style = style.fg(c.inner);
    }
    if let Some(c) = bg {
        style = style.bg(c.inner);
    }
    for m in modifiers {
        style = style.add_modifier(m.inner);
    }
    style
}

fn align_from_u8(v: Option<u8>) -> Option<Alignment> {
    match v {
        Some(0) => Some(Alignment::Left),
        Some(1) => Some(Alignment::Center),
        Some(2) => Some(Alignment::Right),
        _ => None,
    }
}

fn scrollbar_orientation(v: u8) -> ScrollbarOrientation {
    match v {
        1 => ScrollbarOrientation::VerticalLeft,
        2 => ScrollbarOrientation::HorizontalBottom,
        3 => ScrollbarOrientation::HorizontalTop,
        _ => ScrollbarOrientation::VerticalRight,
    }
}

fn marker_from_u8(v: u8) -> Marker {
    match v {
        0 => Marker::Dot,
        1 => Marker::Block,
        2 => Marker::Bar,
        4 => Marker::HalfBlock,
        _ => Marker::Braille,
    }
}

// width kind: 0=Length, 1=Percentage, 2=Fill
fn constraint_from_kind(kind: u8, val: f64) -> Constraint {
    match kind {
        1 => Constraint::Percentage(val as u16),
        2 => Constraint::Fill(val as u16),
        _ => Constraint::Length(val as u16),
    }
}

// ── IrLine ────────────────────────────────────────────────────────────────────
// A pre-built ratatui Line constructed in one boundary crossing.

#[pyclass(name = "IrLine", module = "xnano_core.rust.engine", from_py_object)]
#[derive(Clone)]
pub struct PyIrLine {
    pub inner: Line<'static>,
}

#[pymethods]
impl PyIrLine {
    #[staticmethod]
    fn raw(content: String) -> Self {
        Self { inner: Line::raw(content) }
    }

    #[staticmethod]
    #[pyo3(signature = (content, fg=None, bg=None, modifiers=vec![]))]
    fn styled(
        content: String,
        fg: Option<PyColor>,
        bg: Option<PyColor>,
        modifiers: Vec<PyModifier>,
    ) -> Self {
        let style = build_style(fg, bg, &modifiers);
        Self { inner: Line::styled(content, style) }
    }

    /// Accept a list of `(content, fg, bg, modifiers)` 4-tuples.
    #[staticmethod]
    fn from_spans(
        spans: Vec<(String, Option<PyColor>, Option<PyColor>, Vec<PyModifier>)>,
    ) -> Self {
        let rat_spans: Vec<Span<'static>> = spans
            .into_iter()
            .map(|(content, fg, bg, mods)| Span::styled(content, build_style(fg, bg, &mods)))
            .collect();
        Self { inner: Line::from(rat_spans) }
    }
}

// ── Canvas shape IR ───────────────────────────────────────────────────────────

#[derive(Clone)]
pub enum IrCanvasShape {
    Line   { x1: f64, y1: f64, x2: f64, y2: f64, color: Color },
    Points { coords: Vec<(f64, f64)>, color: Color },
    Rect   { x: f64, y: f64, width: f64, height: f64, color: Color },
    Circle { x: f64, y: f64, radius: f64, color: Color },
    Print  { x: f64, y: f64, text: String },
}

// ── Inner IR enum ─────────────────────────────────────────────────────────────

#[derive(Clone)]
pub enum RenderIrInner {
    Span {
        content: String,
        style: Style,
    },
    Line {
        line: Line<'static>,
    },
    Text {
        text: Text<'static>,
        style: Style,
    },
    Paragraph {
        text: Text<'static>,
        style: Style,
        align: Option<Alignment>,
        wrap: bool,
    },
    List {
        items: Vec<Text<'static>>,
        selected: Option<usize>,
        style: Style,
        highlight_style: Style,
        highlight_symbol: String,
    },
    ProgressBar {
        progress: f64,
        label: Option<String>,
        style: Style,
    },
    Clear,
    Sparkline {
        data: Vec<u64>,
        max_value: Option<u64>,
        style: Style,
        absent_value_style: Style,
        absent_value_symbol: Option<String>,
    },
    LineGauge {
        progress: f64,
        label: Option<String>,
        style: Style,
        filled_style: Style,
        unfilled_style: Style,
    },
    BarChart {
        // each group: (label, bars: (value, bar_label, text_value, bar_style, value_style)[])
        groups: Vec<(Option<String>, Vec<(u64, String, Option<String>, Style, Style)>)>,
        bar_width: u16,
        bar_gap: u16,
        group_gap: u16,
        max_value: Option<u64>,
        horizontal: bool,
        bar_style: Style,
        value_style: Style,
        label_style: Style,
    },
    Table {
        rows: Vec<(Vec<(Text<'static>, Style)>, Style, u16)>,
        header: Option<(Vec<(Text<'static>, Style)>, Style, u16)>,
        footer: Option<(Vec<(Text<'static>, Style)>, Style, u16)>,
        // (kind: u8, value: f64) — 0=Length, 1=Percentage, 2=Fill
        widths: Vec<(u8, f64)>,
        column_spacing: u16,
        selected_row: Option<usize>,
        selected_column: Option<usize>,
        row_highlight_style: Style,
        highlight_symbol: Option<String>,
    },
    Scrollbar {
        orientation: ScrollbarOrientation,
        content_length: usize,
        position: usize,
        viewport_length: Option<usize>,
        style: Style,
        thumb_style: Style,
        track_style: Style,
        begin_symbol: Option<String>,
        end_symbol: Option<String>,
    },
    Tabs {
        titles: Vec<Line<'static>>,
        selected: usize,
        style: Style,
        highlight_style: Style,
        divider: Option<String>,
        padding_left: String,
        padding_right: String,
    },
    Canvas {
        x_bounds: [f64; 2],
        y_bounds: [f64; 2],
        background_color: Option<Color>,
        marker: Option<Marker>,
        shapes: Vec<IrCanvasShape>,
    },
}

// ── CoreRenderIR pyclass ──────────────────────────────────────────────────────

#[pyclass(name = "CoreRenderIR", module = "xnano_core.rust.engine", unsendable, from_py_object)]
#[derive(Clone)]
pub struct CoreRenderIR {
    pub(crate) inner: RenderIrInner,
}

#[pymethods]
impl CoreRenderIR {
    // ── Leaf factories ────────────────────────────────────────────────────────

    #[staticmethod]
    #[pyo3(signature = (content, fg=None, bg=None, modifiers=vec![]))]
    fn span(
        content: String,
        fg: Option<PyColor>,
        bg: Option<PyColor>,
        modifiers: Vec<PyModifier>,
    ) -> Self {
        Self {
            inner: RenderIrInner::Span {
                content,
                style: build_style(fg, bg, &modifiers),
            },
        }
    }

    #[staticmethod]
    fn line(ir_line: PyRef<'_, PyIrLine>) -> Self {
        Self { inner: RenderIrInner::Line { line: ir_line.inner.clone() } }
    }

    #[staticmethod]
    #[pyo3(signature = (content, fg=None, bg=None, modifiers=vec![], align=None))]
    fn text_raw(
        content: String,
        fg: Option<PyColor>,
        bg: Option<PyColor>,
        modifiers: Vec<PyModifier>,
        align: Option<u8>,
    ) -> Self {
        let style = build_style(fg, bg, &modifiers);
        let mut text = Text::raw(content);
        text = text.style(style);
        if let Some(a) = align_from_u8(align) {
            text = text.alignment(a);
        }
        Self { inner: RenderIrInner::Text { text, style } }
    }

    #[staticmethod]
    #[pyo3(signature = (lines, fg=None, bg=None, modifiers=vec![], align=None))]
    fn text_lines(
        lines: Vec<PyRef<'_, PyIrLine>>,
        fg: Option<PyColor>,
        bg: Option<PyColor>,
        modifiers: Vec<PyModifier>,
        align: Option<u8>,
    ) -> Self {
        let style = build_style(fg, bg, &modifiers);
        let rat_lines: Vec<Line<'static>> = lines.iter().map(|l| l.inner.clone()).collect();
        let mut text = Text::from(rat_lines);
        text = text.style(style);
        if let Some(a) = align_from_u8(align) {
            text = text.alignment(a);
        }
        Self { inner: RenderIrInner::Text { text, style } }
    }

    #[staticmethod]
    #[pyo3(signature = (content, fg=None, bg=None, modifiers=vec![], align=None, wrap=true))]
    fn paragraph_raw(
        content: String,
        fg: Option<PyColor>,
        bg: Option<PyColor>,
        modifiers: Vec<PyModifier>,
        align: Option<u8>,
        wrap: bool,
    ) -> Self {
        let style = build_style(fg, bg, &modifiers);
        let text = Text::raw(content);
        Self {
            inner: RenderIrInner::Paragraph {
                text,
                style,
                align: align_from_u8(align),
                wrap,
            },
        }
    }

    #[staticmethod]
    #[pyo3(signature = (lines, fg=None, bg=None, modifiers=vec![], align=None, wrap=true))]
    fn paragraph_lines(
        lines: Vec<PyRef<'_, PyIrLine>>,
        fg: Option<PyColor>,
        bg: Option<PyColor>,
        modifiers: Vec<PyModifier>,
        align: Option<u8>,
        wrap: bool,
    ) -> Self {
        let style = build_style(fg, bg, &modifiers);
        let rat_lines: Vec<Line<'static>> = lines.iter().map(|l| l.inner.clone()).collect();
        let text = Text::from(rat_lines);
        Self {
            inner: RenderIrInner::Paragraph {
                text,
                style,
                align: align_from_u8(align),
                wrap,
            },
        }
    }

    #[staticmethod]
    #[pyo3(signature = (
        items, selected=None,
        fg=None, bg=None,
        highlight_fg=None, highlight_bg=None,
        highlight_symbol="> ".to_string()
    ))]
    fn list(
        items: Vec<PyRef<'_, PyIrLine>>,
        selected: Option<usize>,
        fg: Option<PyColor>,
        bg: Option<PyColor>,
        highlight_fg: Option<PyColor>,
        highlight_bg: Option<PyColor>,
        highlight_symbol: String,
    ) -> Self {
        let texts: Vec<Text<'static>> =
            items.iter().map(|l| Text::from(vec![l.inner.clone()])).collect();
        Self {
            inner: RenderIrInner::List {
                items: texts,
                selected,
                style: build_style(fg, bg, &[]),
                highlight_style: build_style(highlight_fg, highlight_bg, &[]),
                highlight_symbol,
            },
        }
    }

    #[staticmethod]
    #[pyo3(signature = (progress, label=None, fg=None, bg=None))]
    fn progress_bar(
        progress: f64,
        label: Option<String>,
        fg: Option<PyColor>,
        bg: Option<PyColor>,
    ) -> Self {
        Self {
            inner: RenderIrInner::ProgressBar {
                progress,
                label,
                style: build_style(fg, bg, &[]),
            },
        }
    }

    #[staticmethod]
    fn clear() -> Self {
        Self { inner: RenderIrInner::Clear }
    }

    #[staticmethod]
    #[pyo3(signature = (
        data=vec![], max_value=None,
        fg=None, bg=None,
        absent_value_fg=None, absent_value_symbol=None
    ))]
    fn sparkline(
        data: Vec<u64>,
        max_value: Option<u64>,
        fg: Option<PyColor>,
        bg: Option<PyColor>,
        absent_value_fg: Option<PyColor>,
        absent_value_symbol: Option<String>,
    ) -> Self {
        Self {
            inner: RenderIrInner::Sparkline {
                data,
                max_value,
                style: build_style(fg, bg, &[]),
                absent_value_style: build_style(absent_value_fg, None, &[]),
                absent_value_symbol,
            },
        }
    }

    #[staticmethod]
    #[pyo3(signature = (
        progress, label=None,
        fg=None, bg=None,
        filled_fg=None, unfilled_fg=None
    ))]
    fn line_gauge(
        progress: f64,
        label: Option<String>,
        fg: Option<PyColor>,
        bg: Option<PyColor>,
        filled_fg: Option<PyColor>,
        unfilled_fg: Option<PyColor>,
    ) -> Self {
        Self {
            inner: RenderIrInner::LineGauge {
                progress,
                label,
                style: build_style(fg, bg, &[]),
                filled_style: build_style(filled_fg, None, &[]),
                unfilled_style: build_style(unfilled_fg, None, &[]),
            },
        }
    }

    /// groups: list of (label: Optional[str], bars: list of
    ///   (value, bar_label, text_value, bar_fg, bar_bg, value_fg, value_bg))
    #[staticmethod]
    #[pyo3(signature = (
        groups=vec![],
        bar_width=1, bar_gap=1, group_gap=0,
        max_value=None, horizontal=false,
        fg=None, value_fg=None, label_fg=None
    ))]
    fn bar_chart(
        groups: Vec<(
            Option<String>,
            Vec<(u64, String, Option<String>, Option<PyColor>, Option<PyColor>, Option<PyColor>, Option<PyColor>)>,
        )>,
        bar_width: u16,
        bar_gap: u16,
        group_gap: u16,
        max_value: Option<u64>,
        horizontal: bool,
        fg: Option<PyColor>,
        value_fg: Option<PyColor>,
        label_fg: Option<PyColor>,
    ) -> Self {
        let ir_groups = groups
            .into_iter()
            .map(|(label, bars)| {
                let ir_bars = bars
                    .into_iter()
                    .map(|(val, blabel, text_val, bfg, bbg, vfg, _vbg)| {
                        (val, blabel, text_val, build_style(bfg, bbg, &[]), build_style(vfg, None, &[]))
                    })
                    .collect();
                (label, ir_bars)
            })
            .collect();
        Self {
            inner: RenderIrInner::BarChart {
                groups: ir_groups,
                bar_width,
                bar_gap,
                group_gap,
                max_value,
                horizontal,
                bar_style: build_style(fg, None, &[]),
                value_style: build_style(value_fg, None, &[]),
                label_style: build_style(label_fg, None, &[]),
            },
        }
    }

    /// rows: list of (cells, row_fg, row_bg, height)
    /// each cell: (IrLine, cell_fg, cell_bg, cell_mods)
    /// widths: list of (kind: int, value: float) — kind 0=Length, 1=Pct, 2=Fill
    #[staticmethod]
    #[pyo3(signature = (
        rows=vec![],
        header=None, footer=None,
        widths=vec![],
        column_spacing=1,
        selected_row=None, selected_column=None,
        highlight_fg=None, highlight_bg=None,
        highlight_symbol=None
    ))]
    fn table(
        rows: Vec<(
            Vec<(PyRef<'_, PyIrLine>, Option<PyColor>, Option<PyColor>, Vec<PyModifier>)>,
            Option<PyColor>,
            Option<PyColor>,
            u16,
        )>,
        header: Option<(
            Vec<(PyRef<'_, PyIrLine>, Option<PyColor>, Option<PyColor>, Vec<PyModifier>)>,
            Option<PyColor>,
            Option<PyColor>,
            u16,
        )>,
        footer: Option<(
            Vec<(PyRef<'_, PyIrLine>, Option<PyColor>, Option<PyColor>, Vec<PyModifier>)>,
            Option<PyColor>,
            Option<PyColor>,
            u16,
        )>,
        widths: Vec<(u8, f64)>,
        column_spacing: u16,
        selected_row: Option<usize>,
        selected_column: Option<usize>,
        highlight_fg: Option<PyColor>,
        highlight_bg: Option<PyColor>,
        highlight_symbol: Option<String>,
    ) -> Self {
        let convert_row =
            |row: (
                Vec<(PyRef<'_, PyIrLine>, Option<PyColor>, Option<PyColor>, Vec<PyModifier>)>,
                Option<PyColor>,
                Option<PyColor>,
                u16,
            )|
             -> (Vec<(Text<'static>, Style)>, Style, u16) {
                let (cells, rfg, rbg, height) = row;
                let ir_cells = cells
                    .into_iter()
                    .map(|(line, cfg, cbg, cmods)| {
                        (Text::from(vec![line.inner.clone()]), build_style(cfg, cbg, &cmods))
                    })
                    .collect();
                (ir_cells, build_style(rfg, rbg, &[]), height)
            };

        Self {
            inner: RenderIrInner::Table {
                rows: rows.into_iter().map(convert_row).collect(),
                header: header.map(convert_row),
                footer: footer.map(convert_row),
                widths,
                column_spacing,
                selected_row,
                selected_column,
                row_highlight_style: build_style(highlight_fg, highlight_bg, &[]),
                highlight_symbol,
            },
        }
    }

    /// orientation: 0=VerticalRight, 1=VerticalLeft, 2=HorizontalBottom, 3=HorizontalTop
    #[staticmethod]
    #[pyo3(signature = (
        orientation=0u8,
        content_length=0, position=0, viewport_length=None,
        fg=None, thumb_fg=None, track_fg=None,
        begin_symbol=None, end_symbol=None
    ))]
    fn scrollbar(
        orientation: u8,
        content_length: usize,
        position: usize,
        viewport_length: Option<usize>,
        fg: Option<PyColor>,
        thumb_fg: Option<PyColor>,
        track_fg: Option<PyColor>,
        begin_symbol: Option<String>,
        end_symbol: Option<String>,
    ) -> Self {
        Self {
            inner: RenderIrInner::Scrollbar {
                orientation: scrollbar_orientation(orientation),
                content_length,
                position,
                viewport_length,
                style: build_style(fg, None, &[]),
                thumb_style: build_style(thumb_fg, None, &[]),
                track_style: build_style(track_fg, None, &[]),
                begin_symbol,
                end_symbol,
            },
        }
    }

    #[staticmethod]
    #[pyo3(signature = (
        titles=vec![], selected=0usize,
        fg=None, bg=None,
        highlight_fg=None, highlight_bg=None,
        divider=None,
        padding_left=" ".to_string(), padding_right=" ".to_string()
    ))]
    fn tabs(
        titles: Vec<PyRef<'_, PyIrLine>>,
        selected: usize,
        fg: Option<PyColor>,
        bg: Option<PyColor>,
        highlight_fg: Option<PyColor>,
        highlight_bg: Option<PyColor>,
        divider: Option<String>,
        padding_left: String,
        padding_right: String,
    ) -> Self {
        let rat_titles: Vec<Line<'static>> = titles.iter().map(|l| l.inner.clone()).collect();
        Self {
            inner: RenderIrInner::Tabs {
                titles: rat_titles,
                selected,
                style: build_style(fg, bg, &[]),
                highlight_style: build_style(highlight_fg, highlight_bg, &[]),
                divider,
                padding_left,
                padding_right,
            },
        }
    }

    /// shapes: list of tagged tuples, one per shape:
    ///   ("line",   x1, y1, x2, y2, Color)
    ///   ("points", [(x,y),...], Color)
    ///   ("rect",   x, y, w, h, Color)
    ///   ("circle", x, y, r, Color)
    ///   ("print",  x, y, text_str)
    #[staticmethod]
    #[pyo3(signature = (
        shapes=vec![],
        x_bounds=(0.0f64, 1.0f64), y_bounds=(0.0f64, 1.0f64),
        background=None, marker=None
    ))]
    fn canvas(
        shapes: Vec<Py<PyAny>>,
        x_bounds: (f64, f64),
        y_bounds: (f64, f64),
        background: Option<PyColor>,
        marker: Option<u8>,
    ) -> PyResult<Self> {
        let ir_shapes = Python::attach(|py| -> PyResult<Vec<IrCanvasShape>> {
            shapes
                .iter()
                .map(|s| {
                    let s = s.bind(py);
                    let tag: String = s.get_item(0)?.extract()?;
                    match tag.as_str() {
                        "line" => Ok(IrCanvasShape::Line {
                            x1: s.get_item(1)?.extract()?,
                            y1: s.get_item(2)?.extract()?,
                            x2: s.get_item(3)?.extract()?,
                            y2: s.get_item(4)?.extract()?,
                            color: s.get_item(5)?.extract::<PyColor>()?.inner,
                        }),
                        "points" => Ok(IrCanvasShape::Points {
                            coords: s.get_item(1)?.extract()?,
                            color: s.get_item(2)?.extract::<PyColor>()?.inner,
                        }),
                        "rect" => Ok(IrCanvasShape::Rect {
                            x: s.get_item(1)?.extract()?,
                            y: s.get_item(2)?.extract()?,
                            width: s.get_item(3)?.extract()?,
                            height: s.get_item(4)?.extract()?,
                            color: s.get_item(5)?.extract::<PyColor>()?.inner,
                        }),
                        "circle" => Ok(IrCanvasShape::Circle {
                            x: s.get_item(1)?.extract()?,
                            y: s.get_item(2)?.extract()?,
                            radius: s.get_item(3)?.extract()?,
                            color: s.get_item(4)?.extract::<PyColor>()?.inner,
                        }),
                        "print" => Ok(IrCanvasShape::Print {
                            x: s.get_item(1)?.extract()?,
                            y: s.get_item(2)?.extract()?,
                            text: s.get_item(3)?.extract::<String>()?,
                        }),
                        other => Err(pyo3::exceptions::PyValueError::new_err(format!(
                            "unknown canvas shape tag: {other:?}"
                        ))),
                    }
                })
                .collect()
        })?;
        Ok(Self {
            inner: RenderIrInner::Canvas {
                x_bounds: [x_bounds.0, x_bounds.1],
                y_bounds: [y_bounds.0, y_bounds.1],
                background_color: background.map(|c| c.inner),
                marker: marker.map(marker_from_u8),
                shapes: ir_shapes,
            },
        })
    }

    // ── Measure ───────────────────────────────────────────────────────────────

    fn measure(&self) -> (u16, u16) {
        match &self.inner {
            RenderIrInner::Span { content, .. } => (content.len() as u16, 1),
            RenderIrInner::Line { line } => (line_width(line) as u16, 1),
            RenderIrInner::Text { text, .. } => {
                let h = text.lines.len().max(1) as u16;
                let w = text.lines.iter().map(line_width).max().unwrap_or(0) as u16;
                (w, h)
            }
            RenderIrInner::Paragraph { text, .. } => {
                let h = text.lines.len().max(1) as u16;
                let w = text.lines.iter().map(line_width).max().unwrap_or(0) as u16;
                (w, h)
            }
            RenderIrInner::List { items, highlight_symbol, .. } => {
                if items.is_empty() {
                    return (0, 1);
                }
                let sym_w = highlight_symbol.len() as u16;
                let w = items
                    .iter()
                    .flat_map(|t| t.lines.iter())
                    .map(line_width)
                    .max()
                    .unwrap_or(0) as u16;
                (w + sym_w, items.len() as u16)
            }
            RenderIrInner::ProgressBar { .. } => (0, 1),
            RenderIrInner::Clear => (0, 0),
            RenderIrInner::Sparkline { .. } => (0, 1),
            RenderIrInner::LineGauge { .. } => (0, 1),
            RenderIrInner::BarChart { .. } => (0, 0),
            RenderIrInner::Table { rows, header, footer, .. } => {
                let mut row_count = rows.len() as u16;
                if header.is_some() { row_count += 1; }
                if footer.is_some() { row_count += 1; }
                (0, row_count)
            }
            RenderIrInner::Scrollbar { orientation, .. } => match orientation {
                ScrollbarOrientation::HorizontalBottom | ScrollbarOrientation::HorizontalTop => {
                    (0, 1)
                }
                _ => (1, 0),
            },
            RenderIrInner::Tabs { .. } => (0, 1),
            RenderIrInner::Canvas { .. } => (0, 0),
        }
    }
}

fn line_width(line: &Line<'_>) -> usize {
    line.spans.iter().map(|s| s.content.len()).sum()
}

// ── Rust-internal rendering ───────────────────────────────────────────────────

impl CoreRenderIR {
    pub(crate) fn render_to_buffer(&self, rect: Rect, buf: &mut Buffer) -> PyResult<()> {
        match &self.inner {
            RenderIrInner::Span { content, style } => {
                let span = Span::styled(content.clone(), *style);
                Widget::render(Paragraph::new(Line::from(vec![span])), rect, buf);
            }

            RenderIrInner::Line { line } => {
                Widget::render(Paragraph::new(vec![line.clone()]), rect, buf);
            }

            RenderIrInner::Text { text, style } => {
                Widget::render(Paragraph::new(text.clone()).style(*style), rect, buf);
            }

            RenderIrInner::Paragraph { text, style, align, wrap } => {
                let mut para = Paragraph::new(text.clone()).style(*style);
                if *wrap { para = para.wrap(Wrap { trim: true }); }
                if let Some(a) = align { para = para.alignment(*a); }
                Widget::render(para, rect, buf);
            }

            RenderIrInner::List {
                items, selected, style, highlight_style, highlight_symbol,
            } => {
                let list_items: Vec<ListItem<'_>> =
                    items.iter().map(|t| ListItem::new(t.clone())).collect();
                let rat_list = List::new(list_items)
                    .style(*style)
                    .highlight_style(*highlight_style)
                    .highlight_symbol(highlight_symbol.as_str());
                if let Some(sel) = selected {
                    let mut state = ListState::default();
                    state.select(Some(*sel));
                    StatefulWidget::render(rat_list, rect, buf, &mut state);
                } else {
                    Widget::render(rat_list, rect, buf);
                }
            }

            RenderIrInner::ProgressBar { progress, label, style } => {
                let clamped = progress.clamp(0.0, 1.0);
                let mut gauge = Gauge::default().ratio(clamped).style(*style);
                if let Some(lbl) = label { gauge = gauge.label(lbl.clone()); }
                Widget::render(gauge, rect, buf);
            }

            RenderIrInner::Clear => {
                Widget::render(Clear, rect, buf);
            }

            RenderIrInner::Sparkline {
                data, max_value, style, absent_value_style, absent_value_symbol,
            } => {
                let mut spark = Sparkline::default()
                    .data(data)
                    .style(*style)
                    .absent_value_style(*absent_value_style);
                if let Some(mv) = max_value { spark = spark.max(*mv); }
                if let Some(sym) = absent_value_symbol {
                    spark = spark.absent_value_symbol(sym.as_str());
                }
                Widget::render(spark, rect, buf);
            }

            RenderIrInner::LineGauge {
                progress, label, style, filled_style, unfilled_style,
            } => {
                let mut lg = LineGauge::default()
                    .ratio(progress.clamp(0.0, 1.0))
                    .style(*style)
                    .filled_style(*filled_style)
                    .unfilled_style(*unfilled_style);
                if let Some(lbl) = label { lg = lg.label(lbl.clone()); }
                Widget::render(lg, rect, buf);
            }

            RenderIrInner::BarChart {
                groups, bar_width, bar_gap, group_gap,
                max_value, horizontal, bar_style, value_style, label_style,
            } => {
                let mut chart = BarChart::default()
                    .bar_width(*bar_width)
                    .bar_gap(*bar_gap)
                    .group_gap(*group_gap)
                    .bar_style(*bar_style)
                    .value_style(*value_style)
                    .label_style(*label_style);
                if let Some(mv) = max_value { chart = chart.max(*mv); }
                if *horizontal { chart = chart.direction(Direction::Horizontal); }

                for (group_label, bars) in groups {
                    let rat_bars: Vec<Bar<'_>> = bars
                        .iter()
                        .map(|(val, blabel, text_val, bstyle, vstyle)| {
                            let mut b = Bar::default()
                                .value(*val)
                                .label(blabel.as_str().into())
                                .style(*bstyle)
                                .value_style(*vstyle);
                            if let Some(tv) = text_val { b = b.text_value(tv.clone()); }
                            b
                        })
                        .collect();
                    let mut g = BarGroup::default().bars(&rat_bars);
                    if let Some(lbl) = group_label { g = g.label(lbl.as_str().into()); }
                    chart = chart.data(g);
                }
                Widget::render(chart, rect, buf);
            }

            RenderIrInner::Table {
                rows, header, footer, widths,
                column_spacing, selected_row, selected_column,
                row_highlight_style, highlight_symbol,
            } => {
                let make_row = |(cells, row_style, height): &(Vec<(Text<'static>, Style)>, Style, u16)| {
                    let rat_cells: Vec<Cell<'_>> = cells
                        .iter()
                        .map(|(text, style)| Cell::new(text.clone()).style(*style))
                        .collect();
                    let mut row = Row::new(rat_cells).style(*row_style);
                    if *height != 1 { row = row.height(*height); }
                    row
                };

                let constraints: Vec<Constraint> = widths
                    .iter()
                    .map(|(kind, val)| constraint_from_kind(*kind, *val))
                    .collect();

                let rat_rows: Vec<Row<'_>> = rows.iter().map(make_row).collect();
                let mut table = Table::new(rat_rows, constraints)
                    .column_spacing(*column_spacing)
                    .row_highlight_style(*row_highlight_style);
                if let Some(hdr) = header { table = table.header(make_row(hdr)); }
                if let Some(ftr) = footer { table = table.footer(make_row(ftr)); }
                if let Some(sym) = highlight_symbol {
                    table = table.highlight_symbol(sym.as_str());
                }
                if selected_row.is_some() || selected_column.is_some() {
                    let mut state = TableState::default();
                    if let Some(r) = selected_row { state.select(Some(*r)); }
                    if let Some(c) = selected_column { state.select_column(Some(*c)); }
                    StatefulWidget::render(table, rect, buf, &mut state);
                } else {
                    Widget::render(table, rect, buf);
                }
            }

            RenderIrInner::Scrollbar {
                orientation, content_length, position, viewport_length,
                style, thumb_style, track_style, begin_symbol, end_symbol,
            } => {
                let sb = Scrollbar::new(orientation.clone())
                    .style(*style)
                    .thumb_style(*thumb_style)
                    .track_style(*track_style)
                    .begin_symbol(begin_symbol.as_deref())
                    .end_symbol(end_symbol.as_deref());
                let mut state = ScrollbarState::new(*content_length).position(*position);
                if let Some(vl) = viewport_length {
                    state = state.viewport_content_length(*vl);
                }
                StatefulWidget::render(sb, rect, buf, &mut state);
            }

            RenderIrInner::Tabs {
                titles, selected, style, highlight_style,
                divider, padding_left, padding_right,
            } => {
                let mut tabs = Tabs::new(titles.clone())
                    .select(*selected)
                    .style(*style)
                    .highlight_style(*highlight_style)
                    .padding_left(padding_left.as_str())
                    .padding_right(padding_right.as_str());
                if let Some(div) = divider { tabs = tabs.divider(div.as_str()); }
                Widget::render(tabs, rect, buf);
            }

            RenderIrInner::Canvas {
                x_bounds, y_bounds, background_color, marker, shapes,
            } => {
                // Build owned copies for the closure
                let xb = *x_bounds;
                let yb = *y_bounds;
                let bg = *background_color;
                let mk = *marker;

                // Flatten shape data into owned scalars for closure capture
                let mut line_data: Vec<(f64, f64, f64, f64, Color)> = Vec::new();
                let mut point_data: Vec<(Vec<(f64, f64)>, Color)> = Vec::new();
                let mut rect_data: Vec<(f64, f64, f64, f64, Color)> = Vec::new();
                let mut circle_data: Vec<(f64, f64, f64, Color)> = Vec::new();
                let mut print_data: Vec<(f64, f64, String)> = Vec::new();
                // shape_kinds: one entry per shape in original order
                let mut shape_kinds: Vec<(u8, usize)> = Vec::new();

                for shape in shapes {
                    match shape {
                        IrCanvasShape::Line { x1, y1, x2, y2, color } => {
                            shape_kinds.push((0, line_data.len()));
                            line_data.push((*x1, *y1, *x2, *y2, *color));
                        }
                        IrCanvasShape::Points { coords, color } => {
                            shape_kinds.push((1, point_data.len()));
                            point_data.push((coords.clone(), *color));
                        }
                        IrCanvasShape::Rect { x, y, width, height, color } => {
                            shape_kinds.push((2, rect_data.len()));
                            rect_data.push((*x, *y, *width, *height, *color));
                        }
                        IrCanvasShape::Circle { x, y, radius, color } => {
                            shape_kinds.push((3, circle_data.len()));
                            circle_data.push((*x, *y, *radius, *color));
                        }
                        IrCanvasShape::Print { x, y, text } => {
                            shape_kinds.push((4, print_data.len()));
                            print_data.push((*x, *y, text.clone()));
                        }
                    }
                }

                let mut canvas = ratatui::widgets::canvas::Canvas::default()
                    .x_bounds(xb)
                    .y_bounds(yb);
                if let Some(bgc) = bg { canvas = canvas.background_color(bgc); }
                if let Some(m) = mk { canvas = canvas.marker(m); }

                let canvas = canvas.paint(move |ctx| {
                    for (kind, idx) in &shape_kinds {
                        match kind {
                            0 => {
                                let (x1, y1, x2, y2, color) = line_data[*idx];
                                ctx.draw(&CanvasLine { x1, y1, x2, y2, color });
                            }
                            1 => {
                                let (ref coords, color) = point_data[*idx];
                                ctx.draw(&Points { coords, color });
                            }
                            2 => {
                                let (x, y, width, height, color) = rect_data[*idx];
                                ctx.draw(&Rectangle { x, y, width, height, color });
                            }
                            3 => {
                                let (x, y, radius, color) = circle_data[*idx];
                                ctx.draw(&Circle { x, y, radius, color });
                            }
                            4 => {
                                let (x, y, ref text) = print_data[*idx];
                                ctx.print(x, y, Line::raw(text.clone()));
                            }
                            _ => {}
                        }
                    }
                });
                Widget::render(canvas, rect, buf);
            }
        }
        Ok(())
    }
}

pub fn register_render_ir(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyIrLine>()?;
    m.add_class::<CoreRenderIR>()?;
    Ok(())
}
