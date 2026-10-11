//! Integer geometry shared by buffers, drawing, layout and input.
//!
//! Positions may be negative (a buffer can sit partly off its parent); sizes are never
//! negative and are limited to what a terminal can show.

use ratatui_core::layout::Rect;

/// The largest width or height of a buffer, in cells.
pub const MAXIMUM_DIMENSION: i32 = u16::MAX as i32;

fn dimension_between(start: i32, end: i32) -> i32 {
    (i64::from(end) - i64::from(start)).clamp(0, i64::from(i32::MAX)) as i32
}

/// A column and row.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
pub struct Point {
    pub x: i32,
    pub y: i32,
}

impl Point {
    pub const fn new(x: i32, y: i32) -> Self {
        Self { x, y }
    }
}

/// A width and height.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
pub struct Size {
    pub width: i32,
    pub height: i32,
}

impl Size {
    pub const fn new(width: i32, height: i32) -> Self {
        Self { width, height }
    }
}

/// Half-open bounds: left and top are inside, right and bottom are outside.
#[must_use]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
pub struct Rectangle {
    pub x: i32,
    pub y: i32,
    pub width: i32,
    pub height: i32,
}

impl Rectangle {
    pub const fn new(x: i32, y: i32, width: i32, height: i32) -> Self {
        Self {
            x,
            y,
            width,
            height,
        }
    }

    pub const fn right(self) -> i32 {
        self.x.saturating_add(self.width)
    }

    pub const fn bottom(self) -> i32 {
        self.y.saturating_add(self.height)
    }

    pub const fn is_empty(self) -> bool {
        self.width <= 0 || self.height <= 0
    }

    pub fn area(self) -> i64 {
        i64::from(self.width.max(0)) * i64::from(self.height.max(0))
    }

    pub fn position(self) -> Point {
        Point::new(self.x, self.y)
    }

    pub fn size(self) -> Size {
        Size::new(self.width, self.height)
    }

    pub fn contains(self, point: Point) -> bool {
        point.x >= self.x && point.x < self.right() && point.y >= self.y && point.y < self.bottom()
    }

    pub fn intersects(self, other: Self) -> bool {
        !self.intersection(other).is_empty()
    }

    /// The overlap, or an empty rectangle at this rectangle's corner.
    pub fn intersection(self, other: Self) -> Self {
        let left = self.x.max(other.x);
        let top = self.y.max(other.y);
        let right = self.right().min(other.right());
        let bottom = self.bottom().min(other.bottom());
        if right <= left || bottom <= top {
            return Self::new(self.x, self.y, 0, 0);
        }
        Self::new(
            left,
            top,
            dimension_between(left, right),
            dimension_between(top, bottom),
        )
    }

    /// The smallest rectangle holding both; an empty rectangle contributes nothing.
    pub fn union(self, other: Self) -> Self {
        if self.is_empty() {
            return other;
        }
        if other.is_empty() {
            return self;
        }
        let left = self.x.min(other.x);
        let top = self.y.min(other.y);
        let right = self.right().max(other.right());
        let bottom = self.bottom().max(other.bottom());
        Self::new(
            left,
            top,
            dimension_between(left, right),
            dimension_between(top, bottom),
        )
    }

    pub fn translate(self, horizontal: i32, vertical: i32) -> Self {
        Self::new(
            self.x.saturating_add(horizontal),
            self.y.saturating_add(vertical),
            self.width,
            self.height,
        )
    }

    /// Shrink by `horizontal` columns and `vertical` rows on every side (grow when negative).
    pub fn inset(self, horizontal: i32, vertical: i32) -> Self {
        let width = (i64::from(self.width) - 2 * i64::from(horizontal))
            .clamp(0, i64::from(i32::MAX)) as i32;
        let height =
            (i64::from(self.height) - 2 * i64::from(vertical)).clamp(0, i64::from(i32::MAX)) as i32;
        if width == 0 || height == 0 {
            return Self::new(
                self.x.saturating_add(horizontal.min(self.width.max(0) / 2)),
                self.y.saturating_add(vertical.min(self.height.max(0) / 2)),
                0,
                0,
            );
        }
        Self::new(
            self.x.saturating_add(horizontal),
            self.y.saturating_add(vertical),
            width,
            height,
        )
    }

    /// Convert to a terminal rectangle, clipping to the area that can be addressed.
    pub fn to_rect(self) -> Rect {
        let clipped = self.intersection(Self::new(0, 0, MAXIMUM_DIMENSION, MAXIMUM_DIMENSION));
        Rect::new(
            clipped.x.max(0) as u16,
            clipped.y.max(0) as u16,
            clipped.width.max(0) as u16,
            clipped.height.max(0) as u16,
        )
    }
}

impl From<Rect> for Rectangle {
    fn from(rect: Rect) -> Self {
        Self::new(
            i32::from(rect.x),
            i32::from(rect.y),
            i32::from(rect.width),
            i32::from(rect.height),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::Rectangle;

    #[test]
    fn union_saturates_spans_that_exceed_the_coordinate_range() {
        let left = Rectangle::new(i32::MIN, 0, i32::MAX, 1);
        let right = Rectangle::new(0, 0, i32::MAX, 1);

        let union = left.union(right);

        assert_eq!(union.x, i32::MIN);
        assert_eq!(union.width, i32::MAX);
    }

    #[test]
    fn inset_saturates_extreme_margins_without_overflowing() {
        let rectangle = Rectangle::new(i32::MAX - 1, i32::MIN + 1, 10, 10);

        let inset = rectangle.inset(i32::MIN, i32::MIN);

        assert_eq!(inset.width, i32::MAX);
        assert_eq!(inset.height, i32::MAX);
        assert_eq!(inset.x, -2);
        assert_eq!(inset.y, i32::MIN);
    }
}
