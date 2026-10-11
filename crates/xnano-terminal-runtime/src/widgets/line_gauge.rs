//! The ratatui `LineGauge`: a one-line progress bar drawn with line symbols.
//!
//! Maps to `ratatui::widgets::LineGauge`.

use ratatui::symbols::line;
use ratatui::widgets::LineGauge;
use ratatui_core::layout::Rect;
use ratatui_core::style::Style;
use ratatui_core::widgets::Widget;

use crate::dynamic::Dynamic;
use crate::expression::EvalError;
use crate::grid::Grid;
use crate::widgets::block::{BlockSpec, ResolvedBlock, resolve_optional};
use crate::widgets::style::StyleSpec;
use crate::widgets::{Resolver, Shared, WidgetSpec};

/// The line symbol sets a line gauge can draw with.
pub const LINE_SETS: [(&str, line::Set<'static>); 3] = [
    ("normal", line::NORMAL),
    ("thick", line::THICK),
    ("double", line::DOUBLE),
];

/// The line symbol set called `name`, if there is one.
pub fn line_set_from_name(name: &str) -> Option<line::Set<'static>> {
    LINE_SETS
        .iter()
        .find(|(candidate, _)| *candidate == name)
        .map(|(_, set)| *set)
}

/// The names of the line symbol sets, for error messages.
pub fn line_set_names() -> String {
    LINE_SETS
        .iter()
        .map(|(name, _)| format!("\"{name}\""))
        .collect::<Vec<_>>()
        .join(", ")
}

#[derive(Debug, Clone)]
pub struct LineGaugeSpec {
    /// The filled fraction, from 0.0 to 1.0.
    pub ratio: Dynamic<f64>,
    pub label: Option<Dynamic<String>>,
    pub line_set: Dynamic<String>,
    /// Replaces the filled part's symbol when set; otherwise the line set's horizontal line.
    pub filled_symbol: Option<Dynamic<String>>,
    /// Replaces the unfilled part's symbol when set.
    pub unfilled_symbol: Option<Dynamic<String>>,
    pub style: StyleSpec,
    pub filled_style: StyleSpec,
    pub unfilled_style: StyleSpec,
    pub block: Option<Shared<BlockSpec>>,
}

impl LineGaugeSpec {
    pub fn new(ratio: Dynamic<f64>) -> Self {
        Self {
            ratio,
            label: None,
            line_set: Dynamic::Fixed("normal".to_owned()),
            filled_symbol: None,
            unfilled_symbol: None,
            style: StyleSpec::default(),
            filled_style: StyleSpec::default(),
            unfilled_style: StyleSpec::default(),
            block: None,
        }
    }
}

#[derive(Debug)]
pub struct ResolvedLineGauge {
    ratio: f64,
    label: Option<String>,
    line_set: line::Set<'static>,
    filled_symbol: Option<String>,
    unfilled_symbol: Option<String>,
    style: Style,
    filled_style: Style,
    unfilled_style: Style,
    block: Option<ResolvedBlock>,
}

impl WidgetSpec for LineGaugeSpec {
    type Resolved = ResolvedLineGauge;

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Self::Resolved, EvalError> {
        let ratio = resolver.get(&self.ratio)?;
        if !ratio.is_finite() {
            return Err(EvalError::Type(format!(
                "a line gauge ratio must be a number from 0.0 to 1.0, not {ratio}"
            )));
        }
        let set_name = resolver.get(&self.line_set)?;
        let line_set = line_set_from_name(&set_name).ok_or_else(|| {
            EvalError::Type(format!(
                "\"{set_name}\" is not a line set; use one of {}",
                line_set_names()
            ))
        })?;
        Ok(ResolvedLineGauge {
            ratio: ratio.clamp(0.0, 1.0),
            label: resolver.get_optional(&self.label)?,
            line_set,
            filled_symbol: resolver.get_optional(&self.filled_symbol)?,
            unfilled_symbol: resolver.get_optional(&self.unfilled_symbol)?,
            style: self.style.resolve(resolver)?,
            filled_style: self.filled_style.resolve(resolver)?,
            unfilled_style: self.unfilled_style.resolve(resolver)?,
            block: resolve_optional(&self.block, resolver)?,
        })
    }

    fn draw(resolved: &Self::Resolved, grid: &mut Grid) {
        let mut gauge = LineGauge::default()
            .ratio(resolved.ratio)
            .filled_symbol(resolved.line_set.horizontal)
            .unfilled_symbol(resolved.line_set.horizontal)
            .style(resolved.style)
            .filled_style(resolved.filled_style)
            .unfilled_style(resolved.unfilled_style);
        if let Some(symbol) = &resolved.filled_symbol {
            gauge = gauge.filled_symbol(symbol);
        }
        if let Some(symbol) = &resolved.unfilled_symbol {
            gauge = gauge.unfilled_symbol(symbol);
        }
        if let Some(label) = &resolved.label {
            gauge = gauge.label(label.clone());
        }
        if let Some(block) = &resolved.block {
            gauge = gauge.block(block.to_widget());
        }
        let area = Rect::new(0, 0, grid.width(), grid.height());
        gauge.render(area, grid.buffer_mut());
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

    fn render(spec: LineGaugeSpec, width: u16) -> String {
        let painter = SpecPainter::new(Spec::new(spec));
        let mut grid = Grid::filled(width, 1, &crate::grid::blank_cell());
        painter.fingerprint(&Offline).expect("resolves");
        painter.paint(&mut grid, &Offline).expect("paints");
        grid.text_rows().join("")
    }

    #[test]
    fn the_filled_part_follows_the_ratio() {
        let mut spec = LineGaugeSpec::new(Dynamic::Fixed(0.5));
        spec.label = Some(Dynamic::Fixed("ab".to_owned()));
        spec.filled_symbol = Some(Dynamic::Fixed("#".to_owned()));
        spec.unfilled_symbol = Some(Dynamic::Fixed("-".to_owned()));
        assert_eq!(render(spec, 12), "ab ####-----");
    }

    #[test]
    fn an_unknown_line_set_names_the_choices() {
        let mut spec = LineGaugeSpec::new(Dynamic::Fixed(0.5));
        spec.line_set = Dynamic::Fixed("wavy".to_owned());
        let painter = SpecPainter::new(Spec::new(spec));
        let error = painter.fingerprint(&Offline).expect_err("rejects");
        assert!(error.to_string().contains("\"normal\""));
    }
}
