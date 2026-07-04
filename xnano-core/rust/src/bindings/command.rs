use crossterm::style::{
    Attribute, Color, ContentStyle, Print, PrintStyledContent, ResetColor, SetAttribute,
    SetBackgroundColor, SetForegroundColor,
};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use super::crossterm_exec::{execute_stdout, flush_stdout};

#[pyclass(name = "ConsoleColor", module = "xnano_core.rust.native", eq, eq_int)]
#[derive(Clone, Copy, PartialEq, Debug)]
pub enum PyConsoleColor {
    Reset,
    Black,
    DarkGrey,
    Red,
    DarkRed,
    Green,
    DarkGreen,
    Yellow,
    DarkYellow,
    Blue,
    DarkBlue,
    Magenta,
    DarkMagenta,
    Cyan,
    DarkCyan,
    White,
    Grey,
    AnsiValue,
    Rgb,
}

fn parse_console_color(
    color: PyConsoleColor,
    ansi_value: Option<u8>,
    rgb: Option<(u8, u8, u8)>,
) -> PyResult<Color> {
    match color {
        PyConsoleColor::Reset => Ok(Color::Reset),
        PyConsoleColor::Black => Ok(Color::Black),
        PyConsoleColor::DarkGrey => Ok(Color::DarkGrey),
        PyConsoleColor::Red => Ok(Color::Red),
        PyConsoleColor::DarkRed => Ok(Color::DarkRed),
        PyConsoleColor::Green => Ok(Color::Green),
        PyConsoleColor::DarkGreen => Ok(Color::DarkGreen),
        PyConsoleColor::Yellow => Ok(Color::Yellow),
        PyConsoleColor::DarkYellow => Ok(Color::DarkYellow),
        PyConsoleColor::Blue => Ok(Color::Blue),
        PyConsoleColor::DarkBlue => Ok(Color::DarkBlue),
        PyConsoleColor::Magenta => Ok(Color::Magenta),
        PyConsoleColor::DarkMagenta => Ok(Color::DarkMagenta),
        PyConsoleColor::Cyan => Ok(Color::Cyan),
        PyConsoleColor::DarkCyan => Ok(Color::DarkCyan),
        PyConsoleColor::White => Ok(Color::White),
        PyConsoleColor::Grey => Ok(Color::Grey),
        PyConsoleColor::AnsiValue => ansi_value
            .map(Color::AnsiValue)
            .ok_or_else(|| PyValueError::new_err("ansi_value is required for ConsoleColor.AnsiValue")),
        PyConsoleColor::Rgb => rgb
            .map(|(r, g, b)| Color::Rgb { r, g, b })
            .ok_or_else(|| PyValueError::new_err("rgb values are required for ConsoleColor.Rgb")),
    }
}

#[pyclass(name = "ConsoleAttribute", module = "xnano_core.rust.native", eq, eq_int)]
#[derive(Clone, Copy, PartialEq, Debug)]
pub enum PyAttribute {
    Reset,
    Bold,
    Dim,
    Italic,
    Underlined,
    DoubleUnderlined,
    Undercurled,
    Underdotted,
    Underdashed,
    SlowBlink,
    RapidBlink,
    Reverse,
    Hidden,
    CrossedOut,
    Fraktur,
    NoBold,
    NormalIntensity,
    NoItalic,
    NoUnderline,
    NoBlink,
    NoReverse,
    NoHidden,
    NotCrossedOut,
    Framed,
    Encircled,
    OverLined,
    NotFramedOrEncircled,
    NotOverLined,
}

impl From<PyAttribute> for Attribute {
    fn from(value: PyAttribute) -> Self {
        match value {
            PyAttribute::Reset => Attribute::Reset,
            PyAttribute::Bold => Attribute::Bold,
            PyAttribute::Dim => Attribute::Dim,
            PyAttribute::Italic => Attribute::Italic,
            PyAttribute::Underlined => Attribute::Underlined,
            PyAttribute::DoubleUnderlined => Attribute::DoubleUnderlined,
            PyAttribute::Undercurled => Attribute::Undercurled,
            PyAttribute::Underdotted => Attribute::Underdotted,
            PyAttribute::Underdashed => Attribute::Underdashed,
            PyAttribute::SlowBlink => Attribute::SlowBlink,
            PyAttribute::RapidBlink => Attribute::RapidBlink,
            PyAttribute::Reverse => Attribute::Reverse,
            PyAttribute::Hidden => Attribute::Hidden,
            PyAttribute::CrossedOut => Attribute::CrossedOut,
            PyAttribute::Fraktur => Attribute::Fraktur,
            PyAttribute::NoBold => Attribute::NoBold,
            PyAttribute::NormalIntensity => Attribute::NormalIntensity,
            PyAttribute::NoItalic => Attribute::NoItalic,
            PyAttribute::NoUnderline => Attribute::NoUnderline,
            PyAttribute::NoBlink => Attribute::NoBlink,
            PyAttribute::NoReverse => Attribute::NoReverse,
            PyAttribute::NoHidden => Attribute::NoHidden,
            PyAttribute::NotCrossedOut => Attribute::NotCrossedOut,
            PyAttribute::Framed => Attribute::Framed,
            PyAttribute::Encircled => Attribute::Encircled,
            PyAttribute::OverLined => Attribute::OverLined,
            PyAttribute::NotFramedOrEncircled => Attribute::NotFramedOrEncircled,
            PyAttribute::NotOverLined => Attribute::NotOverLined,
        }
    }
}

#[pyfunction]
#[pyo3(signature = (color, *, ansi_value=None, rgb=None))]
fn set_foreground_color(
    color: PyConsoleColor,
    ansi_value: Option<u8>,
    rgb: Option<(u8, u8, u8)>,
) -> PyResult<()> {
    execute_stdout(SetForegroundColor(parse_console_color(color, ansi_value, rgb)?))
}

#[pyfunction]
#[pyo3(signature = (color, *, ansi_value=None, rgb=None))]
fn set_background_color(
    color: PyConsoleColor,
    ansi_value: Option<u8>,
    rgb: Option<(u8, u8, u8)>,
) -> PyResult<()> {
    execute_stdout(SetBackgroundColor(parse_console_color(color, ansi_value, rgb)?))
}

#[pyfunction]
fn reset_color() -> PyResult<()> {
    execute_stdout(ResetColor)
}

#[pyfunction]
fn set_attribute(attribute: PyAttribute) -> PyResult<()> {
    execute_stdout(SetAttribute(attribute.into()))
}

#[pyfunction]
#[pyo3(signature = (text, *, foreground=None, background=None, attribute=None, foreground_ansi=None, background_ansi=None, foreground_rgb=None, background_rgb=None))]
fn print_styled_content(
    text: String,
    foreground: Option<PyConsoleColor>,
    background: Option<PyConsoleColor>,
    attribute: Option<PyAttribute>,
    foreground_ansi: Option<u8>,
    background_ansi: Option<u8>,
    foreground_rgb: Option<(u8, u8, u8)>,
    background_rgb: Option<(u8, u8, u8)>,
) -> PyResult<()> {
    let mut style = ContentStyle::new();
    if let Some(fg) = foreground {
        style.foreground_color = Some(parse_console_color(fg, foreground_ansi, foreground_rgb)?);
    }
    if let Some(bg) = background {
        style.background_color = Some(parse_console_color(bg, background_ansi, background_rgb)?);
    }
    if let Some(attr) = attribute {
        let attribute: Attribute = attr.into();
        style.attributes = crossterm::style::Attributes::from(attribute);
    }
    execute_stdout(PrintStyledContent(style.apply(text)))
}

#[pyfunction]
fn print_text(text: String) -> PyResult<()> {
    execute_stdout(Print(text))
}

#[pyfunction]
fn flush_stdout_buffer() -> PyResult<()> {
    flush_stdout()
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyConsoleColor>()?;
    m.add_class::<PyAttribute>()?;
    m.add_function(wrap_pyfunction!(set_foreground_color, m)?)?;
    m.add_function(wrap_pyfunction!(set_background_color, m)?)?;
    m.add_function(wrap_pyfunction!(reset_color, m)?)?;
    m.add_function(wrap_pyfunction!(set_attribute, m)?)?;
    m.add_function(wrap_pyfunction!(print_styled_content, m)?)?;
    m.add_function(wrap_pyfunction!(print_text, m)?)?;
    m.add_function(wrap_pyfunction!(flush_stdout_buffer, m)?)?;
    Ok(())
}