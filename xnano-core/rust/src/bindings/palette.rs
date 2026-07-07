use palette::{Hsl, Mix, Srgb, IntoColor};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use ratatui::style::palette::tailwind;
use ratatui::style::Color;

use super::style::PyColor;

fn parse_hex(value: &str) -> PyResult<Color> {
    let hex = value.trim_start_matches('#');
    let parsed = match hex.len() {
        6 => u32::from_str_radix(hex, 16),
        3 => {
            let expanded: String = hex.chars().flat_map(|c| [c, c]).collect();
            u32::from_str_radix(&expanded, 16)
        }
        _ => return Err(PyValueError::new_err(format!("invalid hex color: {value}"))),
    }
    .map_err(|_| PyValueError::new_err(format!("invalid hex color: {value}")))?;
    Ok(Color::from_u32(parsed << 8 | 0xFF))
}

fn color_to_srgb_components(color: Color) -> Srgb<f32> {
    match color {
        Color::Rgb(r, g, b) => Srgb::new(r as f32 / 255.0, g as f32 / 255.0, b as f32 / 255.0),
        Color::Indexed(i) => {
            let c = Color::from_u32(i as u32);
            color_to_srgb_components(c)
        }
        other => {
            let value = format!("{other:?}");
            if let Some(hex) = value.strip_prefix("Rgb(") {
                let parts: Vec<&str> = hex.trim_end_matches(')').split(", ").collect();
                if parts.len() == 3 {
                    if let (Ok(r), Ok(g), Ok(b)) = (
                        parts[0].parse::<u8>(),
                        parts[1].parse::<u8>(),
                        parts[2].parse::<u8>(),
                    ) {
                        return Srgb::new(r as f32 / 255.0, g as f32 / 255.0, b as f32 / 255.0);
                    }
                }
            }
            Srgb::new(0.5, 0.5, 0.5)
        }
    }
}

#[pyfunction]
fn color_from_hsl(h: f32, s: f32, l: f32) -> PyColor {
    PyColor {
        inner: Color::from_hsl(Hsl::new(h, s, l)),
    }
}

#[pyfunction]
fn color_from_hex(value: &str) -> PyResult<PyColor> {
    Ok(PyColor {
        inner: parse_hex(value)?,
    })
}

#[pyfunction]
fn color_to_hsl(color: PyColor) -> (f32, f32, f32) {
    let hsl: Hsl = color_to_srgb_components(color.inner).into_color();
    (hsl.hue.into_degrees(), hsl.saturation, hsl.lightness)
}

#[pyfunction]
fn color_to_srgb(color: PyColor) -> (f32, f32, f32) {
    let srgb = color_to_srgb_components(color.inner);
    (srgb.red, srgb.green, srgb.blue)
}

#[pyfunction]
#[pyo3(signature = (a, b, t, space="rgb"))]
fn interpolate_colors(a: PyColor, b: PyColor, t: f32, space: &str) -> PyResult<PyColor> {
    let t = t.clamp(0.0, 1.0);
    let mixed = match space.to_ascii_lowercase().as_str() {
        "hsl" => {
            let ha: Hsl = color_to_srgb_components(a.inner).into_color();
            let hb: Hsl = color_to_srgb_components(b.inner).into_color();
            ha.mix(hb, t).into_color()
        }
        "rgb" => color_to_srgb_components(a.inner).mix(color_to_srgb_components(b.inner), t),
        other => {
            return Err(PyValueError::new_err(format!(
                "unsupported color space: {other} (expected 'rgb' or 'hsl')"
            )));
        }
    };
    Ok(PyColor {
        inner: Color::Rgb(
            (mixed.red * 255.0).round() as u8,
            (mixed.green * 255.0).round() as u8,
            (mixed.blue * 255.0).round() as u8,
        ),
    })
}

#[pyfunction]
fn color_lerp(a: PyColor, b: PyColor, t: f32) -> PyColor {
    let t = t.clamp(0.0, 1.0);
    let mixed = color_to_srgb_components(a.inner).mix(color_to_srgb_components(b.inner), t);
    PyColor {
        inner: Color::Rgb(
            (mixed.red * 255.0).round() as u8,
            (mixed.green * 255.0).round() as u8,
            (mixed.blue * 255.0).round() as u8,
        ),
    }
}

#[pyfunction]
fn tailwind_color(name: &str, shade: u16) -> PyResult<PyColor> {
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
        "black" => {
            return Ok(PyColor {
                inner: tailwind::BLACK,
            })
        }
        "white" => {
            return Ok(PyColor {
                inner: tailwind::WHITE,
            })
        }
        other => {
            return Err(PyValueError::new_err(format!(
                "unknown tailwind palette: {other}"
            )));
        }
    };
    let color = match shade {
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
            return Err(PyValueError::new_err(format!(
                "invalid tailwind shade: {shade}"
            )));
        }
    };
    Ok(PyColor { inner: color })
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(color_from_hsl, m)?)?;
    m.add_function(wrap_pyfunction!(color_from_hex, m)?)?;
    m.add_function(wrap_pyfunction!(color_to_hsl, m)?)?;
    m.add_function(wrap_pyfunction!(color_to_srgb, m)?)?;
    m.add_function(wrap_pyfunction!(interpolate_colors, m)?)?;
    m.add_function(wrap_pyfunction!(color_lerp, m)?)?;
    m.add_function(wrap_pyfunction!(tailwind_color, m)?)?;
    Ok(())
}
