//! The ratatui `List` with its `ListState`: a scrollable list with a selection.
//!
//! Maps to `ratatui::widgets::List`, `ListItem`, `ListState`, `HighlightSpacing` and
//! `ListDirection`. This module also holds the pieces the table and tabs widgets share:
//! [`TextSource`], [`Selection`], [`Feedback`] and the style key helpers.

use std::collections::hash_map::DefaultHasher;
use std::fmt;
use std::sync::{Arc, Mutex};

use ratatui::widgets::{
    HighlightSpacing, List, ListDirection, ListItem, ListState, StatefulWidget,
};
use ratatui_core::layout::Rect;
use ratatui_core::style::Style;
use ratatui_core::text::Text;

use crate::components::to_text;
use crate::dynamic::{Dynamic, FromScalar};
use crate::expression::{EvalError, Expr, Scalar};
use crate::grid::Grid;
use crate::text::{Line, Span, split_lines};
use crate::widgets::block::{BlockSpec, ResolvedBlock, resolve_optional};
use crate::widgets::style::StyleSpec;
use crate::widgets::{Resolver, Shared, WidgetSpec, hash_debug};

/// A selected position, or none.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Selection(pub Option<usize>);

impl FromScalar for Selection {
    fn from_scalar(scalar: &Scalar) -> Result<Self, EvalError> {
        match scalar {
            Scalar::Null => Ok(Self(None)),
            other => usize::from_scalar(other).map(|index| Self(Some(index))),
        }
    }
}

/// Styled text that is fixed or follows a text expression.
#[derive(Debug, Clone)]
pub enum TextSource {
    Fixed(Vec<Line>),
    Bound(Arc<Expr>),
}

impl TextSource {
    /// Whether the text is fixed rather than following an expression.
    pub fn is_fixed(&self) -> bool {
        matches!(self, Self::Fixed(_))
    }

    /// Plain text with no styling.
    pub fn plain(text: &str) -> Self {
        Self::Fixed(split_lines(&[Span::new(text, Style::default())]))
    }

    pub fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Vec<Line>, EvalError> {
        match self {
            Self::Fixed(lines) => Ok(lines.clone()),
            Self::Bound(expr) => {
                let text = String::from_scalar(&expr.evaluate(resolver.environment)?)?;
                Ok(split_lines(&[Span::new(text, Style::default())]))
            }
        }
    }

    /// Whether two sources are the same text, or the same expression.
    pub fn same_as(&self, other: &Self) -> bool {
        match (self, other) {
            (Self::Fixed(a), Self::Fixed(b)) => a == b,
            (Self::Bound(a), Self::Bound(b)) => Arc::ptr_eq(a, b),
            _ => false,
        }
    }

    /// A stable key for hashing and comparing.
    pub fn key(&self) -> String {
        match self {
            Self::Fixed(lines) => format!("{lines:?}"),
            Self::Bound(expr) => format!("bound@{:p}", Arc::as_ptr(expr)),
        }
    }

    /// The plain text, or `None` for a bound source.
    pub fn plain_text(&self) -> Option<String> {
        match self {
            Self::Fixed(lines) => Some(
                lines
                    .iter()
                    .map(|line| {
                        line.iter()
                            .map(|span| span.text.as_str())
                            .collect::<String>()
                    })
                    .collect::<Vec<_>>()
                    .join("\n"),
            ),
            Self::Bound(_) => None,
        }
    }
}

/// A key describing a style spec by value, with bound colors by identity.
pub fn style_key(style: &StyleSpec) -> String {
    fn color_key(color: Option<&Dynamic<crate::style::Color>>) -> String {
        match color {
            None => "-".to_owned(),
            Some(Dynamic::Fixed(color)) => format!("{color:?}"),
            Some(Dynamic::Bound(expr)) => format!("bound@{:p}", Arc::as_ptr(expr)),
        }
    }
    format!(
        "{}|{}|{}|{:?}|{:?}",
        color_key(style.foreground.as_ref()),
        color_key(style.background.as_ref()),
        color_key(style.underline_color.as_ref()),
        style.add_modifier,
        style.remove_modifier
    )
}

/// What painting learned that the settings alone cannot say.
#[derive(Debug, Default)]
pub struct Feedback {
    /// The scroll offset the last paint ended at.
    pub offset: usize,
    /// The offset setting and edit count the last paint started from.
    pub seen: Option<(usize, u64)>,
    /// The first and one past the last item or row shown.
    pub visible: Option<(usize, usize)>,
}

/// A shared [`Feedback`] that hashes and prints as nothing, so it never forces a repaint.
#[derive(Clone, Default)]
pub struct FeedbackHandle(pub Arc<Mutex<Feedback>>);

impl fmt::Debug for FeedbackHandle {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("feedback")
    }
}

impl FeedbackHandle {
    pub fn read(&self) -> std::sync::MutexGuard<'_, Feedback> {
        self.0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
    }

    /// The offset a paint should start from.
    pub fn start_offset(&self, setting: usize, epoch: u64) -> usize {
        let feedback = self.read();
        if feedback.seen == Some((setting, epoch)) {
            feedback.offset
        } else {
            setting
        }
    }

    pub fn record(&self, setting: usize, epoch: u64, offset: usize, visible: (usize, usize)) {
        let mut feedback = self.read();
        feedback.seen = Some((setting, epoch));
        feedback.offset = offset;
        feedback.visible = Some(visible);
    }
}

pub const HIGHLIGHT_SPACINGS: [(&str, HighlightSpacing); 3] = [
    ("always", HighlightSpacing::Always),
    ("when_selected", HighlightSpacing::WhenSelected),
    ("never", HighlightSpacing::Never),
];

pub fn highlight_spacing_from_name(name: &str) -> Result<HighlightSpacing, EvalError> {
    HIGHLIGHT_SPACINGS
        .iter()
        .find(|(candidate, _)| *candidate == name)
        .map(|(_, spacing)| spacing.clone())
        .ok_or_else(|| {
            EvalError::Type(format!(
                "\"{name}\" is not a highlight spacing; use \"always\", \"when_selected\" or \"never\""
            ))
        })
}

pub fn direction_from_name(name: &str) -> Result<ListDirection, EvalError> {
    match name {
        "top_to_bottom" => Ok(ListDirection::TopToBottom),
        "bottom_to_top" => Ok(ListDirection::BottomToTop),
        other => Err(EvalError::Type(format!(
            "\"{other}\" is not a list direction; use \"top_to_bottom\" or \"bottom_to_top\""
        ))),
    }
}

/// One item of a list.
#[derive(Debug, Clone)]
pub struct ItemSpec {
    pub content: TextSource,
    pub style: StyleSpec,
}

#[derive(Debug, Clone)]
pub struct ListSpec {
    pub items: Vec<ItemSpec>,
    pub selected: Dynamic<Selection>,
    pub offset: Dynamic<usize>,
    /// Counts edits to `offset`, so setting it to the same number again scrolls back to it.
    pub offset_epoch: u64,
    pub style: StyleSpec,
    pub highlight_style: StyleSpec,
    pub highlight_symbol: Dynamic<String>,
    pub repeat_highlight_symbol: Dynamic<bool>,
    pub highlight_spacing: Dynamic<String>,
    pub direction: Dynamic<String>,
    pub scroll_padding: Dynamic<usize>,
    pub block: Option<Shared<BlockSpec>>,
    pub feedback: FeedbackHandle,
}

impl Default for ListSpec {
    fn default() -> Self {
        Self {
            items: Vec::new(),
            selected: Dynamic::Fixed(Selection(None)),
            offset: Dynamic::Fixed(0),
            offset_epoch: 0,
            style: StyleSpec::default(),
            highlight_style: StyleSpec::default(),
            highlight_symbol: Dynamic::Fixed(String::new()),
            repeat_highlight_symbol: Dynamic::Fixed(false),
            highlight_spacing: Dynamic::Fixed("when_selected".to_owned()),
            direction: Dynamic::Fixed("top_to_bottom".to_owned()),
            scroll_padding: Dynamic::Fixed(0),
            block: None,
            feedback: FeedbackHandle::default(),
        }
    }
}

#[derive(Debug)]
pub struct ResolvedList {
    /// Only the items that can be shown, starting at index `first` of the whole list.
    items: Vec<(Vec<Line>, Style)>,
    first: usize,
    /// The offset the paint starts scrolling from (a position in the whole list).
    start: usize,
    selected: Option<usize>,
    offset: usize,
    offset_epoch: u64,
    style: Style,
    highlight_style: Style,
    highlight_symbol: String,
    repeat_highlight_symbol: bool,
    highlight_spacing: HighlightSpacing,
    direction: ListDirection,
    scroll_padding: usize,
    block: Option<ResolvedBlock>,
    feedback: FeedbackHandle,
}

impl WidgetSpec for ListSpec {
    type Resolved = ResolvedList;

    fn hash_bindings(
        &self,
        resolver: &mut Resolver<'_>,
        hasher: &mut DefaultHasher,
    ) -> Option<Result<(), EvalError>> {
        Some((|| {
            for item in &self.items {
                if !item.content.is_fixed() {
                    hash_debug(&item.content.resolve(resolver)?, hasher);
                }
                if !item.style.is_static() {
                    hash_debug(&item.style.resolve(resolver)?, hasher);
                }
            }
            resolver.hash_bound(&self.selected, hasher)?;
            resolver.hash_bound(&self.offset, hasher)?;
            resolver.hash_bound(&self.highlight_symbol, hasher)?;
            resolver.hash_bound(&self.repeat_highlight_symbol, hasher)?;
            resolver.hash_bound(&self.highlight_spacing, hasher)?;
            resolver.hash_bound(&self.direction, hasher)?;
            resolver.hash_bound(&self.scroll_padding, hasher)?;
            for style in [&self.style, &self.highlight_style] {
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
        let selected = resolver.get(&self.selected)?.0;
        let offset = resolver.get(&self.offset)?;
        let scroll_padding = resolver.get(&self.scroll_padding)?;
        let total = self.items.len();
        let start = self.feedback.start_offset(offset, self.offset_epoch);
        // Only the items that can be shown are read: from the earlier of the scroll offset
        // and the selection (less its padding), to a screenful past the later one. Every
        // item takes at least one row, so that always covers what ratatui draws.
        let (first, last) = match resolver.size() {
            Some((_, height)) if total > 0 => {
                // The scroll padding keeps items above the selection in view too.
                let lowest = selected.map_or(start, |position| {
                    position.saturating_sub(scroll_padding).min(start)
                });
                let highest = selected.map_or(start, |position| position.max(start));
                let first = lowest.min(total - 1);
                let last = highest
                    .saturating_add(usize::from(height))
                    .saturating_add(scroll_padding)
                    .saturating_add(1)
                    .min(total);
                (first, last.max(first + 1))
            }
            _ => (0, total),
        };
        let mut items = Vec::with_capacity(last - first);
        for item in &self.items[first..last] {
            items.push((
                item.content.resolve(resolver)?,
                item.style.resolve(resolver)?,
            ));
        }
        let spacing = resolver.get(&self.highlight_spacing)?;
        let direction = resolver.get(&self.direction)?;
        Ok(ResolvedList {
            items,
            first,
            start,
            selected,
            offset,
            offset_epoch: self.offset_epoch,
            style: self.style.resolve(resolver)?,
            highlight_style: self.highlight_style.resolve(resolver)?,
            highlight_symbol: resolver.get(&self.highlight_symbol)?,
            repeat_highlight_symbol: resolver.get(&self.repeat_highlight_symbol)?,
            highlight_spacing: highlight_spacing_from_name(&spacing)?,
            direction: direction_from_name(&direction)?,
            scroll_padding,
            block: resolve_optional(&self.block, resolver)?,
            feedback: self.feedback.clone(),
        })
    }

    fn draw(resolved: &Self::Resolved, grid: &mut Grid) {
        let area = Rect::new(0, 0, grid.width(), grid.height());
        let mut list = List::new(
            resolved
                .items
                .iter()
                .map(|(lines, style)| ListItem::new(to_text(lines)).style(*style))
                .collect::<Vec<ListItem<'_>>>(),
        )
        .style(resolved.style)
        .highlight_style(resolved.highlight_style)
        .highlight_symbol(resolved.highlight_symbol.as_str())
        .repeat_highlight_symbol(resolved.repeat_highlight_symbol)
        .highlight_spacing(resolved.highlight_spacing.clone())
        .direction(resolved.direction)
        .scroll_padding(resolved.scroll_padding);
        let mut inner = area;
        if let Some(block) = &resolved.block {
            inner = block.inner(area);
            list = list.block(block.to_widget());
        }
        let first = resolved.first;
        let mut state = ListState::default()
            .with_offset(resolved.start.saturating_sub(first))
            .with_selected(
                resolved
                    .selected
                    .map(|position| position.saturating_sub(first)),
            );
        StatefulWidget::render(list, area, grid.buffer_mut(), &mut state);
        let offset = state.offset() + first;
        let mut used = 0_usize;
        let mut end = offset;
        for (lines, _) in resolved.items.iter().skip(offset - first) {
            let height = lines.len().max(1);
            if used + height > usize::from(inner.height) {
                break;
            }
            used += height;
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

/// Plain `Text` for tests and callers that need ratatui text.
pub fn text_of(lines: &[Line]) -> Text<'static> {
    to_text(lines)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::expression::{Environment, EvalError, PropertyId};

    struct Offline;

    impl Environment for Offline {
        fn property(&self, id: PropertyId) -> Result<Scalar, EvalError> {
            Err(EvalError::RuntimeRequired(id.name().to_owned()))
        }
    }

    fn spec(count: usize, direction: &str, scroll_padding: usize) -> ListSpec {
        ListSpec {
            items: (0..count)
                .map(|index| ItemSpec {
                    // Every third item takes two rows.
                    content: TextSource::plain(&if index % 3 == 0 {
                        format!("item {index}\nsecond row {index}")
                    } else {
                        format!("item {index}")
                    }),
                    style: StyleSpec::default(),
                })
                .collect(),
            highlight_symbol: Dynamic::Fixed("> ".to_owned()),
            direction: Dynamic::Fixed(direction.to_owned()),
            scroll_padding: Dynamic::Fixed(scroll_padding),
            ..ListSpec::default()
        }
    }

    fn paint(spec: &ListSpec, height: u16, with_size: bool) -> (Grid, (usize, usize)) {
        let mut resolver = Resolver::new(&Offline);
        if with_size {
            resolver = resolver.with_size(20, height);
        }
        let resolved = spec.resolve(&mut resolver).expect("the list resolves");
        let mut grid = Grid::new(20, height);
        ListSpec::draw(&resolved, &mut grid);
        let visible = spec.feedback.read().visible.expect("the paint recorded");
        (grid, visible)
    }

    /// Showing only the items that fit paints exactly what showing all of them paints,
    /// however the selection and the scroll offset move.
    #[test]
    fn a_windowed_list_paints_like_the_whole_list() {
        let selections = [
            Some(0),
            Some(1),
            Some(5),
            Some(6),
            Some(40),
            Some(41),
            Some(7),
            Some(0),
            Some(99),
            Some(500),
            None,
            Some(50),
            Some(49),
            Some(2),
        ];
        for direction in ["top_to_bottom", "bottom_to_top"] {
            for scroll_padding in [0, 2] {
                for height in [1_u16, 4, 9] {
                    for count in [0_usize, 1, 7, 100] {
                        let windowed = spec(count, direction, scroll_padding);
                        let whole = spec(count, direction, scroll_padding);
                        for selected in selections {
                            let mut windowed_spec = windowed.clone();
                            windowed_spec.selected = Dynamic::Fixed(Selection(selected));
                            let mut whole_spec = whole.clone();
                            whole_spec.selected = Dynamic::Fixed(Selection(selected));
                            // The feedback handles are shared with the originals, so the
                            // scroll offset carries over from step to step.
                            let (expected, expected_visible) = paint(&whole_spec, height, false);
                            let (actual, actual_visible) = paint(&windowed_spec, height, true);
                            assert_eq!(
                                actual.buffer(),
                                expected.buffer(),
                                "{direction} padding {scroll_padding} height {height} \
                                 count {count} selected {selected:?}"
                            );
                            assert_eq!(actual_visible, expected_visible);
                        }
                    }
                }
            }
        }
    }
}
