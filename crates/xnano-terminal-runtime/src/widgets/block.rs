//! The ratatui `Block`: borders, titles and padding around a widget.
//!
//! Maps to `ratatui::widgets::Block`.

use ratatui::widgets::{Block, BorderType, Borders, Padding};
use ratatui_core::layout::{Alignment, Rect};
use ratatui_core::style::Style;
use ratatui_core::symbols::merge::MergeStrategy;
use ratatui_core::text::Line as RLine;
use ratatui_core::widgets::Widget;

use crate::dynamic::Dynamic;
use crate::expression::EvalError;
use crate::grid::Grid;
use crate::widgets::style::StyleSpec;
use crate::widgets::{Resolver, Shared, WidgetSpec};

/// The sides of a block that draw a border.
pub const BORDER_SIDES: [(&str, Borders); 4] = [
    ("top", Borders::TOP),
    ("right", Borders::RIGHT),
    ("bottom", Borders::BOTTOM),
    ("left", Borders::LEFT),
];

pub const BORDER_TYPES: [(&str, BorderType); 11] = [
    ("plain", BorderType::Plain),
    ("rounded", BorderType::Rounded),
    ("double", BorderType::Double),
    ("thick", BorderType::Thick),
    ("light_double_dashed", BorderType::LightDoubleDashed),
    ("heavy_double_dashed", BorderType::HeavyDoubleDashed),
    ("light_triple_dashed", BorderType::LightTripleDashed),
    ("heavy_triple_dashed", BorderType::HeavyTripleDashed),
    ("light_quadruple_dashed", BorderType::LightQuadrupleDashed),
    ("heavy_quadruple_dashed", BorderType::HeavyQuadrupleDashed),
    ("quadrant_inside", BorderType::QuadrantInside),
];

pub const MERGE_STRATEGIES: [(&str, MergeStrategy); 3] = [
    ("replace", MergeStrategy::Replace),
    ("exact", MergeStrategy::Exact),
    ("fuzzy", MergeStrategy::Fuzzy),
];

pub fn border_type_from_name(name: &str) -> Option<BorderType> {
    BORDER_TYPES
        .iter()
        .find(|(candidate, _)| *candidate == name)
        .map(|(_, kind)| *kind)
}

pub fn alignment_from_name(name: &str) -> Option<Alignment> {
    Some(match name {
        "left" => Alignment::Left,
        "center" => Alignment::Center,
        "right" => Alignment::Right,
        _ => return None,
    })
}

/// One title of a block.
#[derive(Debug, Clone)]
pub struct TitleSpec {
    pub text: Dynamic<String>,
    pub is_bottom: bool,
    pub alignment: Option<Alignment>,
    pub style: StyleSpec,
}

/// The settings of a block.
#[derive(Debug, Clone)]
pub struct BlockSpec {
    /// Border sides, as names from [`BORDER_SIDES`].
    pub sides: Vec<String>,
    pub border_type: Dynamic<String>,
    pub border_style: StyleSpec,
    pub style: StyleSpec,
    pub title_style: StyleSpec,
    pub titles: Vec<TitleSpec>,
    pub title_alignment: Alignment,
    pub padding: [Dynamic<u16>; 4],
    pub merge_strategy: Option<String>,
}

impl Default for BlockSpec {
    fn default() -> Self {
        Self {
            sides: BORDER_SIDES
                .iter()
                .map(|(name, _)| (*name).to_owned())
                .collect(),
            border_type: Dynamic::Fixed("plain".to_owned()),
            border_style: StyleSpec::default(),
            style: StyleSpec::default(),
            title_style: StyleSpec::default(),
            titles: Vec::new(),
            title_alignment: Alignment::Left,
            padding: [
                Dynamic::Fixed(0),
                Dynamic::Fixed(0),
                Dynamic::Fixed(0),
                Dynamic::Fixed(0),
            ],
            merge_strategy: None,
        }
    }
}

/// A block with every bound value read.
#[derive(Debug, Clone)]
pub struct ResolvedBlock {
    borders: Borders,
    border_type: BorderType,
    border_style: Style,
    style: Style,
    title_style: Style,
    titles: Vec<(String, bool, Option<Alignment>, Style)>,
    title_alignment: Alignment,
    padding: Padding,
    merge_strategy: Option<MergeStrategy>,
}

impl BlockSpec {
    /// A block that draws no border at all.
    pub fn borderless() -> Self {
        Self {
            sides: Vec::new(),
            ..Self::default()
        }
    }

    pub fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<ResolvedBlock, EvalError> {
        let mut borders = Borders::NONE;
        for side in &self.sides {
            if let Some((_, flag)) = BORDER_SIDES.iter().find(|(name, _)| name == side) {
                borders |= *flag;
            }
        }
        let border_name = resolver.get(&self.border_type)?;
        let border_type = border_type_from_name(&border_name).ok_or_else(|| {
            EvalError::Type(format!(
                "\"{border_name}\" is not a border type; use one of {}",
                BORDER_TYPES
                    .iter()
                    .map(|(name, _)| *name)
                    .collect::<Vec<_>>()
                    .join(", ")
            ))
        })?;
        let mut titles = Vec::with_capacity(self.titles.len());
        for title in &self.titles {
            titles.push((
                resolver.get(&title.text)?,
                title.is_bottom,
                title.alignment,
                title.style.resolve(resolver)?,
            ));
        }
        let [left, right, top, bottom] = &self.padding;
        let merge_strategy = match &self.merge_strategy {
            None => None,
            Some(name) => Some(
                MERGE_STRATEGIES
                    .iter()
                    .find(|(candidate, _)| candidate == name)
                    .map(|(_, strategy)| *strategy)
                    .ok_or_else(|| {
                        EvalError::Type(format!(
                            "\"{name}\" is not a merge strategy; use replace, exact or fuzzy"
                        ))
                    })?,
            ),
        };
        Ok(ResolvedBlock {
            borders,
            border_type,
            border_style: self.border_style.resolve(resolver)?,
            style: self.style.resolve(resolver)?,
            title_style: self.title_style.resolve(resolver)?,
            titles,
            title_alignment: self.title_alignment,
            padding: Padding::new(
                resolver.get(left)?,
                resolver.get(right)?,
                resolver.get(top)?,
                resolver.get(bottom)?,
            ),
            merge_strategy,
        })
    }
}

impl ResolvedBlock {
    /// The ratatui block these settings describe.
    pub fn to_widget(&self) -> Block<'static> {
        let mut block = Block::new()
            .borders(self.borders)
            .border_type(self.border_type)
            .border_style(self.border_style)
            .style(self.style)
            .title_style(self.title_style)
            .title_alignment(self.title_alignment)
            .padding(self.padding);
        if let Some(strategy) = self.merge_strategy {
            block = block.merge_borders(strategy);
        }
        for (text, is_bottom, alignment, style) in &self.titles {
            let mut line = RLine::styled(text.clone(), *style);
            if let Some(alignment) = alignment {
                line = line.alignment(*alignment);
            }
            block = if *is_bottom {
                block.title_bottom(line)
            } else {
                block.title_top(line)
            };
        }
        block
    }

    /// The area inside the borders and padding.
    pub fn inner(&self, area: Rect) -> Rect {
        self.to_widget().inner(area)
    }
}

/// Resolve an optional shared block.
pub fn resolve_optional(
    block: &Option<Shared<BlockSpec>>,
    resolver: &mut Resolver<'_>,
) -> Result<Option<ResolvedBlock>, EvalError> {
    block
        .as_ref()
        .map(|shared| shared.read().resolve(resolver))
        .transpose()
}

impl WidgetSpec for BlockSpec {
    type Resolved = ResolvedBlock;

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Self::Resolved, EvalError> {
        BlockSpec::resolve(self, resolver)
    }

    fn draw(resolved: &Self::Resolved, grid: &mut Grid) {
        let area = Rect::new(0, 0, grid.width(), grid.height());
        resolved.to_widget().render(area, grid.buffer_mut());
    }
}
