//! Arranging attached children inside their parent's content area.
//!
//! Only children attached with inherited geometry take part: they are the children whose
//! position and size the parent owns. Children attached with explicit geometry keep the
//! position and size they were given.

use ratatui_core::layout::{Constraint, Direction, Layout, Rect};

use crate::geometry::{Rectangle, Size};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Arrangement {
    Row,
    #[default]
    Column,
    Overlay,
}

impl Arrangement {
    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "row" => Self::Row,
            "column" => Self::Column,
            "overlay" => Self::Overlay,
            _ => return None,
        })
    }

    pub fn name(self) -> &'static str {
        match self {
            Self::Row => "row",
            Self::Column => "column",
            Self::Overlay => "overlay",
        }
    }
}

/// How much room one child takes along the arrangement's direction.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SizeRule {
    Cells(u16),
    Percent(u16),
    Fill(u16),
    /// The child's own size.
    Fit,
    Minimum(u16),
    Maximum(u16),
}

/// A retained arrangement rule for a buffer's inherited children.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct LayoutSpec {
    pub arrangement: Arrangement,
    pub sizes: Vec<SizeRule>,
    pub spacing: u16,
    pub padding: u16,
}

/// Where each child goes inside `area`. `intrinsic` holds each child's own size.
///
/// Children without a rule share the remaining room equally; a missing rule never means
/// a zero-sized child.
pub fn solve(spec: &LayoutSpec, area: Rectangle, intrinsic: &[Size]) -> Vec<Rectangle> {
    let content = area.inset(i32::from(spec.padding), i32::from(spec.padding));
    if intrinsic.is_empty() {
        return Vec::new();
    }
    if spec.arrangement == Arrangement::Overlay {
        return intrinsic.iter().map(|_| content).collect();
    }
    let direction = match spec.arrangement {
        Arrangement::Row => Direction::Horizontal,
        _ => Direction::Vertical,
    };
    let constraints: Vec<Constraint> = intrinsic
        .iter()
        .enumerate()
        .map(
            |(index, size)| match spec.sizes.get(index).copied().unwrap_or(SizeRule::Fill(1)) {
                SizeRule::Cells(count) => Constraint::Length(count),
                SizeRule::Percent(percentage) => Constraint::Percentage(percentage.min(100)),
                SizeRule::Fill(weight) => Constraint::Fill(weight.max(1)),
                SizeRule::Fit => {
                    let own = if direction == Direction::Horizontal {
                        size.width
                    } else {
                        size.height
                    };
                    Constraint::Length(own.clamp(0, i32::from(u16::MAX)) as u16)
                }
                SizeRule::Minimum(count) => Constraint::Min(count),
                SizeRule::Maximum(count) => Constraint::Max(count),
            },
        )
        .collect();
    let rects = Layout::default()
        .direction(direction)
        .constraints(constraints)
        .spacing(spec.spacing)
        .split(content.to_rect());
    let offset_x = content.x - i32::from(content.to_rect().x);
    let offset_y = content.y - i32::from(content.to_rect().y);
    rects
        .iter()
        .map(|rect: &Rect| {
            Rectangle::new(
                i32::from(rect.x) + offset_x,
                i32::from(rect.y) + offset_y,
                i32::from(rect.width),
                i32::from(rect.height),
            )
        })
        .collect()
}
