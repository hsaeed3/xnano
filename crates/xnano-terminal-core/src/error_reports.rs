//! Error reports: labelled problems, and an exception that carries them.
//!
//! Modelled on pydantic-core's `ValidationError` and its line errors: each `ErrorDetail` has
//! a code, the location of the value it is about, a message, a hint and the value itself,
//! an `ErrorReport` formats them all, plainly or with terminal colors, and `ReportedError`
//! is raised with a report as its one argument, so ``str(error)`` is the report.

use std::fmt::Write as _;

use pyo3::exceptions::{PyException, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString, PyTuple};

pyo3::create_exception!(
    xnano_core._xnano_core,
    ReportedError,
    PyException,
    "An error raised with an ErrorReport as its one argument; str(error) is the report."
);

/// The longest representation of an input value a report shows before cutting it short.
const MOST_INPUT_CHARACTERS: usize = 60;

/// One problem of a report: what it is, where it is, and what to do about it.
#[pyclass(name = "ErrorDetail", module = "xnano_core._xnano_core", frozen)]
pub struct PyErrorDetail {
    code: String,
    message: String,
    location: Py<PyTuple>,
    hint: Option<String>,
    input_value: Option<Py<PyAny>>,
}

#[pymethods]
impl PyErrorDetail {
    fn __richcmp__(
        slf: &Bound<'_, Self>,
        other: &Bound<'_, PyAny>,
        operation: pyo3::basic::CompareOp,
    ) -> PyResult<Py<PyAny>> {
        crate::reprs::compare_by_properties(slf.as_any(), other, operation)
    }

    fn __hash__(slf: &Bound<'_, Self>) -> PyResult<isize> {
        crate::reprs::hash_by_properties(slf.as_any())
    }

    #[new]
    #[pyo3(signature = (code, message, *, location = None, hint = None, **input))]
    fn new(
        py: Python<'_>,
        code: String,
        message: String,
        location: Option<&Bound<'_, PyAny>>,
        hint: Option<String>,
        input: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Self> {
        if code.trim().is_empty() {
            return Err(PyValueError::new_err(
                "an error detail needs a code, such as 'validation.type'; pass code='...'",
            ));
        }
        let location = location_tuple(py, location)?;
        let mut input_value = None;
        if let Some(input) = input {
            for (key, value) in input.iter() {
                let name = key.extract::<String>()?;
                if name != "input_value" {
                    return Err(PyTypeError::new_err(format!(
                        "ErrorDetail() takes code, message, location, hint and input_value, \
                         not {name}; pass the value the problem is about as input_value=..."
                    )));
                }
                input_value = Some(value.unbind());
            }
        }
        Ok(Self {
            code,
            message,
            location: location.unbind(),
            hint,
            input_value,
        })
    }

    /// The label of the problem, such as ``'validation.type'``.
    #[getter]
    fn code(&self) -> &str {
        &self.code
    }

    /// What went wrong, in a sentence.
    #[getter]
    fn message(&self) -> &str {
        &self.message
    }

    /// Where the value is: argument names, keys and indexes, outermost first.
    #[getter]
    fn location(&self, py: Python<'_>) -> Py<PyTuple> {
        self.location.clone_ref(py)
    }

    /// What to do next, or ``None``.
    #[getter]
    fn hint(&self) -> Option<&str> {
        self.hint.as_deref()
    }

    /// Whether the detail carries the value the problem is about.
    #[getter]
    fn has_input_value(&self) -> bool {
        self.input_value.is_some()
    }

    /// The value the problem is about; ``None`` when there is none.
    #[getter]
    fn input_value(&self, py: Python<'_>) -> Py<PyAny> {
        match &self.input_value {
            Some(value) => value.clone_ref(py),
            None => py.None(),
        }
    }

    /// The name of the type of the input value, or ``None`` when there is no input value.
    #[getter]
    fn input_type(&self, py: Python<'_>) -> PyResult<Option<String>> {
        self.input_value
            .as_ref()
            .map(|value| type_name(value.bind(py)))
            .transpose()
    }

    fn __reduce__<'py>(
        &self,
        py: Python<'py>,
    ) -> PyResult<(Bound<'py, PyAny>, Bound<'py, PyTuple>)> {
        let restore = py
            .import("xnano_core._xnano_core")?
            .getattr("_restore_error_detail")?;
        let arguments = (
            self.code.clone(),
            self.message.clone(),
            self.location.clone_ref(py),
            self.hint.clone(),
            self.input_value.is_some(),
            self.input_value(py),
        )
            .into_pyobject(py)?;
        Ok((restore, arguments))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        Ok(format!(
            "ErrorDetail(code={:?}, location={}, message={:?})",
            self.code,
            self.location.bind(py).repr()?,
            self.message
        ))
    }
}

impl PyErrorDetail {
    /// The lines of this detail in a report.
    fn report_lines(&self, py: Python<'_>, is_colored: bool) -> PyResult<Vec<String>> {
        let mut lines = Vec::new();
        let location = location_text(self.location.bind(py))?;
        if !location.is_empty() {
            lines.push(paint(&location, BOLD, is_colored));
        }
        let mut facts = vec![format!("code={}", paint(&self.code, CYAN, is_colored))];
        if let Some(value) = &self.input_value {
            let value = value.bind(py);
            facts.push(format!(
                "input_value={}",
                shortened(&value.repr()?.to_string())
            ));
            facts.push(format!("input_type={}", type_name(value)?));
        }
        lines.push(format!(
            "  {} {}",
            self.message,
            paint(&format!("[{}]", facts.join(", ")), DIM, is_colored)
        ));
        if let Some(hint) = &self.hint {
            lines.push(format!("    {}", paint(hint, GREEN, is_colored)));
        }
        Ok(lines)
    }
}

/// One or more labelled problems, which a ``ReportedError`` is raised with.
#[pyclass(name = "ErrorReport", module = "xnano_core._xnano_core", frozen)]
pub struct PyErrorReport {
    title: String,
    details: Vec<Py<PyErrorDetail>>,
}

#[pymethods]
impl PyErrorReport {
    fn __richcmp__(
        slf: &Bound<'_, Self>,
        other: &Bound<'_, PyAny>,
        operation: pyo3::basic::CompareOp,
    ) -> PyResult<Py<PyAny>> {
        crate::reprs::compare_by_properties(slf.as_any(), other, operation)
    }

    fn __hash__(slf: &Bound<'_, Self>) -> PyResult<isize> {
        crate::reprs::hash_by_properties(slf.as_any())
    }

    #[new]
    #[pyo3(signature = (title, details))]
    fn new(title: String, details: Vec<Py<PyErrorDetail>>) -> PyResult<Self> {
        if details.is_empty() {
            return Err(PyValueError::new_err(
                "an error report needs at least one ErrorDetail; pass details=[ErrorDetail(...)]",
            ));
        }
        Ok(Self { title, details })
    }

    /// What the report is about, such as ``'canvas.write()'``; may be empty.
    #[getter]
    fn title(&self) -> &str {
        &self.title
    }

    /// The problems, in the order they were found.
    #[getter]
    fn details<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        PyTuple::new(py, self.details.iter().map(|detail| detail.clone_ref(py)))
    }

    /// How many problems the report has.
    fn error_count(&self) -> usize {
        self.details.len()
    }

    /// The report as text, with terminal colors when ``is_colored`` is true.
    #[pyo3(signature = (*, is_colored = false))]
    fn render(&self, py: Python<'_>, is_colored: bool) -> PyResult<String> {
        let count = self.details.len();
        let noun = if count == 1 { "error" } else { "errors" };
        let heading = if self.title.is_empty() {
            format!("{count} {noun}")
        } else {
            format!("{count} {noun} in {}", self.title)
        };
        let mut lines = vec![paint(&heading, BOLD_RED, is_colored)];
        for detail in &self.details {
            lines.extend(detail.get().report_lines(py, is_colored)?);
        }
        Ok(lines.join("\n"))
    }

    fn __str__(&self, py: Python<'_>) -> PyResult<String> {
        self.render(py, false)
    }

    fn __repr__(&self) -> String {
        format!(
            "ErrorReport(title={:?}, error_count={})",
            self.title,
            self.details.len()
        )
    }

    fn __reduce__<'py>(
        slf: &Bound<'py, Self>,
    ) -> PyResult<(Bound<'py, PyAny>, (String, Vec<Py<PyErrorDetail>>))> {
        let py = slf.py();
        let this = slf.get();
        Ok((
            slf.get_type().into_any(),
            (
                this.title.clone(),
                this.details
                    .iter()
                    .map(|detail| detail.clone_ref(py))
                    .collect(),
            ),
        ))
    }
}

/// Rebuild an ``ErrorDetail`` when it is unpickled.
#[pyfunction]
#[pyo3(name = "_restore_error_detail")]
fn restore_error_detail(
    code: String,
    message: String,
    location: Py<PyTuple>,
    hint: Option<String>,
    has_input_value: bool,
    input_value: Py<PyAny>,
) -> PyErrorDetail {
    PyErrorDetail {
        code,
        message,
        location,
        hint,
        input_value: has_input_value.then_some(input_value),
    }
}

const BOLD: &str = "1";
const BOLD_RED: &str = "1;31";
const CYAN: &str = "36";
const DIM: &str = "2";
const GREEN: &str = "32";

/// Wrap text in an ANSI style when colors are wanted.
fn paint(text: &str, style: &str, is_colored: bool) -> String {
    if is_colored {
        format!("\x1b[{style}m{text}\x1b[0m")
    } else {
        text.to_owned()
    }
}

/// A representation cut to a readable length, as pydantic does for input values.
fn shortened(text: &str) -> String {
    if text.chars().count() <= MOST_INPUT_CHARACTERS {
        return text.to_owned();
    }
    let half = MOST_INPUT_CHARACTERS / 2 - 2;
    let start: String = text.chars().take(half).collect();
    let end: String = text
        .chars()
        .rev()
        .take(half)
        .collect::<Vec<_>>()
        .into_iter()
        .rev()
        .collect();
    format!("{start}...{end}")
}

fn type_name(value: &Bound<'_, PyAny>) -> PyResult<String> {
    Ok(value.get_type().name()?.to_string())
}

/// Check a location: a string, an index, or a sequence of them.
fn location_tuple<'py>(
    py: Python<'py>,
    location: Option<&Bound<'py, PyAny>>,
) -> PyResult<Bound<'py, PyTuple>> {
    let Some(location) = location else {
        return Ok(PyTuple::empty(py));
    };
    if location.is_none() {
        return Ok(PyTuple::empty(py));
    }
    let parts: Vec<Bound<'py, PyAny>> =
        if location.is_instance_of::<PyString>() || is_index(location) {
            vec![location.clone()]
        } else {
            location.try_iter()?.collect::<PyResult<_>>()?
        };
    for part in &parts {
        if !part.is_instance_of::<PyString>() && !is_index(part) {
            return Err(PyTypeError::new_err(format!(
                "a location holds names and indexes, such as ('settings', 'height') or \
                 ('items', 0), but it held {}",
                part.repr()?
            )));
        }
    }
    PyTuple::new(py, parts)
}

fn is_index(value: &Bound<'_, PyAny>) -> bool {
    value.is_instance_of::<pyo3::types::PyInt>() && !value.is_instance_of::<pyo3::types::PyBool>()
}

/// ``('settings', 'items', 0)`` as ``settings.items[0]``.
fn location_text(location: &Bound<'_, PyTuple>) -> PyResult<String> {
    let mut text = String::new();
    for part in location.iter() {
        if is_index(&part) {
            let _ = write!(text, "[{}]", part.str()?);
        } else {
            if !text.is_empty() {
                text.push('.');
            }
            text.push_str(&part.str()?.to_string());
        }
    }
    Ok(text)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyErrorDetail>()?;
    m.add_class::<PyErrorReport>()?;
    m.add_function(wrap_pyfunction!(restore_error_detail, m)?)?;
    m.add("ReportedError", m.py().get_type::<ReportedError>())?;
    Ok(())
}
