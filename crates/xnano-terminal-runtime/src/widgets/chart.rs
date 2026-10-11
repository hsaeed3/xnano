//! The ratatui `Chart`: datasets plotted against two axes.
//!
//! Maps to `ratatui::widgets::Chart`.

use ratatui::widgets::{Axis, Chart, Dataset, GraphType, LegendPosition};
use ratatui_core::layout::{Alignment, Constraint, Rect};
use ratatui_core::style::Style;
use ratatui_core::symbols::Marker;
use ratatui_core::text::Line;
use ratatui_core::widgets::Widget;

use crate::dynamic::Dynamic;
use crate::expression::EvalError;
use crate::grid::Grid;
use crate::widgets::block::{BlockSpec, ResolvedBlock, resolve_optional};
use crate::widgets::canvas::{marker_error, marker_from_name};
use crate::widgets::style::StyleSpec;
use crate::widgets::{Resolver, Shared, WidgetSpec};

/// The graph types a dataset can use.
pub const GRAPH_TYPES: [&str; 3] = ["scatter", "line", "bar"];

/// The legend positions, besides `None` which hides the legend.
pub const LEGEND_POSITIONS: [(&str, LegendPosition); 8] = [
    ("top", LegendPosition::Top),
    ("top_right", LegendPosition::TopRight),
    ("top_left", LegendPosition::TopLeft),
    ("left", LegendPosition::Left),
    ("right", LegendPosition::Right),
    ("bottom", LegendPosition::Bottom),
    ("bottom_right", LegendPosition::BottomRight),
    ("bottom_left", LegendPosition::BottomLeft),
];

fn graph_type(name: &str) -> Result<GraphType, EvalError> {
    match name {
        "scatter" => Ok(GraphType::Scatter),
        "line" => Ok(GraphType::Line),
        "bar" => Ok(GraphType::Bar),
        other => Err(EvalError::Type(format!(
            "\"{other}\" is not a graph type; use {}",
            GRAPH_TYPES.join(", ")
        ))),
    }
}

/// A size limit for the hidden legend: a kind such as `"length"` and its numbers.
#[derive(Debug, Clone, PartialEq)]
pub struct LimitSpec {
    pub kind: String,
    pub value: u32,
    pub denominator: u32,
}

impl LimitSpec {
    /// The ratatui constraint these numbers describe.
    pub fn constraint(&self) -> Result<Constraint, String> {
        let short = |value: u32| {
            u16::try_from(value).map_err(|_| format!("{value} is too large for a size limit"))
        };
        Ok(match self.kind.as_str() {
            "length" => Constraint::Length(short(self.value)?),
            "min" => Constraint::Min(short(self.value)?),
            "max" => Constraint::Max(short(self.value)?),
            "percentage" => Constraint::Percentage(short(self.value)?),
            "fill" => Constraint::Fill(short(self.value)?),
            "ratio" => {
                if self.denominator == 0 {
                    return Err("a ratio limit cannot have a denominator of zero".to_owned());
                }
                Constraint::Ratio(self.value, self.denominator)
            }
            other => {
                return Err(format!(
                    "\"{other}\" is not a size limit; use length, min, max, percentage, fill or ratio"
                ));
            }
        })
    }
}

/// One series of points.
#[derive(Debug, Clone)]
pub struct DatasetSpec {
    pub name: Option<Dynamic<String>>,
    pub data: Vec<(f64, f64)>,
    pub marker: Dynamic<String>,
    pub graph_type: Dynamic<String>,
    pub style: StyleSpec,
    pub fill_to_y: Dynamic<f64>,
}

impl Default for DatasetSpec {
    fn default() -> Self {
        Self {
            name: None,
            data: Vec::new(),
            marker: Dynamic::Fixed("dot".to_owned()),
            graph_type: Dynamic::Fixed("scatter".to_owned()),
            style: StyleSpec::default(),
            fill_to_y: Dynamic::Fixed(0.0),
        }
    }
}

/// One axis.
#[derive(Debug, Clone)]
pub struct AxisSpec {
    pub title: Option<Dynamic<String>>,
    pub bounds: [Dynamic<f64>; 2],
    pub labels: Vec<Dynamic<String>>,
    pub style: StyleSpec,
    pub labels_alignment: Alignment,
}

impl Default for AxisSpec {
    fn default() -> Self {
        Self {
            title: None,
            bounds: [Dynamic::Fixed(0.0), Dynamic::Fixed(1.0)],
            labels: Vec::new(),
            style: StyleSpec::default(),
            labels_alignment: Alignment::Left,
        }
    }
}

/// The settings of a chart.
#[derive(Debug, Clone)]
pub struct ChartSpec {
    pub datasets: Vec<Shared<DatasetSpec>>,
    pub x_axis: Shared<AxisSpec>,
    pub y_axis: Shared<AxisSpec>,
    pub style: StyleSpec,
    /// `None` hides the legend.
    pub legend_position: Option<Dynamic<String>>,
    pub hidden_legend_limits: Option<(LimitSpec, LimitSpec)>,
    pub block: Option<Shared<BlockSpec>>,
}

#[derive(Debug)]
struct ResolvedDataset {
    name: Option<String>,
    data: Vec<(f64, f64)>,
    marker: Marker,
    graph_type: GraphType,
    style: Style,
    fill_to_y: f64,
}

#[derive(Debug)]
struct ResolvedAxis {
    title: Option<String>,
    bounds: [f64; 2],
    labels: Vec<String>,
    style: Style,
    labels_alignment: Alignment,
}

#[derive(Debug)]
pub struct ResolvedChart {
    datasets: Vec<ResolvedDataset>,
    x_axis: ResolvedAxis,
    y_axis: ResolvedAxis,
    style: Style,
    legend_position: Option<LegendPosition>,
    hidden_legend_limits: Option<(Constraint, Constraint)>,
    block: Option<ResolvedBlock>,
}

fn resolve_axis(
    axis: &Shared<AxisSpec>,
    resolver: &mut Resolver<'_>,
    name: &str,
) -> Result<ResolvedAxis, EvalError> {
    let axis = axis.read();
    let bound = |value: &Dynamic<f64>, resolver: &mut Resolver<'_>| {
        let number = resolver.get(value)?;
        if number.is_finite() {
            Ok(number)
        } else {
            Err(EvalError::Type(format!(
                "a bound of the {name} axis must be a finite number, not {number}"
            )))
        }
    };
    let mut labels = Vec::with_capacity(axis.labels.len());
    for label in &axis.labels {
        labels.push(resolver.get(label)?);
    }
    Ok(ResolvedAxis {
        title: resolver.get_optional(&axis.title)?,
        bounds: [
            bound(&axis.bounds[0], resolver)?,
            bound(&axis.bounds[1], resolver)?,
        ],
        labels,
        style: axis.style.resolve(resolver)?,
        labels_alignment: axis.labels_alignment,
    })
}

fn build_axis(axis: &ResolvedAxis) -> Axis<'static> {
    let mut built = Axis::default()
        .bounds(axis.bounds)
        .labels(axis.labels.iter().map(|label| Line::from(label.clone())))
        .style(axis.style)
        .labels_alignment(axis.labels_alignment);
    if let Some(title) = &axis.title {
        built = built.title(title.clone());
    }
    built
}

impl WidgetSpec for ChartSpec {
    type Resolved = ResolvedChart;

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Self::Resolved, EvalError> {
        let mut datasets = Vec::with_capacity(self.datasets.len());
        for dataset in &self.datasets {
            let dataset = dataset.read();
            let marker_name = resolver.get(&dataset.marker)?;
            datasets.push(ResolvedDataset {
                name: resolver.get_optional(&dataset.name)?,
                data: dataset.data.clone(),
                marker: marker_from_name(&marker_name)
                    .ok_or_else(|| EvalError::Type(marker_error(&marker_name)))?,
                graph_type: graph_type(&resolver.get(&dataset.graph_type)?)?,
                style: dataset.style.resolve(resolver)?,
                fill_to_y: resolver.get(&dataset.fill_to_y)?,
            });
        }
        let legend_position = match resolver.get_optional(&self.legend_position)? {
            None => None,
            Some(name) => Some(
                LEGEND_POSITIONS
                    .iter()
                    .find(|(candidate, _)| *candidate == name)
                    .map(|(_, position)| *position)
                    .ok_or_else(|| {
                        EvalError::Type(format!(
                            "\"{name}\" is not a legend position; use one of {}",
                            LEGEND_POSITIONS
                                .iter()
                                .map(|(name, _)| *name)
                                .collect::<Vec<_>>()
                                .join(", ")
                        ))
                    })?,
            ),
        };
        let hidden_legend_limits = match &self.hidden_legend_limits {
            None => None,
            Some((width, height)) => Some((
                width.constraint().map_err(EvalError::Type)?,
                height.constraint().map_err(EvalError::Type)?,
            )),
        };
        Ok(ResolvedChart {
            datasets,
            x_axis: resolve_axis(&self.x_axis, resolver, "x")?,
            y_axis: resolve_axis(&self.y_axis, resolver, "y")?,
            style: self.style.resolve(resolver)?,
            legend_position,
            hidden_legend_limits,
            block: resolve_optional(&self.block, resolver)?,
        })
    }

    fn draw(resolved: &Self::Resolved, grid: &mut Grid) {
        let datasets = resolved
            .datasets
            .iter()
            .map(|dataset| {
                let mut built = Dataset::default()
                    .data(&dataset.data)
                    .marker(dataset.marker)
                    .graph_type(dataset.graph_type)
                    .style(dataset.style)
                    .fill_to_y(dataset.fill_to_y);
                if let Some(name) = &dataset.name {
                    built = built.name(name.clone());
                }
                built
            })
            .collect::<Vec<_>>();
        let mut chart = Chart::new(datasets)
            .x_axis(build_axis(&resolved.x_axis))
            .y_axis(build_axis(&resolved.y_axis))
            .style(resolved.style)
            .legend_position(resolved.legend_position);
        if let Some((width, height)) = resolved.hidden_legend_limits {
            chart = chart.hidden_legend_constraints((width, height));
        }
        if let Some(block) = &resolved.block {
            chart = chart.block(block.to_widget());
        }
        let area = Rect::new(0, 0, grid.width(), grid.height());
        chart.render(area, grid.buffer_mut());
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

    fn sample() -> ChartSpec {
        let dataset = DatasetSpec {
            name: Some(Dynamic::Fixed("series".to_owned())),
            data: vec![(0.0, 0.0), (1.0, 1.0)],
            graph_type: Dynamic::Fixed("line".to_owned()),
            ..DatasetSpec::default()
        };
        ChartSpec {
            datasets: vec![Spec::new(dataset)],
            x_axis: Spec::new(AxisSpec::default()),
            y_axis: Spec::new(AxisSpec::default()),
            style: StyleSpec::default(),
            legend_position: Some(Dynamic::Fixed("top_right".to_owned())),
            hidden_legend_limits: None,
            block: None,
        }
    }

    #[test]
    fn a_line_dataset_draws_and_names_the_legend() {
        let spec = sample();
        let resolved = spec.resolve(&mut Resolver::new(&Offline)).unwrap();
        let mut grid = Grid::new(30, 10);
        ChartSpec::draw(&resolved, &mut grid);
        assert!(grid.text_rows().iter().any(|row| row.contains("series")));
    }

    #[test]
    fn unknown_names_explain_the_choices() {
        let mut spec = sample();
        spec.legend_position = Some(Dynamic::Fixed("middle".to_owned()));
        let error = spec.resolve(&mut Resolver::new(&Offline)).unwrap_err();
        assert!(error.to_string().contains("top_right"));
    }

    #[test]
    fn limits_convert_to_constraints() {
        let ratio = LimitSpec {
            kind: "ratio".into(),
            value: 1,
            denominator: 4,
        };
        assert_eq!(ratio.constraint(), Ok(Constraint::Ratio(1, 4)));
        let zero = LimitSpec {
            kind: "ratio".into(),
            value: 1,
            denominator: 0,
        };
        assert!(zero.constraint().is_err());
    }
}
