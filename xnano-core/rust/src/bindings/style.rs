use palette::Hsl;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use ratatui::style::{Color, Modifier, Style};
use std::str::FromStr;

#[pyclass(name = "Color", module = "xnano_core.rust.native", from_py_object)]
#[derive(Clone, Copy)]
pub struct PyColor {
    pub inner: Color,
}

impl From<Color> for PyColor {
    fn from(value: Color) -> Self {
        Self { inner: value }
    }
}

#[pymethods]
impl PyColor {
    #[classattr]
    const RESET: Self = Self { inner: Color::Reset };
    #[classattr]
    const BLACK: Self = Self { inner: Color::Black };
    #[classattr]
    const RED: Self = Self { inner: Color::Red };
    #[classattr]
    const GREEN: Self = Self { inner: Color::Green };
    #[classattr]
    const YELLOW: Self = Self { inner: Color::Yellow };
    #[classattr]
    const BLUE: Self = Self { inner: Color::Blue };
    #[classattr]
    const MAGENTA: Self = Self { inner: Color::Magenta };
    #[classattr]
    const CYAN: Self = Self { inner: Color::Cyan };
    #[classattr]
    const GRAY: Self = Self { inner: Color::Gray };
    #[classattr]
    const DARK_GRAY: Self = Self { inner: Color::DarkGray };
    #[classattr]
    const LIGHT_RED: Self = Self { inner: Color::LightRed };
    #[classattr]
    const LIGHT_GREEN: Self = Self { inner: Color::LightGreen };
    #[classattr]
    const LIGHT_YELLOW: Self = Self { inner: Color::LightYellow };
    #[classattr]
    const LIGHT_BLUE: Self = Self { inner: Color::LightBlue };
    #[classattr]
    const LIGHT_MAGENTA: Self = Self { inner: Color::LightMagenta };
    #[classattr]
    const LIGHT_CYAN: Self = Self { inner: Color::LightCyan };
    #[classattr]
    const WHITE: Self = Self { inner: Color::White };

    #[staticmethod]
    fn parse(value: &str) -> PyResult<Self> {
        Color::from_str(value)
            .map(Self::from)
            .map_err(|err| PyValueError::new_err(err.to_string()))
    }

    #[staticmethod]
    fn indexed(value: u8) -> Self {
        Self {
            inner: Color::Indexed(value),
        }
    }

    #[staticmethod]
    fn rgb(r: u8, g: u8, b: u8) -> Self {
        Self {
            inner: Color::Rgb(r, g, b),
        }
    }

    #[staticmethod]
    fn from_u32(value: u32) -> Self {
        Self {
            inner: Color::from_u32(value),
        }
    }

    #[staticmethod]
    fn from_hsl(h: f32, s: f32, l: f32) -> Self {
        Self {
            inner: Color::from_hsl(Hsl::new(h, s, l)),
        }
    }

    fn to_u32(&self) -> u32 {
        match self.inner {
            Color::Rgb(r, g, b) => u32::from(r) << 16 | u32::from(g) << 8 | u32::from(b),
            Color::Indexed(value) => u32::from(value),
            _ => 0,
        }
    }

    fn __repr__(&self) -> String {
        format!("{self:?}", self = self.inner)
    }

    fn __eq__(&self, other: &Self) -> bool {
        self.inner == other.inner
    }

    fn __hash__(&self) -> isize {
        format!("{self:?}", self = self.inner)
            .bytes()
            .fold(0isize, |acc, b| acc.wrapping_mul(31).wrapping_add(b as isize))
    }
}

#[pyclass(name = "Modifier", module = "xnano_core.rust.native", from_py_object)]
#[derive(Clone, Copy)]
pub struct PyModifier {
    pub inner: Modifier,
}

#[pymethods]
impl PyModifier {
    #[classattr]
    const BOLD: Self = Self {
        inner: Modifier::BOLD,
    };
    #[classattr]
    const DIM: Self = Self {
        inner: Modifier::DIM,
    };
    #[classattr]
    const ITALIC: Self = Self {
        inner: Modifier::ITALIC,
    };
    #[classattr]
    const UNDERLINED: Self = Self {
        inner: Modifier::UNDERLINED,
    };
    #[classattr]
    const SLOW_BLINK: Self = Self {
        inner: Modifier::SLOW_BLINK,
    };
    #[classattr]
    const RAPID_BLINK: Self = Self {
        inner: Modifier::RAPID_BLINK,
    };
    #[classattr]
    const REVERSED: Self = Self {
        inner: Modifier::REVERSED,
    };
    #[classattr]
    const HIDDEN: Self = Self {
        inner: Modifier::HIDDEN,
    };
    #[classattr]
    const CROSSED_OUT: Self = Self {
        inner: Modifier::CROSSED_OUT,
    };
    #[classattr]
    const EMPTY: Self = Self {
        inner: Modifier::empty(),
    };

    fn __or__(&self, other: Self) -> Self {
        Self {
            inner: self.inner | other.inner,
        }
    }

    fn __and__(&self, other: Self) -> Self {
        Self {
            inner: self.inner & other.inner,
        }
    }

    fn contains(&self, other: Self) -> bool {
        self.inner.contains(other.inner)
    }

    fn intersection(&self, other: Self) -> Self {
        Self {
            inner: self.inner.intersection(other.inner),
        }
    }

    fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    fn __repr__(&self) -> String {
        format!("{self:?}", self = self.inner)
    }
}

#[pyclass(name = "Style", module = "xnano_core.rust.native", from_py_object)]
#[derive(Clone, Copy)]
pub struct PyStyle {
    pub inner: Style,
}

#[pymethods]
impl PyStyle {
    #[staticmethod]
    fn default() -> Self {
        Self {
            inner: Style::default(),
        }
    }

    #[staticmethod]
    fn new() -> Self {
        Self {
            inner: Style::new(),
        }
    }

    #[staticmethod]
    fn reset() -> Self {
        Self {
            inner: Style::reset(),
        }
    }

    fn fg(&self, color: PyColor) -> Self {
        Self {
            inner: self.inner.fg(color.inner),
        }
    }

    fn bg(&self, color: PyColor) -> Self {
        Self {
            inner: self.inner.bg(color.inner),
        }
    }

    fn add_modifier(&self, modifier: PyModifier) -> Self {
        Self {
            inner: self.inner.add_modifier(modifier.inner),
        }
    }

    fn remove_modifier(&self, modifier: PyModifier) -> Self {
        Self {
            inner: self.inner.remove_modifier(modifier.inner),
        }
    }

    fn patch(&self, other: Self) -> Self {
        Self {
            inner: self.inner.patch(other.inner),
        }
    }

    fn get_fg(&self) -> Option<PyColor> {
        self.inner.fg.map(PyColor::from)
    }

    fn get_bg(&self) -> Option<PyColor> {
        self.inner.bg.map(PyColor::from)
    }

    fn get_modifiers(&self) -> PyModifier {
        PyModifier {
            inner: self.inner.add_modifier,
        }
    }

    fn get_sub_modifiers(&self) -> PyModifier {
        PyModifier {
            inner: self.inner.sub_modifier,
        }
    }

    #[cfg(feature = "terminal")]
    fn underline_color(&self, color: PyColor) -> Self {
        Self {
            inner: self.inner.underline_color(color.inner),
        }
    }

    #[cfg(feature = "terminal")]
    fn get_underline_color(&self) -> Option<PyColor> {
        self.inner.underline_color.map(PyColor::from)
    }

    fn __repr__(&self) -> String {
        format!("{self:?}", self = self.inner)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyColor>()?;
    m.add_class::<PyModifier>()?;
    m.add_class::<PyStyle>()?;
    Ok(())
}
