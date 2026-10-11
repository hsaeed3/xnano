//! The ratatui `Canvas`: shapes, points and labels drawn on a coordinate plane.
//!
//! Maps to `ratatui::widgets::canvas::Canvas`.

use ratatui::widgets::canvas::{
    Canvas, Circle, FilledLine, Line, Map, MapResolution, Points, Rectangle,
};
use ratatui_core::layout::Rect;
use ratatui_core::style::{Color, Style};
use ratatui_core::symbols::Marker;
use ratatui_core::text::Line as TextLine;
use ratatui_core::widgets::Widget;

use crate::dynamic::Dynamic;
use crate::expression::EvalError;
use crate::grid::Grid;
use crate::widgets::block::{BlockSpec, ResolvedBlock, resolve_optional};
use crate::widgets::style::StyleSpec;
use crate::widgets::{Resolver, Shared, WidgetSpec};

/// The marker names accepted for canvases and chart datasets.
pub const MARKER_NAMES: [&str; 8] = [
    "dot",
    "block",
    "bar",
    "braille",
    "half_block",
    "quadrant",
    "sextant",
    "octant",
];

/// The marker called `name`, or a custom marker for any single character.
pub fn marker_from_name(name: &str) -> Option<Marker> {
    Some(match name {
        "dot" => Marker::Dot,
        "block" => Marker::Block,
        "bar" => Marker::Bar,
        "braille" => Marker::Braille,
        "half_block" => Marker::HalfBlock,
        "quadrant" => Marker::Quadrant,
        "sextant" => Marker::Sextant,
        "octant" => Marker::Octant,
        other => {
            let mut characters = other.chars();
            match (characters.next(), characters.next()) {
                (Some(character), None) => Marker::Custom(character),
                _ => return None,
            }
        }
    })
}

/// Explain which marker names exist.
pub fn marker_error(name: &str) -> String {
    format!(
        "\"{name}\" is not a marker; use one of {} or a single character",
        MARKER_NAMES.join(", ")
    )
}

fn resolve_marker(
    resolver: &mut Resolver<'_>,
    value: &Dynamic<String>,
) -> Result<Marker, EvalError> {
    let name = resolver.get(value)?;
    marker_from_name(&name).ok_or_else(|| EvalError::Type(marker_error(&name)))
}

/// A straight line, optionally filled down to a baseline.
#[derive(Debug, Clone)]
pub struct LineShape {
    pub x1: Dynamic<f64>,
    pub y1: Dynamic<f64>,
    pub x2: Dynamic<f64>,
    pub y2: Dynamic<f64>,
    pub color: Dynamic<Color>,
    /// When set, the area between the line and this `y` is filled.
    pub fill_to_y: Option<Dynamic<f64>>,
}

/// An axis-aligned rectangle outline.
#[derive(Debug, Clone)]
pub struct RectangleShape {
    pub x: Dynamic<f64>,
    pub y: Dynamic<f64>,
    pub width: Dynamic<f64>,
    pub height: Dynamic<f64>,
    pub color: Dynamic<Color>,
}

/// A circle outline.
#[derive(Debug, Clone)]
pub struct CircleShape {
    pub x: Dynamic<f64>,
    pub y: Dynamic<f64>,
    pub radius: Dynamic<f64>,
    pub color: Dynamic<Color>,
}

/// A set of single points.
#[derive(Debug, Clone)]
pub struct PointsShape {
    pub coordinates: Vec<(f64, f64)>,
    pub color: Dynamic<Color>,
}

/// The world map.
#[derive(Debug, Clone)]
pub struct MapShape {
    /// `"low"` or `"high"`.
    pub resolution: Dynamic<String>,
    pub color: Dynamic<Color>,
}

/// Text printed on top of the canvas.
#[derive(Debug, Clone)]
pub struct LabelShape {
    pub x: Dynamic<f64>,
    pub y: Dynamic<f64>,
    pub text: Dynamic<String>,
    pub style: StyleSpec,
}

/// Switches the marker used by the shapes that follow it.
#[derive(Debug, Clone)]
pub struct MarkerShape {
    pub marker: Dynamic<String>,
}

/// A shape in a canvas, sharing its settings with the object that edits them.
#[derive(Debug, Clone)]
pub enum ShapeHandle {
    Line(Shared<LineShape>),
    Rectangle(Shared<RectangleShape>),
    Circle(Shared<CircleShape>),
    Points(Shared<PointsShape>),
    Map(Shared<MapShape>),
    Label(Shared<LabelShape>),
    /// Saves what was drawn so far as a layer; later shapes draw on top of it.
    Layer,
    Marker(Shared<MarkerShape>),
}

#[derive(Debug, Clone)]
enum ResolvedShape {
    Line([f64; 4], Color, Option<f64>),
    Rectangle([f64; 4], Color),
    Circle([f64; 3], Color),
    Points(Vec<(f64, f64)>, Color),
    Map(MapResolution, Color),
    Label(f64, f64, String, Style),
    Layer,
    Marker(Marker),
}

/// The settings of a canvas.
#[derive(Debug, Clone)]
pub struct CanvasSpec {
    pub x_bounds: [Dynamic<f64>; 2],
    pub y_bounds: [Dynamic<f64>; 2],
    pub marker: Dynamic<String>,
    pub background_color: Option<Dynamic<Color>>,
    pub shapes: Vec<ShapeHandle>,
    pub block: Option<Shared<BlockSpec>>,
}

impl Default for CanvasSpec {
    fn default() -> Self {
        Self {
            x_bounds: [Dynamic::Fixed(0.0), Dynamic::Fixed(1.0)],
            y_bounds: [Dynamic::Fixed(0.0), Dynamic::Fixed(1.0)],
            marker: Dynamic::Fixed("braille".to_owned()),
            background_color: None,
            shapes: Vec::new(),
            block: None,
        }
    }
}

#[derive(Debug)]
pub struct ResolvedCanvas {
    x_bounds: [f64; 2],
    y_bounds: [f64; 2],
    marker: Marker,
    background_color: Color,
    shapes: Vec<ResolvedShape>,
    block: Option<ResolvedBlock>,
}

fn resolve_map_resolution(name: &str) -> Result<MapResolution, EvalError> {
    match name {
        "low" => Ok(MapResolution::Low),
        "high" => Ok(MapResolution::High),
        other => Err(EvalError::Type(format!(
            "\"{other}\" is not a map resolution; use \"low\" or \"high\""
        ))),
    }
}

fn finite(value: f64, name: &str) -> Result<f64, EvalError> {
    if value.is_finite() {
        Ok(value)
    } else {
        Err(EvalError::Type(format!(
            "{name} must be a finite number, not {value}"
        )))
    }
}

impl ShapeHandle {
    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<ResolvedShape, EvalError> {
        Ok(match self {
            Self::Line(shape) => {
                let shape = shape.read();
                ResolvedShape::Line(
                    [
                        finite(resolver.get(&shape.x1)?, "x1")?,
                        finite(resolver.get(&shape.y1)?, "y1")?,
                        finite(resolver.get(&shape.x2)?, "x2")?,
                        finite(resolver.get(&shape.y2)?, "y2")?,
                    ],
                    resolver.get(&shape.color)?,
                    shape
                        .fill_to_y
                        .as_ref()
                        .map(|value| resolver.get(value))
                        .transpose()?,
                )
            }
            Self::Rectangle(shape) => {
                let shape = shape.read();
                ResolvedShape::Rectangle(
                    [
                        finite(resolver.get(&shape.x)?, "x")?,
                        finite(resolver.get(&shape.y)?, "y")?,
                        finite(resolver.get(&shape.width)?, "width")?,
                        finite(resolver.get(&shape.height)?, "height")?,
                    ],
                    resolver.get(&shape.color)?,
                )
            }
            Self::Circle(shape) => {
                let shape = shape.read();
                ResolvedShape::Circle(
                    [
                        finite(resolver.get(&shape.x)?, "x")?,
                        finite(resolver.get(&shape.y)?, "y")?,
                        finite(resolver.get(&shape.radius)?, "radius")?,
                    ],
                    resolver.get(&shape.color)?,
                )
            }
            Self::Points(shape) => {
                let shape = shape.read();
                ResolvedShape::Points(shape.coordinates.clone(), resolver.get(&shape.color)?)
            }
            Self::Map(shape) => {
                let shape = shape.read();
                ResolvedShape::Map(
                    resolve_map_resolution(&resolver.get(&shape.resolution)?)?,
                    resolver.get(&shape.color)?,
                )
            }
            Self::Label(shape) => {
                let shape = shape.read();
                ResolvedShape::Label(
                    finite(resolver.get(&shape.x)?, "x")?,
                    finite(resolver.get(&shape.y)?, "y")?,
                    resolver.get(&shape.text)?,
                    shape.style.resolve(resolver)?,
                )
            }
            Self::Layer => ResolvedShape::Layer,
            Self::Marker(shape) => {
                ResolvedShape::Marker(resolve_marker(resolver, &shape.read().marker)?)
            }
        })
    }
}

impl WidgetSpec for CanvasSpec {
    type Resolved = ResolvedCanvas;

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Self::Resolved, EvalError> {
        let bounds = |pair: &[Dynamic<f64>; 2],
                      resolver: &mut Resolver<'_>,
                      name: &str|
         -> Result<[f64; 2], EvalError> {
            Ok([
                finite(resolver.get(&pair[0])?, name)?,
                finite(resolver.get(&pair[1])?, name)?,
            ])
        };
        let mut shapes = Vec::with_capacity(self.shapes.len());
        for shape in &self.shapes {
            shapes.push(shape.resolve(resolver)?);
        }
        Ok(ResolvedCanvas {
            x_bounds: bounds(&self.x_bounds, resolver, "an x bound")?,
            y_bounds: bounds(&self.y_bounds, resolver, "a y bound")?,
            marker: resolve_marker(resolver, &self.marker)?,
            background_color: resolver
                .get_optional(&self.background_color)?
                .unwrap_or(Color::Reset),
            shapes,
            block: resolve_optional(&self.block, resolver)?,
        })
    }

    fn draw(resolved: &Self::Resolved, grid: &mut Grid) {
        let shapes = &resolved.shapes;
        let mut canvas = Canvas::default()
            .x_bounds(resolved.x_bounds)
            .y_bounds(resolved.y_bounds)
            .marker(resolved.marker)
            .background_color(resolved.background_color)
            .paint(|context| {
                for shape in shapes {
                    match shape {
                        ResolvedShape::Line([x1, y1, x2, y2], color, None) => {
                            context.draw(&Line::new(*x1, *y1, *x2, *y2, *color));
                        }
                        ResolvedShape::Line([x1, y1, x2, y2], color, Some(fill_to_y)) => {
                            context.draw(&FilledLine::new(*x1, *y1, *x2, *y2, *fill_to_y, *color));
                        }
                        ResolvedShape::Rectangle([x, y, width, height], color) => {
                            context.draw(&Rectangle::new(*x, *y, *width, *height, *color));
                        }
                        ResolvedShape::Circle([x, y, radius], color) => {
                            context.draw(&Circle::new(*x, *y, *radius, *color));
                        }
                        ResolvedShape::Points(coordinates, color) => {
                            context.draw(&Points::new(coordinates, *color));
                        }
                        ResolvedShape::Map(resolution, color) => {
                            context.draw(&Map {
                                resolution: *resolution,
                                color: *color,
                            });
                        }
                        ResolvedShape::Label(x, y, text, style) => {
                            context.print(*x, *y, TextLine::styled(text.clone(), *style));
                        }
                        ResolvedShape::Layer => context.layer(),
                        ResolvedShape::Marker(marker) => context.marker(*marker),
                    }
                }
            });
        if let Some(block) = &resolved.block {
            canvas = canvas.block(block.to_widget());
        }
        let area = Rect::new(0, 0, grid.width(), grid.height());
        canvas.render(area, grid.buffer_mut());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::expression::{Environment, PropertyId, Scalar};
    use crate::painter::Spec;

    struct Offline;
    impl Environment for Offline {
        fn property(&self, id: PropertyId) -> Result<Scalar, EvalError> {
            Err(EvalError::RuntimeRequired(id.name().to_owned()))
        }
    }

    #[test]
    fn marker_names_and_characters_parse() {
        for name in MARKER_NAMES {
            assert!(marker_from_name(name).is_some(), "{name}");
        }
        assert_eq!(marker_from_name("#"), Some(Marker::Custom('#')));
        assert_eq!(marker_from_name("two"), None);
    }

    #[test]
    fn a_canvas_with_a_rectangle_draws_cells() {
        let mut spec = CanvasSpec {
            x_bounds: [Dynamic::Fixed(0.0), Dynamic::Fixed(10.0)],
            y_bounds: [Dynamic::Fixed(0.0), Dynamic::Fixed(10.0)],
            marker: Dynamic::Fixed("block".to_owned()),
            ..CanvasSpec::default()
        };
        spec.shapes
            .push(ShapeHandle::Rectangle(Spec::new(RectangleShape {
                x: Dynamic::Fixed(0.0),
                y: Dynamic::Fixed(0.0),
                width: Dynamic::Fixed(10.0),
                height: Dynamic::Fixed(10.0),
                color: Dynamic::Fixed(Color::Red),
            })));
        let resolved = spec.resolve(&mut Resolver::new(&Offline)).unwrap();
        let mut grid = Grid::new(10, 5);
        CanvasSpec::draw(&resolved, &mut grid);
        assert!(grid.text_rows().iter().any(|row| row.contains('█')));
    }

    #[test]
    fn a_non_finite_bound_is_rejected() {
        let mut spec = CanvasSpec::default();
        spec.x_bounds[1] = Dynamic::Fixed(f64::NAN);
        assert!(spec.resolve(&mut Resolver::new(&Offline)).is_err());
    }
}
