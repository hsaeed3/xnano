//! The ratatui `Tabs`: a row of titles with one selected.
//!
//! Maps to `ratatui::widgets::Tabs`.

use ratatui::widgets::Tabs;
use ratatui_core::layout::Rect;
use ratatui_core::style::Style;
use ratatui_core::text::{Line as RLine, Span as RSpan};
use ratatui_core::widgets::Widget;

use crate::dynamic::Dynamic;
use crate::expression::EvalError;
use crate::grid::Grid;
use crate::text::Line;
use crate::widgets::block::{BlockSpec, ResolvedBlock, resolve_optional};
use crate::widgets::list::{Selection, TextSource};
use crate::widgets::style::StyleSpec;
use crate::widgets::{Resolver, Shared, WidgetSpec};

#[derive(Debug, Clone)]
pub struct TabsSpec {
    pub titles: Vec<TextSource>,
    pub selected: Dynamic<Selection>,
    pub style: StyleSpec,
    pub highlight_style: StyleSpec,
    pub divider: TextSource,
    pub padding_left: TextSource,
    pub padding_right: TextSource,
    pub block: Option<Shared<BlockSpec>>,
}

impl Default for TabsSpec {
    fn default() -> Self {
        Self {
            titles: Vec::new(),
            selected: Dynamic::Fixed(Selection(Some(0))),
            style: StyleSpec::default(),
            highlight_style: StyleSpec::default(),
            divider: TextSource::plain("|"),
            padding_left: TextSource::plain(" "),
            padding_right: TextSource::plain(" "),
            block: None,
        }
    }
}

#[derive(Debug)]
pub struct ResolvedTabs {
    titles: Vec<Vec<Line>>,
    selected: Option<usize>,
    style: Style,
    highlight_style: Style,
    divider: Vec<Line>,
    padding_left: Vec<Line>,
    padding_right: Vec<Line>,
    block: Option<ResolvedBlock>,
}

fn first_line(lines: &[Line]) -> RLine<'static> {
    RLine::from(
        lines
            .first()
            .map(|line| {
                line.iter()
                    .map(|span| RSpan::styled(span.text.clone(), span.style))
                    .collect::<Vec<_>>()
            })
            .unwrap_or_default(),
    )
}

fn divider_span(lines: &[Line]) -> RSpan<'static> {
    let Some(line) = lines.first() else {
        return RSpan::raw("");
    };
    let style = line.first().map(|span| span.style).unwrap_or_default();
    RSpan::styled(
        line.iter()
            .map(|span| span.text.as_str())
            .collect::<String>(),
        style,
    )
}

impl WidgetSpec for TabsSpec {
    type Resolved = ResolvedTabs;

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Self::Resolved, EvalError> {
        let mut titles = Vec::with_capacity(self.titles.len());
        for title in &self.titles {
            titles.push(title.resolve(resolver)?);
        }
        Ok(ResolvedTabs {
            titles,
            selected: resolver.get(&self.selected)?.0,
            style: self.style.resolve(resolver)?,
            highlight_style: self.highlight_style.resolve(resolver)?,
            divider: self.divider.resolve(resolver)?,
            padding_left: self.padding_left.resolve(resolver)?,
            padding_right: self.padding_right.resolve(resolver)?,
            block: resolve_optional(&self.block, resolver)?,
        })
    }

    fn draw(resolved: &Self::Resolved, grid: &mut Grid) {
        let area = Rect::new(0, 0, grid.width(), grid.height());
        let mut tabs = Tabs::new(resolved.titles.iter().map(|lines| first_line(lines)))
            .select(resolved.selected)
            .style(resolved.style)
            .highlight_style(resolved.highlight_style)
            .divider(divider_span(&resolved.divider))
            .padding(
                first_line(&resolved.padding_left),
                first_line(&resolved.padding_right),
            );
        if let Some(block) = &resolved.block {
            tabs = tabs.block(block.to_widget());
        }
        tabs.render(area, grid.buffer_mut());
    }
}
