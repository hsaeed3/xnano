//! The ratatui `Sparkline`: a row of bars showing a series of values.
//!
//! Maps to `ratatui::widgets::Sparkline`.

use ratatui::symbols::bar;
use ratatui::widgets::{RenderDirection, Sparkline, SparklineBar};
use ratatui_core::layout::Rect;
use ratatui_core::style::Style;
use ratatui_core::widgets::Widget;

use crate::dynamic::Dynamic;
use crate::expression::EvalError;
use crate::grid::Grid;
use crate::widgets::block::{BlockSpec, ResolvedBlock, resolve_optional};
use crate::widgets::style::StyleSpec;
use crate::widgets::{Resolver, Shared, WidgetSpec};

/// The bar symbol sets a sparkline or bar chart can draw with.
pub const BAR_SETS: [(&str, bar::Set<'static>); 2] = [
    ("nine_levels", bar::NINE_LEVELS),
    ("three_levels", bar::THREE_LEVELS),
];

/// The bar symbol set called `name`, if there is one.
pub fn bar_set_from_name(name: &str) -> Option<bar::Set<'static>> {
    BAR_SETS
        .iter()
        .find(|(candidate, _)| *candidate == name)
        .map(|(_, set)| set.clone())
}

/// A bar set setting, resolved or explained.
pub fn resolve_bar_set(name: &str) -> Result<bar::Set<'static>, EvalError> {
    bar_set_from_name(name).ok_or_else(|| {
        EvalError::Type(format!(
            "\"{name}\" is not a bar set; use \"nine_levels\" or \"three_levels\""
        ))
    })
}

/// One value of a sparkline, with an optional style of its own.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct SparklineBarData {
    /// `None` marks an absent value, which is drawn differently from zero.
    pub value: Option<u64>,
    pub style: Option<Style>,
}

#[derive(Debug, Clone)]
pub struct SparklineSpec {
    pub bars: Vec<SparklineBarData>,
    /// The value that fills a bar completely; `None` uses the largest value shown.
    pub maximum: Option<Dynamic<u64>>,
    pub style: StyleSpec,
    pub absent_value_style: StyleSpec,
    pub absent_value_symbol: Option<Dynamic<String>>,
    /// `"left_to_right"` or `"right_to_left"`.
    pub direction: Dynamic<String>,
    pub bar_set: Dynamic<String>,
    pub block: Option<Shared<BlockSpec>>,
}

impl Default for SparklineSpec {
    fn default() -> Self {
        Self {
            bars: Vec::new(),
            maximum: None,
            style: StyleSpec::default(),
            absent_value_style: StyleSpec::default(),
            absent_value_symbol: None,
            direction: Dynamic::Fixed("left_to_right".to_owned()),
            bar_set: Dynamic::Fixed("nine_levels".to_owned()),
            block: None,
        }
    }
}

#[derive(Debug)]
pub struct ResolvedSparkline {
    bars: Vec<SparklineBarData>,
    maximum: Option<u64>,
    style: Style,
    absent_value_style: Style,
    absent_value_symbol: Option<String>,
    direction: RenderDirection,
    bar_set: bar::Set<'static>,
    block: Option<ResolvedBlock>,
}

impl WidgetSpec for SparklineSpec {
    type Resolved = ResolvedSparkline;

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Self::Resolved, EvalError> {
        let direction = match resolver.get(&self.direction)?.as_str() {
            "left_to_right" => RenderDirection::LeftToRight,
            "right_to_left" => RenderDirection::RightToLeft,
            other => {
                return Err(EvalError::Type(format!(
                    "\"{other}\" is not a direction; use \"left_to_right\" or \"right_to_left\""
                )));
            }
        };
        Ok(ResolvedSparkline {
            bars: self.bars.clone(),
            maximum: resolver.get_optional(&self.maximum)?,
            style: self.style.resolve(resolver)?,
            absent_value_style: self.absent_value_style.resolve(resolver)?,
            absent_value_symbol: resolver.get_optional(&self.absent_value_symbol)?,
            direction,
            bar_set: resolve_bar_set(&resolver.get(&self.bar_set)?)?,
            block: resolve_optional(&self.block, resolver)?,
        })
    }

    fn draw(resolved: &Self::Resolved, grid: &mut Grid) {
        let bars = resolved
            .bars
            .iter()
            .map(|entry| SparklineBar::from(entry.value).style(entry.style))
            .collect::<Vec<_>>();
        let mut sparkline = Sparkline::default()
            .data(bars)
            .style(resolved.style)
            .absent_value_style(resolved.absent_value_style)
            .bar_set(resolved.bar_set.clone())
            .direction(resolved.direction);
        if let Some(maximum) = resolved.maximum {
            sparkline = sparkline.max(maximum);
        }
        if let Some(symbol) = &resolved.absent_value_symbol {
            sparkline = sparkline.absent_value_symbol(symbol.clone());
        }
        if let Some(block) = &resolved.block {
            sparkline = sparkline.block(block.to_widget());
        }
        let area = Rect::new(0, 0, grid.width(), grid.height());
        sparkline.render(area, grid.buffer_mut());
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

    fn render(spec: SparklineSpec, width: u16) -> String {
        let painter = SpecPainter::new(Spec::new(spec));
        let mut grid = Grid::filled(width, 1, &crate::grid::blank_cell());
        painter.fingerprint(&Offline).expect("resolves");
        painter.paint(&mut grid, &Offline).expect("paints");
        grid.text_rows().join("")
    }

    fn bars(values: &[Option<u64>]) -> Vec<SparklineBarData> {
        values
            .iter()
            .map(|value| SparklineBarData {
                value: *value,
                style: None,
            })
            .collect()
    }

    #[test]
    fn bars_scale_to_the_largest_value() {
        let spec = SparklineSpec {
            bars: bars(&[Some(0), Some(4), Some(8)]),
            ..SparklineSpec::default()
        };
        assert_eq!(render(spec, 3), " ▄█");
    }

    #[test]
    fn a_maximum_changes_the_scale_and_direction_reverses_the_row() {
        let spec = SparklineSpec {
            bars: bars(&[Some(8), Some(0)]),
            maximum: Some(Dynamic::Fixed(16)),
            direction: Dynamic::Fixed("right_to_left".to_owned()),
            ..SparklineSpec::default()
        };
        assert_eq!(render(spec, 2), " ▄");
    }

    #[test]
    fn absent_values_use_their_own_symbol() {
        let spec = SparklineSpec {
            bars: bars(&[Some(8), None]),
            absent_value_symbol: Some(Dynamic::Fixed("?".to_owned())),
            ..SparklineSpec::default()
        };
        assert_eq!(render(spec, 2), "█?");
    }
}
