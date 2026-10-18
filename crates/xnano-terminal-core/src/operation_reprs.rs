//! The `repr` of operations: the Python call that builds each one.
//!
//! Settings that are left at their defaults are not shown, and data with no literal
//! form, such as pixels or a drawing, is shown as `<...>`, as Python does for objects that
//! cannot be written back as code.

use ratatui_core::style::Style;
use xnano_terminal_runtime::grid::{PasteMode, WriteMode};
use xnano_terminal_runtime::layout::{Arrangement, LayoutSpec, SizeRule};
use xnano_terminal_runtime::operation::{BorderKind, Operation};
use xnano_terminal_runtime::style::{describe_color, modifier_names};

use crate::style::style_repr;

/// The Python class that builds an operation of this kind.
fn class_name(operation: &Operation) -> &'static str {
    match operation {
        Operation::Resize { .. } => "Resize",
        Operation::Move { .. } => "Move",
        Operation::Place { .. } => "Place",
        Operation::Write { .. } => "Write",
        Operation::Fill(_) => "Fill",
        Operation::Clear => "Clear",
        Operation::Foreground(_) => "Foreground",
        Operation::Background(_) => "Background",
        Operation::ApplyStyle(_) => "ApplyStyle",
        Operation::Border { .. } => "Border",
        Operation::Paste { .. } => "Paste",
        Operation::Pixels { .. } => "Pixels",
        Operation::Raster { .. } => "Raster",
        Operation::SetState { .. } => "SetState",
        Operation::ApplyStatePatch { .. } => "ApplyStatePatch",
        Operation::Draw { .. } => "Draw",
        Operation::AnimateDrawing { .. } => "AnimateDrawing",
        Operation::Effect(_) => "Effect",
        Operation::CancelEffect(_) => "CancelEffect",
        Operation::Fuzz { .. } => "Fuzz",
        Operation::Layout(_) => "Layout",
        Operation::Component(_) => "Component",
        Operation::Editor(_) => "Editor",
        Operation::Sequence(_) => "SequenceOperation",
        Operation::Conditional { .. } => "Conditional",
        Operation::SetValue { .. } => "SetValue",
        Operation::Dynamic(_) => "Operation",
    }
}

/// Text as a Python string literal.
fn text_literal(text: &str) -> String {
    let escaped = text
        .replace('\\', "\\\\")
        .replace('\'', "\\'")
        .replace('\n', "\\n");
    format!("'{escaped}'")
}

/// `CamelCase` debug text as the `snake_case` word Python takes, such as `'half_blocks'`.
fn snake_word(debug: impl std::fmt::Debug) -> String {
    let text = format!("{debug:?}");
    let mut word = String::with_capacity(text.len() + 4);
    for (index, character) in text.chars().enumerate() {
        if character.is_uppercase() {
            if index > 0 {
                word.push('_');
            }
            word.extend(character.to_lowercase());
        } else {
            word.push(character);
        }
    }
    format!("'{word}'")
}

fn style_argument(style: &Style) -> Option<String> {
    (*style != Style::default()).then(|| format!("style={}", style_repr(style)))
}

fn size_rule(rule: &SizeRule) -> String {
    match rule {
        SizeRule::Cells(count) => format!("SizeRule.cells({count})"),
        SizeRule::Percent(percentage) => format!("SizeRule.percent({percentage})"),
        SizeRule::Fill(weight) => format!("SizeRule.fill({weight})"),
        SizeRule::Fit => "SizeRule.fit()".to_owned(),
        SizeRule::Minimum(count) => format!("SizeRule.minimum({count})"),
        SizeRule::Maximum(count) => format!("SizeRule.maximum({count})"),
    }
}

fn layout_arguments(layout: &LayoutSpec) -> Vec<String> {
    let arrangement = match layout.arrangement {
        Arrangement::Row => "'row'",
        Arrangement::Column => "'column'",
        Arrangement::Overlay => "'overlay'",
    };
    let mut arguments = vec![arrangement.to_owned()];
    if !layout.sizes.is_empty() {
        let sizes: Vec<String> = layout.sizes.iter().map(size_rule).collect();
        arguments.push(format!("sizes=[{}]", sizes.join(", ")));
    }
    if layout.spacing != 0 {
        arguments.push(format!("spacing={}", layout.spacing));
    }
    if layout.padding != 0 {
        arguments.push(format!("padding={}", layout.padding));
    }
    arguments
}

fn position_arguments(arguments: &mut Vec<String>, x: i32, y: i32) {
    if x != 0 {
        arguments.push(format!("x={x}"));
    }
    if y != 0 {
        arguments.push(format!("y={y}"));
    }
}

/// The arguments of the Python call that builds `operation`.
fn arguments(operation: &Operation) -> Vec<String> {
    match operation {
        Operation::Resize { width, height } => {
            vec![format!("width={width}"), format!("height={height}")]
        }
        Operation::Move { x, y } | Operation::Place { x, y } => {
            vec![format!("x={x}"), format!("y={y}")]
        }
        Operation::Write {
            lines,
            x,
            y,
            style,
            mode,
        } => {
            let text: Vec<String> = lines
                .iter()
                .map(|line| line.iter().map(|span| span.text.as_str()).collect())
                .collect();
            let mut arguments = vec![text_literal(&text.join("\n"))];
            position_arguments(&mut arguments, *x, *y);
            arguments.extend(style_argument(style));
            if *mode != WriteMode::default() {
                arguments.push(format!("mode={}", snake_word(mode)));
            }
            arguments
        }
        Operation::Fill(cell) => {
            let is_plain = cell.fg == ratatui_core::style::Color::Reset
                && cell.bg == ratatui_core::style::Color::Reset
                && cell.modifier.is_empty();
            if is_plain {
                vec![text_literal(cell.symbol())]
            } else {
                vec![format!(
                    "Cell({}, foreground='{}', background='{}', modifiers={:?})",
                    text_literal(cell.symbol()),
                    describe_color(cell.fg),
                    describe_color(cell.bg),
                    modifier_names(cell.modifier)
                )]
            }
        }
        Operation::Clear => Vec::new(),
        Operation::Foreground(color) | Operation::Background(color) => {
            vec![format!("'{}'", describe_color(*color))]
        }
        Operation::ApplyStyle(style) => vec![style_repr(style)],
        Operation::Border { kind, style } => {
            let mut arguments = Vec::new();
            if *kind != BorderKind::Plain {
                arguments.push(snake_word(kind));
            }
            arguments.extend(style_argument(style));
            arguments
        }
        Operation::Paste { x, y, mode, .. } => {
            let mut arguments = vec!["<source>".to_owned()];
            position_arguments(&mut arguments, *x, *y);
            if *mode != PasteMode::default() {
                arguments.push(format!("mode={}", snake_word(mode)));
            }
            arguments
        }
        Operation::Pixels {
            pixels, encoding, ..
        } => vec![
            format!("<{} pixels>", pixels.len()),
            format!("encoding={}", snake_word(encoding)),
        ],
        Operation::Raster {
            width,
            height,
            x,
            y,
            ..
        } => {
            let mut arguments = vec![
                "<rgba>".to_owned(),
                format!("width={width}"),
                format!("height={height}"),
            ];
            position_arguments(&mut arguments, *x, *y);
            arguments
        }
        Operation::SetState { path, .. } => {
            vec![format!("state.{}", path.join(".")), "<value>".to_owned()]
        }
        Operation::ApplyStatePatch { path, .. } => {
            vec![format!("state.{}", path.join(".")), "<patch>".to_owned()]
        }
        Operation::Draw { x, y, .. } => {
            let mut arguments = vec!["<drawing>".to_owned()];
            position_arguments(&mut arguments, *x, *y);
            arguments
        }
        Operation::AnimateDrawing { x, y, .. } => {
            let mut arguments = vec!["<animation>".to_owned()];
            position_arguments(&mut arguments, *x, *y);
            arguments
        }
        Operation::Effect(_) => vec!["<effect>".to_owned()],
        Operation::CancelEffect(key) => vec![text_literal(key)],
        Operation::Fuzz { intensity, seed } => {
            let mut arguments = vec![intensity.to_string()];
            if let Some(seed) = seed {
                arguments.push(format!("seed={seed}"));
            }
            arguments
        }
        Operation::Layout(layout) => layout_arguments(layout),
        Operation::Component(_) => vec!["<component>".to_owned()],
        Operation::Editor(_) => vec!["<editor>".to_owned()],
        Operation::Sequence(operations) => operations
            .iter()
            .map(|operation| operation_repr(operation, class_name(operation)))
            .collect(),
        Operation::Conditional {
            condition,
            then,
            otherwise,
        } => {
            let mut arguments = vec![
                condition.to_string(),
                operation_repr(then, class_name(then)),
            ];
            if let Some(otherwise) = otherwise {
                arguments.push(format!(
                    "otherwise={}",
                    operation_repr(otherwise, class_name(otherwise))
                ));
            }
            arguments
        }
        Operation::SetValue { property, value } => {
            vec![property.python_name().to_owned(), value.to_string()]
        }
        Operation::Dynamic(_) => vec!["<dynamic settings>".to_owned()],
    }
}

/// The Python call that builds `operation`, under the class name `name`.
pub fn operation_repr(operation: &Operation, name: &str) -> String {
    format!("{name}({})", arguments(operation).join(", "))
}
