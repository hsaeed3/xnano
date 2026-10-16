//! `Color` and `Style`.

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyFrozenSet, PyString, PyTuple};
use tachyonfx::{
    ColorSpace, ToRgbComponents, color_from_hsl, color_from_hsv, color_to_hsl, color_to_hsv,
};
use xnano_terminal_runtime::style::{
    Color, Modifier, Style, describe_color, modifier_from_name, modifier_names, parse_color,
    tailwind_color, to_rgb,
};

#[pyclass(
    name = "Color",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct PyColor {
    pub inner: Color,
}

/// Read a color from a `Color`, a color name or hex string, or an `(r, g, b)` tuple.
pub fn color_arg(value: &Bound<'_, PyAny>) -> PyResult<Color> {
    if let Ok(color) = value.extract::<PyColor>() {
        return Ok(color.inner);
    }
    if let Ok(text) = value.cast::<PyString>() {
        return parse_color(&text.to_cow()?).map_err(PyValueError::new_err);
    }
    if let Ok(channels) = value.extract::<(i64, i64, i64)>() {
        let check = |channel: i64| {
            u8::try_from(channel).map_err(|_| {
                PyValueError::new_err(format!(
                    "the color channel {channel} is out of range; use whole numbers from 0 to 255"
                ))
            })
        };
        return Ok(Color::Rgb(
            check(channels.0)?,
            check(channels.1)?,
            check(channels.2)?,
        ));
    }
    Err(PyTypeError::new_err(format!(
        "a color must be a Color, a name such as \"red\", a hex string such as \"#ff8800\", or an \
         (r, g, b) tuple, not {}",
        value.get_type().name()?
    )))
}

fn check_hsl(third: &str, hue: f32, saturation: f32, lightness: f32) -> PyResult<()> {
    if !hue.is_finite() || !(0.0..=360.0).contains(&hue) {
        return Err(PyValueError::new_err(format!(
            "the hue {hue} is out of range; use degrees from 0 to 360"
        )));
    }
    for (name, value) in [("saturation", saturation), (third, lightness)] {
        if !value.is_finite() || !(0.0..=100.0).contains(&value) {
            return Err(PyValueError::new_err(format!(
                "the {name} {value} is out of range; use a percentage from 0 to 100"
            )));
        }
    }
    Ok(())
}

/// Colors that have a known RGB value: true colors, palette entries and the named colors.
fn convertible(color: Color) -> PyResult<()> {
    if color == Color::Reset {
        return Err(PyValueError::new_err(
            "the reset color follows the terminal's theme, so it has no fixed value to convert; use a named, indexed or true color",
        ));
    }
    let _ = color.to_rgb();
    Ok(())
}

fn color_space_arg(name: &str) -> PyResult<ColorSpace> {
    Ok(match name {
        "rgb" => ColorSpace::Rgb,
        "hsl" => ColorSpace::Hsl,
        "hsv" => ColorSpace::Hsv,
        other => {
            return Err(PyValueError::new_err(format!(
                "\"{other}\" is not a color space; use \"rgb\", \"hsl\" or \"hsv\""
            )));
        }
    })
}

#[pymethods]
impl PyColor {
    #[new]
    fn new(value: &Bound<'_, PyAny>) -> PyResult<Self> {
        Ok(Self {
            inner: color_arg(value)?,
        })
    }

    #[classmethod]
    fn parse(_cls: &Bound<'_, pyo3::types::PyType>, value: &str) -> PyResult<Self> {
        Ok(Self {
            inner: parse_color(value).map_err(PyValueError::new_err)?,
        })
    }

    #[classmethod]
    fn from_tailwind(
        _cls: &Bound<'_, pyo3::types::PyType>,
        palette: &str,
        shade: i64,
    ) -> PyResult<Self> {
        let shade = u16::try_from(shade).map_err(|_| {
            PyValueError::new_err(format!(
                "the Tailwind shade {shade} is out of range; use 50, 100, 200 through 900, or 950"
            ))
        })?;
        Ok(Self {
            inner: tailwind_color(palette, shade).map_err(PyValueError::new_err)?,
        })
    }

    #[classmethod]
    fn indexed(_cls: &Bound<'_, pyo3::types::PyType>, index: i64) -> PyResult<Self> {
        let index = u8::try_from(index).map_err(|_| {
            PyValueError::new_err(format!(
                "the palette index {index} is out of range; use 0 to 255"
            ))
        })?;
        Ok(Self {
            inner: Color::Indexed(index),
        })
    }

    #[classmethod]
    fn from_rgb(
        _cls: &Bound<'_, pyo3::types::PyType>,
        red: i64,
        green: i64,
        blue: i64,
    ) -> PyResult<Self> {
        Ok(Self {
            inner: color_arg(&(red, green, blue).into_pyobject(_cls.py())?.into_any())?,
        })
    }

    #[classattr]
    fn black() -> Self {
        Self {
            inner: Color::Black,
        }
    }

    #[classattr]
    fn red() -> Self {
        Self { inner: Color::Red }
    }

    #[classattr]
    fn green() -> Self {
        Self {
            inner: Color::Green,
        }
    }

    #[classattr]
    fn yellow() -> Self {
        Self {
            inner: Color::Yellow,
        }
    }

    #[classattr]
    fn blue() -> Self {
        Self { inner: Color::Blue }
    }

    #[classattr]
    fn magenta() -> Self {
        Self {
            inner: Color::Magenta,
        }
    }

    #[classattr]
    fn cyan() -> Self {
        Self { inner: Color::Cyan }
    }

    #[classattr]
    fn gray() -> Self {
        Self { inner: Color::Gray }
    }

    #[classattr]
    fn dark_gray() -> Self {
        Self {
            inner: Color::DarkGray,
        }
    }

    #[classattr]
    fn light_red() -> Self {
        Self {
            inner: Color::LightRed,
        }
    }

    #[classattr]
    fn light_green() -> Self {
        Self {
            inner: Color::LightGreen,
        }
    }

    #[classattr]
    fn light_yellow() -> Self {
        Self {
            inner: Color::LightYellow,
        }
    }

    #[classattr]
    fn light_blue() -> Self {
        Self {
            inner: Color::LightBlue,
        }
    }

    #[classattr]
    fn light_magenta() -> Self {
        Self {
            inner: Color::LightMagenta,
        }
    }

    #[classattr]
    fn light_cyan() -> Self {
        Self {
            inner: Color::LightCyan,
        }
    }

    #[classattr]
    fn white() -> Self {
        Self {
            inner: Color::White,
        }
    }

    #[classattr]
    fn reset() -> Self {
        Self {
            inner: Color::Reset,
        }
    }

    /// A true color from hue (degrees), saturation and lightness (percent).
    #[classmethod]
    fn from_hsl(
        _cls: &Bound<'_, pyo3::types::PyType>,
        hue: f32,
        saturation: f32,
        lightness: f32,
    ) -> PyResult<Self> {
        check_hsl("lightness", hue, saturation, lightness)?;
        Ok(Self {
            inner: color_from_hsl(hue, saturation, lightness),
        })
    }

    /// A true color from hue (degrees), saturation and value (percent).
    #[classmethod]
    fn from_hsv(
        _cls: &Bound<'_, pyo3::types::PyType>,
        hue: f32,
        saturation: f32,
        value: f32,
    ) -> PyResult<Self> {
        check_hsl("value", hue, saturation, value)?;
        Ok(Self {
            inner: color_from_hsv(hue, saturation, value),
        })
    }

    /// Hue (degrees), saturation and lightness (percent); named colors use their standard values.
    #[allow(clippy::wrong_self_convention)]
    fn to_hsl(&self) -> PyResult<(f32, f32, f32)> {
        convertible(self.inner)?;
        Ok(color_to_hsl(&self.inner))
    }

    #[allow(clippy::wrong_self_convention)]
    fn to_hsv(&self) -> PyResult<(f32, f32, f32)> {
        convertible(self.inner)?;
        Ok(color_to_hsv(&self.inner))
    }

    /// The color between this one and ``other``; ``ratio`` 0.0 is this color and 1.0 is ``other``.
    #[pyo3(signature = (other, ratio, *, color_space = "hsl"))]
    fn lerp(&self, other: &Bound<'_, PyAny>, ratio: f32, color_space: &str) -> PyResult<Self> {
        let target = color_arg(other)?;
        convertible(self.inner)?;
        convertible(target)?;
        Ok(Self {
            inner: color_space_arg(color_space)?.lerp(&self.inner, &target, ratio),
        })
    }

    /// Lighten (positive) or darken (negative) by a fraction from -1.0 to 1.0.
    #[pyo3(signature = (amount, *, color_space = "hsl"))]
    fn lighten(&self, amount: f32, color_space: &str) -> PyResult<Self> {
        convertible(self.inner)?;
        Ok(Self {
            inner: color_space_arg(color_space)?.lighten(&self.inner, amount.clamp(-1.0, 1.0)),
        })
    }

    /// Darken by a fraction from 0.0 to 1.0.
    #[pyo3(signature = (amount, *, color_space = "hsl"))]
    fn darken(&self, amount: f32, color_space: &str) -> PyResult<Self> {
        if !amount.is_finite() || !(0.0..=1.0).contains(&amount) {
            return Err(PyValueError::new_err(format!(
                "Color.darken needs an amount from 0.0 to 1.0, not {amount}; use Color.lighten to make a color lighter"
            )));
        }
        convertible(self.inner)?;
        Ok(Self {
            inner: color_space_arg(color_space)?.lighten(&self.inner, -amount),
        })
    }

    /// The color that has each red, green and blue channel inverted.
    #[allow(clippy::trivially_copy_pass_by_ref)]
    fn inverse(&self) -> PyResult<Self> {
        if self.inner == Color::Reset {
            return Err(PyValueError::new_err(
                "Color.reset has no fixed value, so it cannot be inverted.",
            ));
        }
        let (red, green, blue) = self.inner.to_rgb();
        Ok(Self {
            inner: Color::Rgb(255 - red, 255 - green, 255 - blue),
        })
    }

    /// Scale saturation: 0.0 removes it, 1.0 keeps it, more than 1.0 boosts it.
    #[pyo3(signature = (factor, *, color_space = "hsl"))]
    fn saturate(&self, factor: f32, color_space: &str) -> PyResult<Self> {
        convertible(self.inner)?;
        Ok(Self {
            inner: color_space_arg(color_space)?.saturate(&self.inner, factor.max(0.0)),
        })
    }

    #[getter]
    fn is_reset(&self) -> bool {
        self.inner == Color::Reset
    }

    fn __copy__(&self) -> Self {
        *self
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        *self
    }

    #[allow(clippy::trivially_copy_pass_by_ref, clippy::wrong_self_convention)]
    fn to_rgb(&self) -> Option<(u8, u8, u8)> {
        to_rgb(self.inner)
    }

    /// The color as ``#rrggbb``; only true colors have one.
    #[allow(clippy::wrong_self_convention)]
    fn to_hex(&self) -> PyResult<String> {
        let (red, green, blue) = to_rgb(self.inner).ok_or_else(|| {
            PyValueError::new_err(
                "only a true color has a fixed #rrggbb value; a named or indexed color is chosen by the terminal's theme, so pass a color such as \"#ff8800\" or an (r, g, b) tuple",
            )
        })?;
        Ok(format!("#{red:02x}{green:02x}{blue:02x}"))
    }

    fn __repr__(&self) -> String {
        format!("Color('{}')", describe_color(self.inner))
    }
}

#[pyclass(
    name = "Style",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct PyStyle {
    pub inner: Style,
}

/// Read an optional style argument.
pub fn style_arg(value: Option<&Bound<'_, PyAny>>) -> PyResult<Style> {
    match value {
        None => Ok(Style::default()),
        Some(value) if value.is_none() => Ok(Style::default()),
        Some(value) => Ok(value.extract::<PyStyle>()?.inner),
    }
}

#[pymethods]
impl PyStyle {
    #[new]
    #[pyo3(signature = (foreground = None, background = None, *, bold = false, dim = false, italic = false,
        underline = false, blink = false, rapid_blink = false, reverse = false, hidden = false,
        crossed_out = false, underline_color = None))]
    fn new(
        foreground: Option<&Bound<'_, PyAny>>,
        background: Option<&Bound<'_, PyAny>>,
        bold: bool,
        dim: bool,
        italic: bool,
        underline: bool,
        blink: bool,
        rapid_blink: bool,
        reverse: bool,
        hidden: bool,
        crossed_out: bool,
        underline_color: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        let mut style = Style::default();
        if let Some(color) = foreground.filter(|value| !value.is_none()) {
            style = style.fg(color_arg(color)?);
        }
        if let Some(color) = background.filter(|value| !value.is_none()) {
            style = style.bg(color_arg(color)?);
        }
        if let Some(color) = underline_color.filter(|value| !value.is_none()) {
            style = style.underline_color(color_arg(color)?);
        }
        for (flag, name) in [
            (bold, "bold"),
            (dim, "dim"),
            (italic, "italic"),
            (underline, "underline"),
            (blink, "blink"),
            (rapid_blink, "rapid_blink"),
            (reverse, "reverse"),
            (hidden, "hidden"),
            (crossed_out, "crossed_out"),
        ] {
            if flag {
                style = style.add_modifier(modifier_from_name(name).unwrap_or(Modifier::empty()));
            }
        }
        Ok(Self { inner: style })
    }

    /// A style that resets every color and modifier.
    #[classmethod]
    fn reset(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self {
            inner: Style::reset(),
        }
    }

    #[getter]
    fn foreground(&self) -> Option<PyColor> {
        self.inner.fg.map(|inner| PyColor { inner })
    }

    #[getter]
    fn background(&self) -> Option<PyColor> {
        self.inner.bg.map(|inner| PyColor { inner })
    }

    #[getter]
    fn underline_color(&self) -> Option<PyColor> {
        self.inner.underline_color.map(|inner| PyColor { inner })
    }

    /// The modifiers this style turns on.
    #[getter]
    fn modifiers<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyFrozenSet>> {
        PyFrozenSet::new(py, modifier_names(self.inner.add_modifier))
    }

    /// The modifiers this style turns off.
    #[getter]
    fn removed_modifiers<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyFrozenSet>> {
        PyFrozenSet::new(py, modifier_names(self.inner.sub_modifier))
    }

    /// A copy with a new text color (``None`` clears it).
    fn with_foreground(&self, color: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let mut style = self.inner;
        style.fg = color
            .filter(|value| !value.is_none())
            .map(color_arg)
            .transpose()?;
        Ok(Self { inner: style })
    }

    /// A copy with a new background color (``None`` clears it).
    fn with_background(&self, color: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let mut style = self.inner;
        style.bg = color
            .filter(|value| !value.is_none())
            .map(color_arg)
            .transpose()?;
        Ok(Self { inner: style })
    }

    /// A copy with a new underline color (``None`` clears it).
    fn with_underline_color(&self, color: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let mut style = self.inner;
        style.underline_color = color
            .filter(|value| !value.is_none())
            .map(color_arg)
            .transpose()?;
        Ok(Self { inner: style })
    }

    /// A copy that also turns on the named modifiers.
    #[pyo3(signature = (*names))]
    fn add_modifier(&self, names: &Bound<'_, PyTuple>) -> PyResult<Self> {
        let modifiers = modifiers_arg(names.as_any())?;
        Ok(Self {
            inner: self.inner.add_modifier(modifiers),
        })
    }

    /// A copy that turns the named modifiers off, even when another style turns them on.
    #[pyo3(signature = (*names))]
    fn remove_modifier(&self, names: &Bound<'_, PyTuple>) -> PyResult<Self> {
        let modifiers = modifiers_arg(names.as_any())?;
        Ok(Self {
            inner: self.inner.remove_modifier(modifiers),
        })
    }

    fn patch(&self, other: &Self) -> Self {
        Self {
            inner: self.inner.patch(other.inner),
        }
    }

    /// ``a | b`` patches ``a`` with ``b``.
    fn __or__(&self, other: &Self) -> Self {
        self.patch(other)
    }

    fn __bool__(&self) -> bool {
        self.inner != Style::default()
    }

    fn __copy__(&self) -> Self {
        *self
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        *self
    }

    fn __repr__(&self) -> String {
        style_repr(&self.inner)
    }
}

/// The constructor-like text of a style, for `repr`.
pub fn style_repr(style: &Style) -> String {
    let mut parts = Vec::new();
    if let Some(color) = style.fg {
        parts.push(format!("foreground='{}'", describe_color(color)));
    }
    if let Some(color) = style.bg {
        parts.push(format!("background='{}'", describe_color(color)));
    }
    if let Some(color) = style.underline_color {
        parts.push(format!("underline_color='{}'", describe_color(color)));
    }
    for name in modifier_names(style.add_modifier) {
        parts.push(format!("{name}=True"));
    }
    let removed: Vec<String> = modifier_names(style.sub_modifier)
        .into_iter()
        .map(|name| format!("'{name}'"))
        .collect();
    let base = format!("Style({})", parts.join(", "));
    if removed.is_empty() {
        base
    } else {
        format!("{base}.remove_modifier({})", removed.join(", "))
    }
}

/// A tuple of modifier names for a `Cell` constructor argument.
pub fn modifiers_arg(value: &Bound<'_, PyAny>) -> PyResult<Modifier> {
    let mut result = Modifier::empty();
    for item in value.try_iter()? {
        let name: String = item?.extract()?;
        result |= modifier_from_name(&name).ok_or_else(|| {
            PyValueError::new_err(format!(
                "\"{name}\" is not a modifier; use bold, dim, italic, underline, blink, reverse, \
                 hidden or crossed_out"
            ))
        })?;
    }
    Ok(result)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyColor>()?;
    m.add_class::<PyStyle>()?;
    let _ = PyTuple::empty(m.py());
    Ok(())
}
