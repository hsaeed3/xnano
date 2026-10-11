//! The ratatui `BarChart`: groups of labelled bars, vertical or horizontal.
//!
//! Maps to `ratatui::widgets::BarChart`, `Bar` and `BarGroup`.

use ratatui::widgets::{Bar, BarChart, BarGroup};
use ratatui_core::layout::{Direction, Rect};
use ratatui_core::style::Style;
use ratatui_core::widgets::Widget;

use crate::dynamic::Dynamic;
use crate::expression::EvalError;
use crate::grid::Grid;
use crate::widgets::block::{BlockSpec, ResolvedBlock, resolve_optional};
use crate::widgets::sparkline::resolve_bar_set;
use crate::widgets::style::StyleSpec;
use crate::widgets::{Resolver, Shared, WidgetSpec};

/// One bar.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct BarData {
    pub value: u64,
    pub label: Option<String>,
    /// Shown on the bar instead of the number.
    pub text_value: Option<String>,
    pub style: Style,
    pub value_style: Style,
}

/// Bars drawn together under one label.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct BarGroupData {
    pub label: Option<String>,
    pub bars: Vec<BarData>,
}

impl BarData {
    fn to_widget(&self) -> Bar<'static> {
        let mut bar = Bar::new(self.value)
            .style(self.style)
            .value_style(self.value_style);
        if let Some(label) = &self.label {
            bar = bar.label(label.clone());
        }
        if let Some(text) = &self.text_value {
            bar = bar.text_value(text.clone());
        }
        bar
    }
}

#[derive(Debug, Clone)]
pub struct BarChartSpec {
    pub groups: Vec<BarGroupData>,
    pub bar_width: Dynamic<u16>,
    pub bar_gap: Dynamic<u16>,
    pub group_gap: Dynamic<u16>,
    /// The value that fills a bar completely; `None` uses the largest value shown.
    pub maximum: Option<Dynamic<u64>>,
    /// `"vertical"` or `"horizontal"`.
    pub direction: Dynamic<String>,
    pub bar_style: StyleSpec,
    pub value_style: StyleSpec,
    pub label_style: StyleSpec,
    pub style: StyleSpec,
    pub bar_set: Dynamic<String>,
    pub block: Option<Shared<BlockSpec>>,
}

impl Default for BarChartSpec {
    fn default() -> Self {
        Self {
            groups: Vec::new(),
            bar_width: Dynamic::Fixed(1),
            bar_gap: Dynamic::Fixed(1),
            group_gap: Dynamic::Fixed(0),
            maximum: None,
            direction: Dynamic::Fixed("vertical".to_owned()),
            bar_style: StyleSpec::default(),
            value_style: StyleSpec::default(),
            label_style: StyleSpec::default(),
            style: StyleSpec::default(),
            bar_set: Dynamic::Fixed("nine_levels".to_owned()),
            block: None,
        }
    }
}

#[derive(Debug)]
pub struct ResolvedBarChart {
    groups: Vec<BarGroupData>,
    bar_width: u16,
    bar_gap: u16,
    group_gap: u16,
    maximum: Option<u64>,
    direction: Direction,
    bar_style: Style,
    value_style: Style,
    label_style: Style,
    style: Style,
    bar_set: ratatui::symbols::bar::Set<'static>,
    block: Option<ResolvedBlock>,
}

impl WidgetSpec for BarChartSpec {
    type Resolved = ResolvedBarChart;

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Self::Resolved, EvalError> {
        let direction = match resolver.get(&self.direction)?.as_str() {
            "vertical" => Direction::Vertical,
            "horizontal" => Direction::Horizontal,
            other => {
                return Err(EvalError::Type(format!(
                    "\"{other}\" is not a direction; use \"vertical\" or \"horizontal\""
                )));
            }
        };
        Ok(ResolvedBarChart {
            groups: self.groups.clone(),
            bar_width: resolver.get(&self.bar_width)?,
            bar_gap: resolver.get(&self.bar_gap)?,
            group_gap: resolver.get(&self.group_gap)?,
            maximum: resolver.get_optional(&self.maximum)?,
            direction,
            bar_style: self.bar_style.resolve(resolver)?,
            value_style: self.value_style.resolve(resolver)?,
            label_style: self.label_style.resolve(resolver)?,
            style: self.style.resolve(resolver)?,
            bar_set: resolve_bar_set(&resolver.get(&self.bar_set)?)?,
            block: resolve_optional(&self.block, resolver)?,
        })
    }

    fn draw(resolved: &Self::Resolved, grid: &mut Grid) {
        let mut chart = BarChart::default()
            .direction(resolved.direction)
            .bar_width(resolved.bar_width)
            .bar_gap(resolved.bar_gap)
            .group_gap(resolved.group_gap)
            .bar_style(resolved.bar_style)
            .value_style(resolved.value_style)
            .label_style(resolved.label_style)
            .style(resolved.style)
            .bar_set(resolved.bar_set.clone());
        if let Some(maximum) = resolved.maximum {
            chart = chart.max(maximum);
        }
        if let Some(block) = &resolved.block {
            chart = chart.block(block.to_widget());
        }
        for group in &resolved.groups {
            let bars = group
                .bars
                .iter()
                .map(BarData::to_widget)
                .collect::<Vec<_>>();
            let mut widget = BarGroup::new(bars);
            if let Some(label) = &group.label {
                widget = widget.label(label.clone());
            }
            chart = chart.data(widget);
        }
        let area = Rect::new(0, 0, grid.width(), grid.height());
        chart.render(area, grid.buffer_mut());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::expression::{Environment, PropertyId, Scalar};
    use crate::painter::{Painter, Spec};
    use crate::widgets::SpecPainter;

    struct Offline;
    impl Environment for Offline {
        fn property(&self, id: PropertyId) -> Result<Scalar, EvalError> {
            Err(EvalError::RuntimeRequired(id.name().to_owned()))
        }
    }

    fn bar(value: u64, label: &str) -> BarData {
        BarData {
            value,
            label: Some(label.to_owned()),
            text_value: None,
            style: Style::default(),
            value_style: Style::default(),
        }
    }

    fn render(spec: BarChartSpec, width: u16, height: u16) -> Vec<String> {
        let painter = SpecPainter::new(Spec::new(spec));
        let mut grid = Grid::filled(width, height, &crate::grid::blank_cell());
        painter.fingerprint(&Offline).expect("resolves");
        painter.paint(&mut grid, &Offline).expect("paints");
        grid.text_rows()
    }

    #[test]
    fn vertical_bars_grow_with_their_values_and_show_labels() {
        let spec = BarChartSpec {
            groups: vec![BarGroupData {
                label: None,
                bars: vec![bar(4, "a"), bar(8, "b")],
            }],
            ..BarChartSpec::default()
        };
        let rows = render(spec, 3, 3);
        assert_eq!(rows[2].trim_end(), "a b");
        assert!(rows[0].contains('█'));
    }

    #[test]
    fn an_unknown_direction_is_explained() {
        let spec = BarChartSpec {
            direction: Dynamic::Fixed("diagonal".to_owned()),
            ..BarChartSpec::default()
        };
        let painter = SpecPainter::new(Spec::new(spec));
        let error = painter.fingerprint(&Offline).expect_err("rejects");
        assert!(error.to_string().contains("\"vertical\""));
    }
}
