//! The ratatui `Paragraph`: styled, optionally wrapped and scrolled text.
//!
//! Maps to `ratatui::widgets::Paragraph`.

use std::sync::Arc;

use ratatui::widgets::{Paragraph, Wrap};
use ratatui_core::layout::{Alignment, Rect};
use ratatui_core::style::Style;
use ratatui_core::widgets::Widget;

use crate::components::to_text;
use crate::dynamic::Dynamic;
use crate::expression::{EvalError, Expr};
use crate::grid::Grid;
use crate::style::Style as TextStyle;
use crate::text::{Line, Span, has_wide_glyphs, split_lines, wrap_lines};
use crate::widgets::block::{BlockSpec, ResolvedBlock, alignment_from_name, resolve_optional};
use crate::widgets::style::StyleSpec;
use crate::widgets::{Resolver, Shared, WidgetSpec};

/// The text of a paragraph: styled rows, or an expression that produces plain text.
#[derive(Debug, Clone)]
pub enum TextSetting {
    Fixed(Vec<Line>),
    Bound(Arc<Expr>),
}

impl TextSetting {
    /// The rows to show.
    pub fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Vec<Line>, EvalError> {
        match self {
            Self::Fixed(lines) => Ok(lines.clone()),
            Self::Bound(expression) => {
                let text = resolver.get(&Dynamic::<String>::Bound(Arc::clone(expression)))?;
                Ok(split_lines(&[Span::new(text, TextStyle::default())]))
            }
        }
    }
}

#[derive(Debug, Clone)]
pub struct ParagraphSpec {
    pub text: TextSetting,
    pub style: StyleSpec,
    /// `"left"`, `"center"` or `"right"`.
    pub alignment: Dynamic<String>,
    pub should_wrap: Dynamic<bool>,
    /// Whether wrapped rows lose their leading whitespace.
    pub should_trim: Dynamic<bool>,
    pub scroll_row: Dynamic<u16>,
    pub scroll_column: Dynamic<u16>,
    pub block: Option<Shared<BlockSpec>>,
}

impl ParagraphSpec {
    pub fn new(text: TextSetting) -> Self {
        Self {
            text,
            style: StyleSpec::default(),
            alignment: Dynamic::Fixed("left".to_owned()),
            should_wrap: Dynamic::Fixed(false),
            should_trim: Dynamic::Fixed(false),
            scroll_row: Dynamic::Fixed(0),
            scroll_column: Dynamic::Fixed(0),
            block: None,
        }
    }
}

#[derive(Debug)]
pub struct ResolvedParagraph {
    lines: Vec<Line>,
    style: Style,
    alignment: Alignment,
    wrap: Option<Wrap>,
    scroll: (u16, u16),
    block: Option<ResolvedBlock>,
}

impl ResolvedParagraph {
    /// The widget for an area `width` columns wide.
    ///
    /// Text with wide glyphs is wrapped here, because the wrapping of the widget itself lets a
    /// wide glyph overhang the last column of a row and loses it.
    fn to_widget(&self, width: u16) -> Paragraph<'static> {
        let inner_width = self.block.as_ref().map_or(width, |block| {
            block
                .to_widget()
                .inner(Rect::new(0, 0, width, u16::MAX))
                .width
        });
        let wraps_itself = self.wrap.is_some() && has_wide_glyphs(&self.lines);
        let text = if wraps_itself {
            to_text(&wrap_lines(&self.lines, usize::from(inner_width)))
        } else {
            to_text(&self.lines)
        };
        let mut paragraph = Paragraph::new(text)
            .style(self.style)
            .alignment(self.alignment)
            .scroll(self.scroll);
        if let (Some(wrap), false) = (self.wrap, wraps_itself) {
            paragraph = paragraph.wrap(wrap);
        }
        if let Some(block) = &self.block {
            paragraph = paragraph.block(block.to_widget());
        }
        paragraph
    }

    /// How many rows the paragraph takes at `width` columns.
    pub fn line_count(&self, width: u16) -> usize {
        self.to_widget(width).line_count(width)
    }

    /// The width in columns of the widest row.
    pub fn line_width(&self) -> usize {
        self.to_widget(u16::MAX).line_width()
    }
}

impl ParagraphSpec {
    /// Read every setting, for measuring without drawing.
    pub fn resolve_now(&self, resolver: &mut Resolver<'_>) -> Result<ResolvedParagraph, EvalError> {
        <Self as WidgetSpec>::resolve(self, resolver)
    }
}

impl WidgetSpec for ParagraphSpec {
    type Resolved = ResolvedParagraph;

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Self::Resolved, EvalError> {
        let alignment_name = resolver.get(&self.alignment)?;
        let alignment = alignment_from_name(&alignment_name).ok_or_else(|| {
            EvalError::Type(format!(
                "\"{alignment_name}\" is not an alignment; use \"left\", \"center\" or \"right\""
            ))
        })?;
        let should_wrap = resolver.get(&self.should_wrap)?;
        let should_trim = resolver.get(&self.should_trim)?;
        let wrap = should_wrap.then_some(Wrap { trim: should_trim });
        Ok(ResolvedParagraph {
            lines: self.text.resolve(resolver)?,
            style: self.style.resolve(resolver)?,
            alignment,
            wrap,
            scroll: (
                resolver.get(&self.scroll_row)?,
                resolver.get(&self.scroll_column)?,
            ),
            block: resolve_optional(&self.block, resolver)?,
        })
    }

    fn draw(resolved: &Self::Resolved, grid: &mut Grid) {
        let area = Rect::new(0, 0, grid.width(), grid.height());
        resolved
            .to_widget(area.width)
            .render(area, grid.buffer_mut());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::expression::{Environment, PropertyId, Scalar};

    struct Offline;
    impl Environment for Offline {
        fn property(&self, id: PropertyId) -> Result<Scalar, EvalError> {
            Err(EvalError::RuntimeRequired(id.name().to_owned()))
        }
    }

    fn lines(text: &str) -> Vec<Line> {
        split_lines(&[Span::new(text, TextStyle::default())])
    }

    #[test]
    fn a_paragraph_draws_wrapped_text() {
        let mut spec = ParagraphSpec::new(TextSetting::Fixed(lines("one two three")));
        spec.should_wrap = Dynamic::Fixed(true);
        let resolved = spec.resolve_now(&mut Resolver::new(&Offline)).unwrap();
        assert_eq!(resolved.line_count(7), 2);
        let mut grid = Grid::new(7, 2);
        ParagraphSpec::draw(&resolved, &mut grid);
        assert_eq!(
            grid.text_rows(),
            vec!["one two".to_owned(), "three".to_owned()]
        );
    }

    #[test]
    fn bound_text_comes_from_the_expression() {
        let spec = ParagraphSpec::new(TextSetting::Bound(Expr::literal(Scalar::Text("hi".into()))));
        let resolved = spec.resolve_now(&mut Resolver::new(&Offline)).unwrap();
        assert_eq!(resolved.line_width(), 2);
    }

    #[test]
    fn an_unknown_alignment_explains_the_choices() {
        let mut spec = ParagraphSpec::new(TextSetting::Fixed(Vec::new()));
        spec.alignment = Dynamic::Fixed("middle".to_owned());
        let error = spec.resolve_now(&mut Resolver::new(&Offline)).unwrap_err();
        assert!(
            error
                .to_string()
                .contains("\"left\", \"center\" or \"right\"")
        );
    }
}
