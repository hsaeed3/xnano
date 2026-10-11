//! The ratatui `List` with its `ListState`: a scrollable list with a selection.
//!
//! Maps to `ratatui::widgets::List`, `ListItem`, `ListState`, `HighlightSpacing` and
//! `ListDirection`. This module also holds the pieces the table and tabs widgets share:
//! [`TextSource`], [`Selection`], [`Feedback`] and the style key helpers.

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
use crate::widgets::{Resolver, Shared, WidgetSpec};

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
    items: Vec<(Vec<Line>, Style)>,
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

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Self::Resolved, EvalError> {
        let mut items = Vec::with_capacity(self.items.len());
        for item in &self.items {
            items.push((
                item.content.resolve(resolver)?,
                item.style.resolve(resolver)?,
            ));
        }
        let spacing = resolver.get(&self.highlight_spacing)?;
        let direction = resolver.get(&self.direction)?;
        Ok(ResolvedList {
            items,
            selected: resolver.get(&self.selected)?.0,
            offset: resolver.get(&self.offset)?,
            offset_epoch: self.offset_epoch,
            style: self.style.resolve(resolver)?,
            highlight_style: self.highlight_style.resolve(resolver)?,
            highlight_symbol: resolver.get(&self.highlight_symbol)?,
            repeat_highlight_symbol: resolver.get(&self.repeat_highlight_symbol)?,
            highlight_spacing: highlight_spacing_from_name(&spacing)?,
            direction: direction_from_name(&direction)?,
            scroll_padding: resolver.get(&self.scroll_padding)?,
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
        let start = resolved
            .feedback
            .start_offset(resolved.offset, resolved.offset_epoch);
        let mut state = ListState::default()
            .with_offset(start)
            .with_selected(resolved.selected);
        StatefulWidget::render(list, area, grid.buffer_mut(), &mut state);
        let offset = state.offset();
        let mut used = 0_usize;
        let mut end = offset;
        for (lines, _) in resolved.items.iter().skip(offset) {
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
