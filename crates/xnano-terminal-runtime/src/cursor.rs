//! The terminal's cursor: where it is, what it looks like and whether it is shown.

use crate::geometry::Point;

/// What a cursor looks like.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum CursorShape {
    #[default]
    Block,
    Bar,
    Underline,
}

impl CursorShape {
    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "block" => Self::Block,
            "bar" => Self::Bar,
            "underline" => Self::Underline,
            _ => return None,
        })
    }

    pub fn name(self) -> &'static str {
        match self {
            Self::Block => "block",
            Self::Bar => "bar",
            Self::Underline => "underline",
        }
    }
}

/// Where a frame shows the cursor, and how.
///
/// `style` is `None` while the user's own cursor shape is left alone.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CursorPlacement {
    pub position: Point,
    pub style: Option<(CursorShape, bool)>,
}
