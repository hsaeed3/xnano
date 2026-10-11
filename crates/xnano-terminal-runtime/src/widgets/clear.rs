//! The ratatui `Clear`: blank cells that hide whatever is behind them.
//!
//! Maps to `ratatui::widgets::Clear`.

use ratatui_core::buffer::Cell;
use ratatui_core::style::Style;

use crate::dynamic::Dynamic;
use crate::expression::EvalError;
use crate::grid::Grid;
use crate::widgets::style::StyleSpec;
use crate::widgets::{Resolver, WidgetSpec};

#[derive(Debug, Clone)]
pub struct ClearSpec {
    /// The symbol every cell shows, a space by default.
    pub symbol: Dynamic<String>,
    pub style: StyleSpec,
}

impl Default for ClearSpec {
    fn default() -> Self {
        Self {
            symbol: Dynamic::Fixed(" ".to_owned()),
            style: StyleSpec::default(),
        }
    }
}

#[derive(Debug)]
pub struct ResolvedClear {
    symbol: String,
    style: Style,
}

impl WidgetSpec for ClearSpec {
    type Resolved = ResolvedClear;

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Self::Resolved, EvalError> {
        let symbol = resolver.get(&self.symbol)?;
        if crate::text::display_width(&symbol) != 1 {
            return Err(EvalError::Type(format!(
                "a clear symbol must be a single character one column wide, not \"{symbol}\"; \
                 use a space or a glyph such as \"·\""
            )));
        }
        Ok(ResolvedClear {
            symbol,
            style: self.style.resolve(resolver)?,
        })
    }

    fn draw(resolved: &Self::Resolved, grid: &mut Grid) {
        let mut cell = Cell::default();
        cell.set_symbol(&resolved.symbol);
        cell.set_style(resolved.style);
        let bounds = grid.bounds();
        grid.fill(bounds, &cell, false);
    }
}
