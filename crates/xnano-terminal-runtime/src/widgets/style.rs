//! Styles whose colors can follow expressions.

use ratatui_core::style::{Color, Modifier, Style};

use crate::dynamic::Dynamic;
use crate::expression::EvalError;
use crate::widgets::Resolver;

/// A style with colors that are fixed or bound to expressions.
#[derive(Debug, Clone, Default)]
pub struct StyleSpec {
    pub foreground: Option<Dynamic<Color>>,
    pub background: Option<Dynamic<Color>>,
    pub underline_color: Option<Dynamic<Color>>,
    pub add_modifier: Modifier,
    pub remove_modifier: Modifier,
}

impl StyleSpec {
    /// Whether no color follows an expression.
    pub fn is_static(&self) -> bool {
        [&self.foreground, &self.background, &self.underline_color]
            .into_iter()
            .all(|color| !color.as_ref().is_some_and(Dynamic::is_bound))
    }

    /// A style with nothing bound.
    pub fn fixed(style: Style) -> Self {
        Self {
            foreground: style.fg.map(Dynamic::Fixed),
            background: style.bg.map(Dynamic::Fixed),
            underline_color: style.underline_color.map(Dynamic::Fixed),
            add_modifier: style.add_modifier,
            remove_modifier: style.sub_modifier,
        }
    }

    /// The style with every bound color read.
    pub fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Style, EvalError> {
        let mut style = Style::default()
            .add_modifier(self.add_modifier)
            .remove_modifier(self.remove_modifier);
        if let Some(color) = resolver.get_optional(&self.foreground)? {
            style = style.fg(color);
        }
        if let Some(color) = resolver.get_optional(&self.background)? {
            style = style.bg(color);
        }
        if let Some(color) = resolver.get_optional(&self.underline_color)? {
            style = style.underline_color(color);
        }
        Ok(style)
    }
}
