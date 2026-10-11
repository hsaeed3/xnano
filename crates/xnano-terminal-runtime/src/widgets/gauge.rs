//! The ratatui `Gauge`: a filled bar with a percentage or label.
//!
//! Maps to `ratatui::widgets::Gauge`.

use ratatui::widgets::Gauge;
use ratatui_core::layout::Rect;
use ratatui_core::style::Style;
use ratatui_core::widgets::Widget;

use crate::dynamic::Dynamic;
use crate::expression::EvalError;
use crate::grid::Grid;
use crate::widgets::block::{BlockSpec, ResolvedBlock, resolve_optional};
use crate::widgets::style::StyleSpec;
use crate::widgets::{Resolver, Shared, WidgetSpec};

#[derive(Debug, Clone)]
pub struct GaugeSpec {
    /// The filled fraction, from 0.0 to 1.0.
    pub ratio: Dynamic<f64>,
    pub label: Option<Dynamic<String>>,
    pub style: StyleSpec,
    pub gauge_style: StyleSpec,
    pub use_unicode: Dynamic<bool>,
    pub block: Option<Shared<BlockSpec>>,
}

impl GaugeSpec {
    pub fn new(ratio: Dynamic<f64>) -> Self {
        Self {
            ratio,
            label: None,
            style: StyleSpec::default(),
            gauge_style: StyleSpec::default(),
            use_unicode: Dynamic::Fixed(true),
            block: None,
        }
    }
}

#[derive(Debug)]
pub struct ResolvedGauge {
    ratio: f64,
    label: Option<String>,
    style: Style,
    gauge_style: Style,
    use_unicode: bool,
    block: Option<ResolvedBlock>,
}

impl WidgetSpec for GaugeSpec {
    type Resolved = ResolvedGauge;

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Self::Resolved, EvalError> {
        let ratio = resolver.get(&self.ratio)?;
        if !ratio.is_finite() {
            return Err(EvalError::Type(format!(
                "a gauge ratio must be a number from 0.0 to 1.0, not {ratio}"
            )));
        }
        Ok(ResolvedGauge {
            ratio: ratio.clamp(0.0, 1.0),
            label: resolver.get_optional(&self.label)?,
            style: self.style.resolve(resolver)?,
            gauge_style: self.gauge_style.resolve(resolver)?,
            use_unicode: resolver.get(&self.use_unicode)?,
            block: resolve_optional(&self.block, resolver)?,
        })
    }

    fn draw(resolved: &Self::Resolved, grid: &mut Grid) {
        let mut gauge = Gauge::default()
            .ratio(resolved.ratio)
            .use_unicode(resolved.use_unicode)
            .style(resolved.style)
            .gauge_style(resolved.gauge_style);
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
