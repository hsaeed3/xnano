//! The ratatui `Table` with its `TableState`: rows and columns with a selection.
//!
//! Maps to `ratatui::widgets::Table`, `Row`, `Cell` and `TableState`.

use std::collections::hash_map::DefaultHasher;

use ratatui::widgets::{
    Cell as TableCell, HighlightSpacing, Row, StatefulWidget, Table, TableState,
};
use ratatui_core::layout::{Constraint, Flex, Rect};
use ratatui_core::style::Style;

use crate::components::to_text;
use crate::dynamic::Dynamic;
use crate::expression::EvalError;
use crate::grid::Grid;
use crate::text::Line;
use crate::widgets::block::{BlockSpec, ResolvedBlock, resolve_optional};
use crate::widgets::list::{
    FeedbackHandle, Selection, TextSource, highlight_spacing_from_name, style_key,
};
use crate::widgets::style::StyleSpec;
use crate::widgets::{Resolver, Shared, WidgetSpec, hash_debug};

/// How wide a column is.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WidthRule {
    Length(u16),
    Percentage(u16),
    Ratio(u32, u32),
    Minimum(u16),
    Maximum(u16),
    Fill(u16),
}

impl WidthRule {
    pub fn to_constraint(self) -> Constraint {
        match self {
            Self::Length(amount) => Constraint::Length(amount),
            Self::Percentage(amount) => Constraint::Percentage(amount),
            Self::Ratio(numerator, denominator) => Constraint::Ratio(numerator, denominator),
            Self::Minimum(amount) => Constraint::Min(amount),
            Self::Maximum(amount) => Constraint::Max(amount),
            Self::Fill(weight) => Constraint::Fill(weight),
        }
    }
}

pub const FLEXES: [(&str, Flex); 7] = [
    ("legacy", Flex::Legacy),
    ("start", Flex::Start),
    ("center", Flex::Center),
    ("end", Flex::End),
    ("space_between", Flex::SpaceBetween),
    ("space_around", Flex::SpaceAround),
    ("space_evenly", Flex::SpaceEvenly),
];

pub fn flex_from_name(name: &str) -> Result<Flex, EvalError> {
    FLEXES
        .iter()
        .find(|(candidate, _)| *candidate == name)
        .map(|(_, flex)| *flex)
        .ok_or_else(|| {
            EvalError::Type(format!(
                "\"{name}\" is not a flex mode; use legacy, start, center, end, space_between, \
                 space_around or space_evenly"
            ))
        })
}

#[derive(Debug, Clone)]
pub struct CellSpec {
    pub content: TextSource,
    pub style: StyleSpec,
    pub column_span: u16,
}

impl CellSpec {
    pub fn key(&self) -> String {
        format!(
            "{}|{}|{}",
            self.content.key(),
            style_key(&self.style),
            self.column_span
        )
    }
}

#[derive(Debug, Clone)]
pub struct RowSpec {
    pub cells: Vec<CellSpec>,
    pub height: u16,
    pub top_margin: u16,
    pub bottom_margin: u16,
    pub style: StyleSpec,
}

impl RowSpec {
    /// Hash the current value of everything in the row that follows an expression.
    fn hash_bound(
        &self,
        resolver: &mut Resolver<'_>,
        hasher: &mut DefaultHasher,
    ) -> Result<(), EvalError> {
        if !self.style.is_static() {
            hash_debug(&self.style.resolve(resolver)?, hasher);
        }
        for cell in &self.cells {
            if !cell.content.is_fixed() {
                hash_debug(&cell.content.resolve(resolver)?, hasher);
            }
            if !cell.style.is_static() {
                hash_debug(&cell.style.resolve(resolver)?, hasher);
            }
        }
        Ok(())
    }

    pub fn key(&self) -> String {
        format!(
            "{}|{}|{}|{}|{}",
            self.cells
                .iter()
                .map(CellSpec::key)
                .collect::<Vec<_>>()
                .join(";"),
            self.height,
            self.top_margin,
            self.bottom_margin,
            style_key(&self.style)
        )
    }

    /// How many columns the row covers, counting spans.
    pub fn column_count(&self) -> usize {
        self.cells
            .iter()
            .map(|cell| usize::from(cell.column_span.max(1)))
            .sum()
    }
}

#[derive(Debug, Clone)]
pub struct TableSpec {
    pub rows: Vec<RowSpec>,
    pub header: Option<RowSpec>,
    pub footer: Option<RowSpec>,
    pub widths: Vec<WidthRule>,
    pub column_spacing: Dynamic<u16>,
    pub flex: Dynamic<String>,
    pub selected_row: Dynamic<Selection>,
    pub selected_column: Dynamic<Selection>,
    pub offset: Dynamic<usize>,
    /// Counts edits to `offset`, so setting it to the same number again scrolls back to it.
    pub offset_epoch: u64,
    pub style: StyleSpec,
    pub row_highlight_style: StyleSpec,
    pub column_highlight_style: StyleSpec,
    pub cell_highlight_style: StyleSpec,
    pub highlight_symbol: Dynamic<String>,
    pub highlight_spacing: Dynamic<String>,
    pub block: Option<Shared<BlockSpec>>,
    pub feedback: FeedbackHandle,
}

impl Default for TableSpec {
    fn default() -> Self {
        Self {
            rows: Vec::new(),
            header: None,
            footer: None,
            widths: Vec::new(),
            column_spacing: Dynamic::Fixed(1),
            flex: Dynamic::Fixed("start".to_owned()),
            selected_row: Dynamic::Fixed(Selection(None)),
            selected_column: Dynamic::Fixed(Selection(None)),
            offset: Dynamic::Fixed(0),
            offset_epoch: 0,
            style: StyleSpec::default(),
            row_highlight_style: StyleSpec::default(),
            column_highlight_style: StyleSpec::default(),
            cell_highlight_style: StyleSpec::default(),
            highlight_symbol: Dynamic::Fixed(String::new()),
            highlight_spacing: Dynamic::Fixed("when_selected".to_owned()),
            block: None,
            feedback: FeedbackHandle::default(),
        }
    }
}

impl TableSpec {
    /// The most columns any row covers.
    pub fn column_count(&self) -> usize {
        self.rows
            .iter()
            .chain(self.header.iter())
            .chain(self.footer.iter())
            .map(RowSpec::column_count)
            .max()
            .unwrap_or(0)
    }
}

type ResolvedCell = (Vec<Line>, Style, u16);
type ResolvedRow = (Vec<ResolvedCell>, u16, u16, u16, Style);

fn resolve_row(row: &RowSpec, resolver: &mut Resolver<'_>) -> Result<ResolvedRow, EvalError> {
    let mut cells = Vec::with_capacity(row.cells.len());
    for cell in &row.cells {
        cells.push((
            cell.content.resolve(resolver)?,
            cell.style.resolve(resolver)?,
            cell.column_span.max(1),
        ));
    }
    Ok((
        cells,
        row.height.max(1),
        row.top_margin,
        row.bottom_margin,
        row.style.resolve(resolver)?,
    ))
}

fn build_row(row: &ResolvedRow) -> Row<'static> {
    let (cells, height, top, bottom, style) = row;
    Row::new(cells.iter().map(|(lines, cell_style, span)| {
        TableCell::new(to_text(lines))
            .style(*cell_style)
            .column_span(*span)
    }))
    .height(*height)
    .top_margin(*top)
    .bottom_margin(*bottom)
    .style(*style)
}

#[derive(Debug)]
pub struct ResolvedTable {
    rows: Vec<ResolvedRow>,
    header: Option<ResolvedRow>,
    footer: Option<ResolvedRow>,
    widths: Vec<WidthRule>,
    column_count: usize,
    column_spacing: u16,
    flex: Flex,
    selected_row: Option<usize>,
    selected_column: Option<usize>,
    offset: usize,
    offset_epoch: u64,
    style: Style,
    row_highlight_style: Style,
    column_highlight_style: Style,
    cell_highlight_style: Style,
    highlight_symbol: String,
    highlight_spacing: HighlightSpacing,
    block: Option<ResolvedBlock>,
    feedback: FeedbackHandle,
}

impl WidgetSpec for TableSpec {
    type Resolved = ResolvedTable;

    fn hash_bindings(
        &self,
        resolver: &mut Resolver<'_>,
        hasher: &mut DefaultHasher,
    ) -> Option<Result<(), EvalError>> {
        Some((|| {
            for row in self
                .rows
                .iter()
                .chain(self.header.iter())
                .chain(self.footer.iter())
            {
                row.hash_bound(resolver, hasher)?;
            }
            resolver.hash_bound(&self.column_spacing, hasher)?;
            resolver.hash_bound(&self.flex, hasher)?;
            resolver.hash_bound(&self.selected_row, hasher)?;
            resolver.hash_bound(&self.selected_column, hasher)?;
            resolver.hash_bound(&self.offset, hasher)?;
            resolver.hash_bound(&self.highlight_symbol, hasher)?;
            resolver.hash_bound(&self.highlight_spacing, hasher)?;
            for style in [
                &self.style,
                &self.row_highlight_style,
                &self.column_highlight_style,
                &self.cell_highlight_style,
            ] {
                if !style.is_static() {
                    hash_debug(&style.resolve(resolver)?, hasher);
                }
            }
            if let Some(block) = &self.block
                && !block.read().is_static()
            {
                hash_debug(&resolve_optional(&self.block, resolver)?, hasher);
            }
            Ok(())
        })())
    }

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Self::Resolved, EvalError> {
        let mut rows = Vec::with_capacity(self.rows.len());
        for row in &self.rows {
            rows.push(resolve_row(row, resolver)?);
        }
        let flex = resolver.get(&self.flex)?;
        let spacing = resolver.get(&self.highlight_spacing)?;
        Ok(ResolvedTable {
            rows,
            header: self
                .header
                .as_ref()
                .map(|row| resolve_row(row, resolver))
                .transpose()?,
            footer: self
                .footer
                .as_ref()
                .map(|row| resolve_row(row, resolver))
                .transpose()?,
            widths: self.widths.clone(),
            column_count: self.column_count(),
            column_spacing: resolver.get(&self.column_spacing)?,
            flex: flex_from_name(&flex)?,
            selected_row: resolver.get(&self.selected_row)?.0,
            selected_column: resolver.get(&self.selected_column)?.0,
            offset: resolver.get(&self.offset)?,
            offset_epoch: self.offset_epoch,
            style: self.style.resolve(resolver)?,
            row_highlight_style: self.row_highlight_style.resolve(resolver)?,
            column_highlight_style: self.column_highlight_style.resolve(resolver)?,
            cell_highlight_style: self.cell_highlight_style.resolve(resolver)?,
            highlight_symbol: resolver.get(&self.highlight_symbol)?,
            highlight_spacing: highlight_spacing_from_name(&spacing)?,
            block: resolve_optional(&self.block, resolver)?,
            feedback: self.feedback.clone(),
        })
    }

    fn draw(resolved: &Self::Resolved, grid: &mut Grid) {
        let area = Rect::new(0, 0, grid.width(), grid.height());
        let widths: Vec<Constraint> = if resolved.widths.is_empty() {
            vec![Constraint::Fill(1); resolved.column_count]
        } else {
            resolved
                .widths
                .iter()
                .map(|rule| rule.to_constraint())
                .collect()
        };
        let mut table = Table::new(resolved.rows.iter().map(build_row), widths)
            .column_spacing(resolved.column_spacing)
            .flex(resolved.flex)
            .style(resolved.style)
            .row_highlight_style(resolved.row_highlight_style)
            .column_highlight_style(resolved.column_highlight_style)
            .cell_highlight_style(resolved.cell_highlight_style)
            .highlight_symbol(resolved.highlight_symbol.as_str())
            .highlight_spacing(resolved.highlight_spacing.clone());
        if let Some(header) = &resolved.header {
            table = table.header(build_row(header));
        }
        if let Some(footer) = &resolved.footer {
            table = table.footer(build_row(footer));
        }
        let mut inner = area;
        if let Some(block) = &resolved.block {
            inner = block.inner(area);
            table = table.block(block.to_widget());
        }
        let start = resolved
            .feedback
            .start_offset(resolved.offset, resolved.offset_epoch);
        let mut state = TableState::new()
            .with_offset(start)
            .with_selected(resolved.selected_row)
            .with_selected_column(resolved.selected_column);
        StatefulWidget::render(table, area, grid.buffer_mut(), &mut state);
        let offset = state.offset();
        let extra = |row: &Option<ResolvedRow>| {
            row.as_ref().map_or(0, |(_, height, top, bottom, _)| {
                usize::from(*height) + usize::from(*top) + usize::from(*bottom)
            })
        };
        let available = usize::from(inner.height)
            .saturating_sub(extra(&resolved.header))
            .saturating_sub(extra(&resolved.footer));
        let mut used = 0_usize;
        let mut end = offset;
        for (_, height, top, bottom, _) in resolved.rows.iter().skip(offset) {
            let total = usize::from(*height) + usize::from(*top) + usize::from(*bottom);
            if used + total > available {
                break;
            }
            used += total;
            end += 1;
        }
        resolved.feedback.record(
            resolved.offset,
            resolved.offset_epoch,
            offset,
            (offset, end),
        );
    }
}
