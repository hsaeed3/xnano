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
    let mut constraints: Vec<Constraint> = intrinsic
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
    // Fill-only layouts have known shares. Ratatui otherwise relates every pair of
    // fill segments, making a cold solve prohibitively expensive for large trees.
    let terminal_area = content.to_rect();
    let length = match direction {
        Direction::Horizontal => terminal_area.width,
        Direction::Vertical => terminal_area.height,
    };
    if let Some(ratios) = fill_ratios(&constraints, length, spec.spacing) {
        constraints = ratios;
    }
    let rects = Layout::default()
        .direction(direction)
        .constraints(constraints)
        .spacing(spec.spacing)
        .split(terminal_area);
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

fn fill_ratios(constraints: &[Constraint], length: u16, spacing: u16) -> Option<Vec<Constraint>> {
    // Ratatui stores solver spacing as a signed 16-bit value.
    if spacing > i16::MAX as u16 {
        return None;
    }
    let weights: Vec<u32> = constraints
        .iter()
        .map(|constraint| match constraint {
            Constraint::Fill(weight) => Some(u32::from(*weight)),
            _ => None,
        })
        .collect::<Option<_>>()?;
    let total_weight = weights
        .iter()
        .try_fold(0u32, |total, weight| total.checked_add(*weight))?;
    let gap_count = u32::try_from(weights.len().saturating_sub(1)).ok()?;
    let available = u32::from(length).saturating_sub(gap_count.checked_mul(u32::from(spacing))?);
    if available == 0 {
        return Some(vec![Constraint::Length(0); weights.len()]);
    }
    // With spacing, ratios still refer to the whole area, so include the space
    // remaining after the gaps in each numerator. Keep overflow on the general path.
    if spacing == 0 {
        return Some(
            weights
                .into_iter()
                .map(|weight| Constraint::Ratio(weight, total_weight))
                .collect(),
        );
    }
    let denominator = total_weight.checked_mul(u32::from(length))?;
    weights
        .into_iter()
        .map(|weight| {
            Some(Constraint::Ratio(
                weight.checked_mul(available)?,
                denominator,
            ))
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fill_ratios_preserve_upstream_geometry() {
        for direction in [Direction::Horizontal, Direction::Vertical] {
            for count in 1..=12 {
                for length in [0, 1, 7, 40, 121] {
                    for spacing in [0, 1, 3] {
                        for has_weights in [false, true] {
                            let constraints: Vec<_> = (0..count)
                                .map(|index| {
                                    Constraint::Fill(if has_weights { index % 3 + 1 } else { 1 })
                                })
                                .collect();
                            let Some(ratios) = fill_ratios(&constraints, length, spacing) else {
                                continue;
                            };
                            let area = match direction {
                                Direction::Horizontal => Rect::new(3, 5, length, 10),
                                Direction::Vertical => Rect::new(3, 5, 10, length),
                            };
                            let upstream = Layout::default()
                                .direction(direction)
                                .constraints(&constraints)
                                .spacing(spacing)
                                .split(area);
                            let optimized = Layout::default()
                                .direction(direction)
                                .constraints(ratios)
                                .spacing(spacing)
                                .split(area);
                            assert_eq!(
                                optimized, upstream,
                                "{direction:?}, {constraints:?}, {length}, {spacing}"
                            );
                        }
                    }
                }
            }
        }
    }

    #[test]
    fn large_fill_layouts_cover_the_available_space() {
        for count in [40, 50, 100] {
            for arrangement in [Arrangement::Row, Arrangement::Column] {
                let spec = LayoutSpec {
                    arrangement,
                    ..LayoutSpec::default()
                };
                let rectangles = solve(
                    &spec,
                    Rectangle::new(0, 0, 120, 40),
                    &vec![Size::new(1, 1); count],
                );
                assert_eq!(rectangles.len(), count);
                let length: i32 = rectangles
                    .iter()
                    .map(|rectangle| match arrangement {
                        Arrangement::Row => rectangle.width,
                        _ => rectangle.height,
                    })
                    .sum();
                assert_eq!(
                    length,
                    if arrangement == Arrangement::Row {
                        120
                    } else {
                        40
                    }
                );
            }
        }
    }
}
