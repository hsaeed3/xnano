//! Ready-made terminal components that paint into a buffer's cells.
//!
//! Each component is plain data. Painting renders a ratatui widget into a copy of the
//! target region and writes the result back, so components share cells with text, pixels
//! and images.

use ratatui::widgets::{
    Bar, BarChart, BarGroup, Cell as TableCell, Gauge, LineGauge, List, ListItem, ListState,
    Paragraph, Row, Scrollbar, ScrollbarOrientation, ScrollbarState, Sparkline, StatefulWidget,
    Table, TableState, Tabs, Widget as _, Wrap,
};
use ratatui_core::layout::{Constraint, Direction, Rect};
use ratatui_core::text::{Line as RLine, Span as RSpan, Text};

use crate::grid::{Bounds, Grid};
use crate::style::Style;
use crate::text::Line;

/// Styled rows converted for ratatui.
pub fn to_text(lines: &[Line]) -> Text<'static> {
    Text::from(
        lines
            .iter()
            .map(|line| {
                RLine::from(
                    line.iter()
                        .map(|span| RSpan::styled(span.text.clone(), span.style))
                        .collect::<Vec<_>>(),
                )
            })
            .collect::<Vec<_>>(),
    )
}

#[derive(Debug, Clone, PartialEq)]
pub struct BarSpec {
    pub value: u64,
    pub label: String,
    pub text_value: Option<String>,
    pub style: Style,
}

#[derive(Debug, Clone, PartialEq)]
pub struct BarGroupSpec {
    pub bars: Vec<BarSpec>,
    pub label: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct TableCellSpec {
    pub content: Vec<Line>,
    pub style: Style,
}

#[derive(Debug, Clone, PartialEq)]
pub struct TableRowSpec {
    pub cells: Vec<TableCellSpec>,
    pub height: u16,
    pub style: Style,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ScrollbarSide {
    Left,
    Right,
    Top,
    Bottom,
}

impl ScrollbarSide {
    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "left" => Self::Left,
            "right" => Self::Right,
            "top" => Self::Top,
            "bottom" => Self::Bottom,
            _ => return None,
        })
    }
}

/// A component and everything needed to paint it.
#[derive(Debug, Clone, PartialEq)]
pub enum Component {
    ItemList {
        items: Vec<Vec<Line>>,
        selected_index: Option<usize>,
        style: Style,
        highlight_style: Style,
        highlight_symbol: String,
    },
    Gauge {
        ratio: f64,
        label: Option<String>,
        style: Style,
    },
    LineGauge {
        ratio: f64,
        label: Option<String>,
        filled_style: Style,
        unfilled_style: Style,
    },
    Sparkline {
        values: Vec<u64>,
        maximum: Option<u64>,
        style: Style,
    },
    BarChart {
        groups: Vec<BarGroupSpec>,
        bar_width: u16,
        bar_gap: u16,
        group_gap: u16,
        maximum: Option<u64>,
        is_horizontal: bool,
    },
    Table {
        rows: Vec<TableRowSpec>,
        header: Option<TableRowSpec>,
        footer: Option<TableRowSpec>,
        column_widths: Vec<u16>,
        column_spacing: u16,
        selected_row: Option<usize>,
        selected_column: Option<usize>,
        highlight_style: Style,
    },
    Scrollbar {
        content_length: usize,
        position: usize,
        viewport_length: Option<usize>,
        side: ScrollbarSide,
        style: Style,
    },
    Tabs {
        titles: Vec<Vec<Line>>,
        selected_index: usize,
        style: Style,
        highlight_style: Style,
        divider: String,
    },
    /// Text with a visible cursor and optional wrapping, as an editor draws it.
    Paragraph {
        lines: Vec<Line>,
        style: Style,
        should_wrap: bool,
    },
}

impl Component {
    fn render(&self, area: Rect, buffer: &mut ratatui_core::buffer::Buffer) {
        match self {
            Self::ItemList {
                items,
                selected_index,
                style,
                highlight_style,
                highlight_symbol,
            } => {
                let list = List::new(items.iter().map(|item| ListItem::new(to_text(item))))
                    .style(*style)
                    .highlight_style(*highlight_style)
                    .highlight_symbol(highlight_symbol.as_str());
                let mut state = ListState::default();
                state.select(*selected_index);
                StatefulWidget::render(list, area, buffer, &mut state);
            }
            Self::Gauge {
                ratio,
                label,
                style,
            } => {
                let mut gauge = Gauge::default()
                    .ratio(ratio.clamp(0.0, 1.0))
                    .use_unicode(true)
                    .gauge_style(*style);
                if let Some(label) = label {
                    gauge = gauge.label(label.clone());
                }
                gauge.render(area, buffer);
            }
            Self::LineGauge {
                ratio,
                label,
                filled_style,
                unfilled_style,
            } => {
                let mut gauge = LineGauge::default()
                    .ratio(ratio.clamp(0.0, 1.0))
                    .filled_style(*filled_style)
                    .unfilled_style(*unfilled_style);
                if let Some(label) = label {
                    gauge = gauge.label(label.clone());
                }
                gauge.render(area, buffer);
            }
            Self::Sparkline {
                values,
                maximum,
                style,
            } => {
                let mut sparkline = Sparkline::default().data(values).style(*style);
                if let Some(maximum) = maximum {
                    sparkline = sparkline.max(*maximum);
                }
                sparkline.render(area, buffer);
            }
            Self::BarChart {
                groups,
                bar_width,
                bar_gap,
                group_gap,
                maximum,
                is_horizontal,
            } => {
                let mut chart = BarChart::default()
                    .bar_width(*bar_width)
                    .bar_gap(*bar_gap)
                    .group_gap(*group_gap)
                    .direction(if *is_horizontal {
                        Direction::Horizontal
                    } else {
                        Direction::Vertical
                    });
                if let Some(maximum) = maximum {
                    chart = chart.max(*maximum);
                }
                for group in groups {
                    let bars: Vec<Bar<'_>> = group
                        .bars
                        .iter()
                        .map(|bar| {
                            let mut drawn = Bar::default()
                                .value(bar.value)
                                .label(bar.label.as_str())
                                .style(bar.style);
                            if let Some(text) = &bar.text_value {
                                drawn = drawn.text_value(text.clone());
                            }
                            drawn
                        })
                        .collect();
                    let mut drawn_group = BarGroup::default().bars(&bars);
                    if let Some(label) = &group.label {
                        drawn_group = drawn_group.label(label.as_str());
                    }
                    chart = chart.data(drawn_group);
                }
                chart.render(area, buffer);
            }
            Self::Table {
                rows,
                header,
                footer,
                column_widths,
                column_spacing,
                selected_row,
                selected_column,
                highlight_style,
            } => {
                let make_row = |row: &TableRowSpec| {
                    Row::new(
                        row.cells
                            .iter()
                            .map(|cell| TableCell::new(to_text(&cell.content)).style(cell.style)),
                    )
                    .style(row.style)
                    .height(row.height.max(1))
                };
                let column_count = rows
                    .iter()
                    .chain(header)
                    .chain(footer)
                    .map(|row| row.cells.len())
                    .max()
                    .unwrap_or(0);
                let widths: Vec<Constraint> = if column_widths.is_empty() {
                    vec![Constraint::Fill(1); column_count]
                } else {
                    column_widths
                        .iter()
                        .map(|width| Constraint::Length(*width))
                        .collect()
                };
                let mut table = Table::new(rows.iter().map(make_row), widths)
                    .column_spacing(*column_spacing)
                    .row_highlight_style(*highlight_style);
                if let Some(header) = header {
                    table = table.header(make_row(header));
                }
                if let Some(footer) = footer {
                    table = table.footer(make_row(footer));
                }
                let mut state = TableState::default();
                state.select(*selected_row);
                state.select_column(*selected_column);
                StatefulWidget::render(table, area, buffer, &mut state);
            }
            Self::Scrollbar {
                content_length,
                position,
                viewport_length,
                side,
                style,
            } => {
                let orientation = match side {
                    ScrollbarSide::Left => ScrollbarOrientation::VerticalLeft,
                    ScrollbarSide::Right => ScrollbarOrientation::VerticalRight,
                    ScrollbarSide::Top => ScrollbarOrientation::HorizontalTop,
                    ScrollbarSide::Bottom => ScrollbarOrientation::HorizontalBottom,
                };
                let mut state = ScrollbarState::new(*content_length).position(*position);
                if let Some(viewport) = viewport_length {
                    state = state.viewport_content_length(*viewport);
                }
                StatefulWidget::render(
                    Scrollbar::new(orientation).style(*style),
                    area,
                    buffer,
                    &mut state,
                );
            }
            Self::Tabs {
                titles,
                selected_index,
                style,
                highlight_style,
                divider,
            } => {
                Tabs::new(
                    titles
                        .iter()
                        .map(|title| to_text(title).lines.into_iter().next().unwrap_or_default()),
                )
                .select(*selected_index)
                .style(*style)
                .highlight_style(*highlight_style)
                .divider(divider.as_str())
                .render(area, buffer);
            }
            Self::Paragraph {
                lines,
                style,
                should_wrap,
            } => {
                let mut paragraph = Paragraph::new(to_text(lines)).style(*style);
                if *should_wrap {
                    paragraph = paragraph.wrap(Wrap { trim: false });
                }
                paragraph.render(area, buffer);
            }
        }
    }

    /// Paint over `bounds` of `grid`.
    pub fn paint(&self, grid: &mut Grid, bounds: Bounds) {
        if bounds.width() == 0 || bounds.height() == 0 {
            return;
        }
        let mut region = grid.region_buffer(bounds);
        let area = Rect::new(0, 0, bounds.width(), bounds.height());
        self.render(area, &mut region);
        grid.replace_region(bounds, &region);
    }
}
