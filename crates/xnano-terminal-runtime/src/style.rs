//! Colors and styles, built on ratatui's types so cells, widgets and cell grids agree.

use std::str::FromStr;

pub use ratatui_core::style::{Color, Modifier, Style};

/// The modifier names accepted and reported by xnano, in display order.
pub const MODIFIERS: [(&str, Modifier); 9] = [
    ("bold", Modifier::BOLD),
    ("dim", Modifier::DIM),
    ("italic", Modifier::ITALIC),
    ("underline", Modifier::UNDERLINED),
    ("blink", Modifier::SLOW_BLINK),
    ("rapid_blink", Modifier::RAPID_BLINK),
    ("reverse", Modifier::REVERSED),
    ("hidden", Modifier::HIDDEN),
    ("crossed_out", Modifier::CROSSED_OUT),
];

/// The modifier called `name`, if there is one.
pub fn modifier_from_name(name: &str) -> Option<Modifier> {
    MODIFIERS
        .iter()
        .find(|(candidate, _)| *candidate == name)
        .map(|(_, modifier)| *modifier)
}

/// The names of every modifier set in `modifiers`.
pub fn modifier_names(modifiers: Modifier) -> Vec<&'static str> {
    MODIFIERS
        .iter()
        .filter(|(_, modifier)| modifiers.contains(*modifier))
        .map(|(name, _)| *name)
        .collect()
}

/// Parse a color name, `#rrggbb` / `#rgb` hex value, or a 0-255 palette index.
///
/// Names are case-insensitive and accept `_`, `-` or a space as separators:
/// `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `gray`, `dark_gray`,
/// `light_red` (or `bright_red`) and so on, `white` and `reset`.
///
/// A Tailwind name such as `slate-400` is not a color here. Resolve one with
/// [`tailwind_color`].
pub fn parse_color(text: &str) -> Result<Color, String> {
    let trimmed = text.trim();
    if let Some(hex) = trimmed.strip_prefix('#') {
        let expanded = match hex.len() {
            3 => hex
                .chars()
                .flat_map(|digit| [digit, digit])
                .collect::<String>(),
            6 => hex.to_owned(),
            _ => String::new(),
        };
        if expanded.len() == 6
            && let Ok(value) = u32::from_str_radix(&expanded, 16)
        {
            return Ok(Color::Rgb(
                (value >> 16) as u8,
                (value >> 8) as u8,
                value as u8,
            ));
        }
        return Err(format!(
            "\"{text}\" is not a hex color; use #rrggbb or #rgb, for example #ff8800"
        ));
    }
    if let Ok(index) = trimmed.parse::<u16>() {
        return u8::try_from(index)
            .map(Color::Indexed)
            .map_err(|_| format!("the palette index {index} is out of range; use 0 to 255"));
    }
    let normalized = trimmed
        .to_ascii_lowercase()
        .replace(['-', ' '], "_")
        .replace("bright_", "light_")
        .replace("grey", "gray");
    let normalized = match normalized.as_str() {
        "dark_gray" | "darkgray" | "light_black" => "darkgray".to_owned(),
        other => other.replace('_', ""),
    };
    Color::from_str(&normalized).map_err(|_| {
        format!(
            "\"{text}\" is not a color; use a name such as \"red\" or \"light_blue\", \
             a hex value such as \"#ff8800\", or a palette index from 0 to 255"
        )
    })
}

/// The red, green and blue of a true color, or `None` for named, indexed and reset colors.
pub fn to_rgb(color: Color) -> Option<(u8, u8, u8)> {
    match color {
        Color::Rgb(red, green, blue) => Some((red, green, blue)),
        _ => None,
    }
}

/// A readable name for a color, for `repr` and error messages.
pub fn describe_color(color: Color) -> String {
    match color {
        Color::Rgb(red, green, blue) => format!("#{red:02x}{green:02x}{blue:02x}"),
        Color::Indexed(index) => format!("indexed({index})"),
        Color::Reset => "reset".to_owned(),
        named => format!("{named}").to_ascii_lowercase().replace(' ', "_"),
    }
}

/// Resolve a Tailwind palette shade using ratatui's canonical palette.
///
/// `name` is a palette such as `slate` or `red`. `shade` is 50, 100 through 900, or 950.
pub fn tailwind_color(name: &str, shade: u16) -> Result<Color, String> {
    use ratatui_core::style::palette::tailwind;
    let palette = match name.to_ascii_lowercase().as_str() {
        "slate" => tailwind::SLATE,
        "gray" => tailwind::GRAY,
        "zinc" => tailwind::ZINC,
        "neutral" => tailwind::NEUTRAL,
        "stone" => tailwind::STONE,
        "red" => tailwind::RED,
        "orange" => tailwind::ORANGE,
        "amber" => tailwind::AMBER,
        "yellow" => tailwind::YELLOW,
        "lime" => tailwind::LIME,
        "green" => tailwind::GREEN,
        "emerald" => tailwind::EMERALD,
        "teal" => tailwind::TEAL,
        "cyan" => tailwind::CYAN,
        "sky" => tailwind::SKY,
        "blue" => tailwind::BLUE,
        "indigo" => tailwind::INDIGO,
        "violet" => tailwind::VIOLET,
        "purple" => tailwind::PURPLE,
        "fuchsia" => tailwind::FUCHSIA,
        "pink" => tailwind::PINK,
        "rose" => tailwind::ROSE,
        other => return Err(format!("unknown Tailwind palette {other:?}")),
    };
    Ok(match shade {
        50 => palette.c50,
        100 => palette.c100,
        200 => palette.c200,
        300 => palette.c300,
        400 => palette.c400,
        500 => palette.c500,
        600 => palette.c600,
        700 => palette.c700,
        800 => palette.c800,
        900 => palette.c900,
        950 => palette.c950,
        _ => {
            return Err(format!(
                "invalid Tailwind shade {shade}; use 50, 100 through 900, or 950"
            ));
        }
    })
}
