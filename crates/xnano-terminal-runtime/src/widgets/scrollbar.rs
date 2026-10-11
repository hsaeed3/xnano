//! The ratatui `Scrollbar`: a track with a thumb showing a scroll position.
//!
//! Maps to `ratatui::widgets::Scrollbar` and `ScrollbarState`.

use ratatui::symbols::scrollbar::{self, Set};
use ratatui::widgets::{Scrollbar, ScrollbarOrientation, ScrollbarState};
use ratatui_core::layout::Rect;
use ratatui_core::style::Style;
use ratatui_core::widgets::StatefulWidget;

use crate::dynamic::Dynamic;
use crate::expression::EvalError;
use crate::grid::{Grid, blank_cell};
use crate::widgets::style::StyleSpec;
use crate::widgets::{Resolver, WidgetSpec};

/// Where the scrollbar sits inside its area.
pub const ORIENTATIONS: [(&str, ScrollbarOrientation); 4] = [
    ("vertical_right", ScrollbarOrientation::VerticalRight),
    ("vertical_left", ScrollbarOrientation::VerticalLeft),
    ("horizontal_bottom", ScrollbarOrientation::HorizontalBottom),
    ("horizontal_top", ScrollbarOrientation::HorizontalTop),
];

/// The symbol presets, by name.
pub const SYMBOL_PRESETS: [(&str, Set<'static>); 4] = [
    ("double_vertical", scrollbar::DOUBLE_VERTICAL),
    ("double_horizontal", scrollbar::DOUBLE_HORIZONTAL),
    ("vertical", scrollbar::VERTICAL),
    ("horizontal", scrollbar::HORIZONTAL),
];

pub fn orientation_from_name(name: &str) -> Option<ScrollbarOrientation> {
    ORIENTATIONS
        .iter()
        .find(|(candidate, _)| *candidate == name)
        .map(|(_, orientation)| orientation.clone())
}

/// The names of the orientations, for error messages.
pub fn orientation_names() -> String {
    ORIENTATIONS
        .iter()
        .map(|(name, _)| format!("\"{name}\""))
        .collect::<Vec<_>>()
        .join(", ")
}

pub fn symbol_preset_from_name(name: &str) -> Option<Set<'static>> {
    SYMBOL_PRESETS
        .iter()
        .find(|(candidate, _)| *candidate == name)
        .map(|(_, set)| set.clone())
}

/// The names of the symbol presets, for error messages.
pub fn symbol_preset_names() -> String {
    SYMBOL_PRESETS
        .iter()
        .map(|(name, _)| format!("\"{name}\""))
        .collect::<Vec<_>>()
        .join(", ")
}

/// The preset a symbol selection matches exactly, if any.
pub fn matching_preset(
    thumb: &str,
    track: Option<&str>,
    begin: Option<&str>,
    end: Option<&str>,
) -> Option<&'static str> {
    SYMBOL_PRESETS
        .iter()
        .find(|(_, set)| {
            set.thumb == thumb
                && track == Some(set.track)
                && begin == Some(set.begin)
                && end == Some(set.end)
        })
        .map(|(name, _)| *name)
}

#[derive(Debug, Clone)]
pub struct ScrollbarSpec {
    /// One of [`ORIENTATIONS`].
    pub orientation: Dynamic<String>,
    /// The total number of scrollable items; zero draws nothing.
    pub content_length: Dynamic<usize>,
    /// The index of the first visible item.
    pub position: Dynamic<usize>,
    /// How many items fit in view; `None` uses the track length.
    pub viewport_content_length: Option<Dynamic<usize>>,
    pub thumb_symbol: Dynamic<String>,
    /// `None` hides the track.
    pub track_symbol: Option<Dynamic<String>>,
    /// `None` hides the begin arrow.
    pub begin_symbol: Option<Dynamic<String>>,
    /// `None` hides the end arrow.
    pub end_symbol: Option<Dynamic<String>>,
    /// Applies to every part; the part styles below are layered over it.
    pub style: StyleSpec,
    pub thumb_style: StyleSpec,
    pub track_style: StyleSpec,
    pub begin_style: StyleSpec,
    pub end_style: StyleSpec,
    /// Whether cells the scrollbar does not draw let the buffer below show through.
    pub is_transparent: Dynamic<bool>,
}

impl ScrollbarSpec {
    pub fn new(orientation: &str) -> Self {
        let set = default_symbols(orientation);
        Self {
            orientation: Dynamic::Fixed(orientation.to_owned()),
            content_length: Dynamic::Fixed(0),
            position: Dynamic::Fixed(0),
            viewport_content_length: None,
            thumb_symbol: Dynamic::Fixed(set.thumb.to_owned()),
            track_symbol: Some(Dynamic::Fixed(set.track.to_owned())),
            begin_symbol: Some(Dynamic::Fixed(set.begin.to_owned())),
            end_symbol: Some(Dynamic::Fixed(set.end.to_owned())),
            style: StyleSpec::default(),
            thumb_style: StyleSpec::default(),
            track_style: StyleSpec::default(),
            begin_style: StyleSpec::default(),
            end_style: StyleSpec::default(),
            is_transparent: Dynamic::Fixed(true),
        }
    }
}

/// The symbols a scrollbar of this orientation starts with.
pub fn default_symbols(orientation: &str) -> Set<'static> {
    if orientation.starts_with("vertical") {
        scrollbar::DOUBLE_VERTICAL
    } else {
        scrollbar::DOUBLE_HORIZONTAL
    }
}

#[derive(Debug)]
pub struct ResolvedScrollbar {
    orientation: ScrollbarOrientation,
    content_length: usize,
    position: usize,
    viewport_content_length: Option<usize>,
    thumb_symbol: String,
    track_symbol: Option<String>,
    begin_symbol: Option<String>,
    end_symbol: Option<String>,
    thumb_style: Style,
    track_style: Style,
    begin_style: Style,
    end_style: Style,
    is_transparent: bool,
}

impl WidgetSpec for ScrollbarSpec {
    type Resolved = ResolvedScrollbar;

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Self::Resolved, EvalError> {
        let orientation_name = resolver.get(&self.orientation)?;
        let orientation = orientation_from_name(&orientation_name).ok_or_else(|| {
            EvalError::Type(format!(
                "\"{orientation_name}\" is not a scrollbar orientation; use one of {}",
                orientation_names()
            ))
        })?;
        let base = self.style.resolve(resolver)?;
        let part = |spec: &StyleSpec, resolver: &mut Resolver<'_>| -> Result<Style, EvalError> {
            Ok(base.patch(spec.resolve(resolver)?))
        };
        Ok(ResolvedScrollbar {
            orientation,
            content_length: resolver.get(&self.content_length)?,
            position: resolver.get(&self.position)?,
            viewport_content_length: resolver.get_optional(&self.viewport_content_length)?,
            thumb_symbol: resolver.get(&self.thumb_symbol)?,
            track_symbol: resolver.get_optional(&self.track_symbol)?,
            begin_symbol: resolver.get_optional(&self.begin_symbol)?,
            end_symbol: resolver.get_optional(&self.end_symbol)?,
            thumb_style: part(&self.thumb_style, resolver)?,
            track_style: part(&self.track_style, resolver)?,
            begin_style: part(&self.begin_style, resolver)?,
            end_style: part(&self.end_style, resolver)?,
            is_transparent: resolver.get(&self.is_transparent)?,
        })
    }

    fn draw(resolved: &Self::Resolved, grid: &mut Grid) {
        let scrollbar = Scrollbar::new(resolved.orientation.clone())
            .thumb_symbol(&resolved.thumb_symbol)
            .track_symbol(resolved.track_symbol.as_deref())
            .begin_symbol(resolved.begin_symbol.as_deref())
            .end_symbol(resolved.end_symbol.as_deref())
            .thumb_style(resolved.thumb_style)
            .track_style(resolved.track_style)
            .begin_style(resolved.begin_style)
            .end_style(resolved.end_style);
        let mut state = ScrollbarState::new(resolved.content_length).position(resolved.position);
        if let Some(viewport) = resolved.viewport_content_length {
            state = state.viewport_content_length(viewport);
        }
        let area = Rect::new(0, 0, grid.width(), grid.height());
        if resolved.is_transparent {
            grid.mark_all_transparent();
        }
        scrollbar.render(area, grid.buffer_mut(), &mut state);
        if resolved.is_transparent {
            // Cells the scrollbar wrote become opaque; the rest stays see-through.
            let blank = blank_cell();
            for y in 0..grid.height() {
                for x in 0..grid.width() {
                    if let Some(cell) = grid.cell(x, y).cloned()
                        && cell != blank
                    {
                        grid.put(x, y, cell, 1, false);
                    }
                }
            }
        }
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

    fn render(spec: ScrollbarSpec, width: u16, height: u16) -> Grid {
        let painter = SpecPainter::new(Spec::new(spec));
        let mut grid = Grid::filled(width, height, &blank_cell());
        painter.fingerprint(&Offline).expect("resolves");
        painter.paint(&mut grid, &Offline).expect("paints");
        grid
    }

    #[test]
    fn the_thumb_moves_with_the_position() {
        let mut spec = ScrollbarSpec::new("vertical_right");
        spec.content_length = Dynamic::Fixed(10);
        spec.begin_symbol = None;
        spec.end_symbol = None;
        let top = render(spec.clone(), 1, 6).text_rows().join("");
        spec.position = Dynamic::Fixed(9);
        let bottom = render(spec, 1, 6).text_rows().join("");
        assert!(top.starts_with('█') && bottom.ends_with('█'));
        assert_ne!(top, bottom);
    }

    #[test]
    fn unwritten_cells_stay_transparent_and_written_cells_are_opaque() {
        let mut spec = ScrollbarSpec::new("vertical_right");
        spec.content_length = Dynamic::Fixed(4);
        let grid = render(spec, 3, 4);
        assert!(grid.is_transparent(0, 1));
        assert!(!grid.is_transparent(2, 1));
    }

    #[test]
    fn matching_preset_recognizes_the_defaults() {
        let set = default_symbols("horizontal_top");
        assert_eq!(
            matching_preset(set.thumb, Some(set.track), Some(set.begin), Some(set.end)),
            Some("double_horizontal")
        );
    }
}
