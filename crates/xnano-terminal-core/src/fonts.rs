//! Fonts made of characters or pixels, text written in them, and frames drawn as PNG images.

use std::path::PathBuf;
use std::sync::Arc;

use pyo3::exceptions::{PyOSError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use xnano_terminal_pixels::{Font, FontError};
use xnano_terminal_runtime::geometry::Size;

use crate::geometry::PySize;

fn font_error(error: FontError) -> PyErr {
    PyValueError::new_err(error.to_string())
}

/// A font, as Python sees it: a FIGlet character font or a pixel font.
#[pyclass(name = "Font", module = "xnano_core._xnano_core", frozen)]
pub struct PyFont {
    pub inner: Arc<Font>,
}

#[pymethods]
impl PyFont {
    #[new]
    #[pyo3(signature = (name = "small"))]
    fn new(name: &str) -> PyResult<Self> {
        Ok(Self {
            inner: Font::builtin(name).map_err(font_error)?,
        })
    }

    #[staticmethod]
    fn from_file(path: PathBuf) -> PyResult<Self> {
        let shown = path.display().to_string();
        let data = std::fs::read(&path).map_err(|error| {
            PyOSError::new_err(format!(
                "The font file \"{shown}\" could not be read: {error}. Check the path, or load \
                 the font from bytes with Font.from_bytes(data)."
            ))
        })?;
        let name = path
            .file_stem()
            .map_or_else(|| shown.clone(), |stem| stem.to_string_lossy().into_owned());
        let font = Font::parse(&data, &name).map_err(font_error)?;
        Ok(Self {
            inner: Arc::new(font),
        })
    }

    #[staticmethod]
    #[pyo3(signature = (data, *, name = "font"))]
    fn from_bytes(data: &[u8], name: &str) -> PyResult<Self> {
        Ok(Self {
            inner: Arc::new(Font::parse(data, name).map_err(font_error)?),
        })
    }

    #[getter]
    fn name(&self) -> String {
        self.inner.name().to_owned()
    }

    #[getter]
    fn kind(&self) -> &'static str {
        self.inner.kind().name()
    }

    #[getter]
    fn glyph_size(&self) -> PySize {
        let (width, height) = self.inner.glyph_size();
        PySize {
            inner: Size::new(width as i32, height as i32),
        }
    }

    fn has_character(&self, character: &str) -> PyResult<bool> {
        let mut characters = character.chars();
        match (characters.next(), characters.next()) {
            (Some(single), None) => Ok(self.inner.has_character(single)),
            _ => Err(PyValueError::new_err(format!(
                "has_character() takes one character, but got {character:?}. Check each \
                 character on its own."
            ))),
        }
    }

    fn render(&self, text: &str) -> String {
        xnano_terminal_pixels::render_text(&self.inner, text).join("\n")
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other
            .cast::<Self>()
            .is_ok_and(|other| Arc::ptr_eq(&self.inner, &other.get().inner))
    }

    fn __hash__(&self) -> u64 {
        Arc::as_ptr(&self.inner) as usize as u64
    }

    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(slf.as_any(), &["name", "kind", "glyph_size"])
    }
}

/// Read a `font=` argument: a [`PyFont`], the name of a built-in font, or `None`.
pub fn font_arg(value: Option<&Bound<'_, PyAny>>) -> PyResult<Option<Arc<Font>>> {
    let Some(value) = value.filter(|value| !value.is_none()) else {
        return Ok(None);
    };
    if let Ok(font) = value.cast::<PyFont>() {
        return Ok(Some(Arc::clone(&font.get().inner)));
    }
    if let Ok(name) = value.extract::<String>() {
        return Font::builtin(&name).map(Some).map_err(font_error);
    }
    Err(PyTypeError::new_err(format!(
        "font must be a Font or the name of a built-in font, but got {}. Pass Font('small'), \
         Font.from_file(path) or a name such as 'small'.",
        value.get_type().name()?
    )))
}

/// Draw a ratatui buffer as a PNG image, with the cells of `font` (the built-in `large` font
/// when it is `None`).
pub fn buffer_png<'py>(
    py: Python<'py>,
    buffer: &ratatui_core::buffer::Buffer,
    font: Option<Arc<Font>>,
) -> PyResult<Bound<'py, PyBytes>> {
    let font = match font {
        Some(font) => font,
        None => Font::builtin("large").map_err(font_error)?,
    };
    let png = py
        .detach(|| xnano_terminal_pixels::render_buffer(buffer, &font).map(|image| image.to_png()))
        .map_err(font_error)?;
    Ok(PyBytes::new(py, &png))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyFont>()
}
