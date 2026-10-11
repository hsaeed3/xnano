//! Conversions between Python objects and the values the engine works with.

use std::sync::Arc;

use indexmap::IndexMap;
use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple};
use xnano_terminal_runtime::expression::Scalar;
use xnano_terminal_runtime::text::{Line, Span, split_lines};
use xnano_terminal_state::{Node, Segment};

use crate::geometry::{PyPoint, PyRectangle, PySize};
use crate::text::PyStyledText;

const MAXIMUM_DEPTH: usize = 256;

/// A state value from a Python object: `None`, bool, int, float, str, list, tuple or dict.
pub fn node_from_py(value: &Bound<'_, PyAny>) -> PyResult<Node> {
    node_at(value, 0)
}

fn node_at(value: &Bound<'_, PyAny>, depth: usize) -> PyResult<Node> {
    if depth > MAXIMUM_DEPTH {
        return Err(PyValueError::new_err(
            "the value nests deeper than 256 levels; state values must be finite trees, not cycles",
        ));
    }
    if value.is_none() {
        return Ok(Node::Null);
    }
    if let Ok(flag) = value.cast::<PyBool>() {
        return Ok(Node::Bool(flag.is_true()));
    }
    if value.is_instance_of::<PyInt>() {
        return value.extract::<i64>().map(Node::Integer).map_err(|_| {
            PyValueError::new_err(
                "the integer is outside the supported range of -9223372036854775808 to \
                 9223372036854775807",
            )
        });
    }
    if let Ok(float) = value.cast::<PyFloat>() {
        let number = float.value();
        if !number.is_finite() {
            return Err(PyValueError::new_err(
                "state values must be finite; NaN and infinity cannot be stored",
            ));
        }
        return Ok(Node::Float(number));
    }
    if let Ok(text) = value.cast::<PyString>() {
        return Ok(Node::string(&text.to_cow()?));
    }
    if let Ok(dictionary) = value.cast::<PyDict>() {
        let mut entries = IndexMap::with_capacity(dictionary.len());
        for (key, item) in dictionary.iter() {
            let key = key.cast::<PyString>().map_err(|_| {
                PyTypeError::new_err(format!(
                    "state object keys must be strings, not {}",
                    key.get_type()
                        .name()
                        .map_or_else(|_| "?".into(), |name| name.to_string())
                ))
            })?;
            entries.insert(Arc::from(&*key.to_cow()?), node_at(&item, depth + 1)?);
        }
        return Ok(Node::object(entries));
    }
    if value.is_instance_of::<PyList>() || value.is_instance_of::<PyTuple>() {
        let mut items = Vec::new();
        for item in value.try_iter()? {
            items.push(node_at(&item?, depth + 1)?);
        }
        return Ok(Node::array(items));
    }
    Err(PyTypeError::new_err(format!(
        "{} cannot be stored in state; use None, bool, int, float, str, list or dict values, or \
         convert the model to a dictionary first",
        value.get_type().name()?
    )))
}

pub fn node_to_py<'py>(py: Python<'py>, node: &Node) -> PyResult<Bound<'py, PyAny>> {
    Ok(match node {
        Node::Null => py.None().into_bound(py),
        Node::Bool(flag) => PyBool::new(py, *flag).to_owned().into_any(),
        Node::Integer(integer) => integer.into_pyobject(py)?.into_any(),
        Node::Float(float) => float.into_pyobject(py)?.into_any(),
        Node::String(text) => PyString::new(py, text).into_any(),
        Node::Array(items) => {
            let list = PyList::empty(py);
            for item in items.iter() {
                list.append(node_to_py(py, item)?)?;
            }
            list.into_any()
        }
        Node::Object(entries) => {
            let dictionary = PyDict::new(py);
            for (key, item) in entries.iter() {
                dictionary.set_item(&**key, node_to_py(py, item)?)?;
            }
            dictionary.into_any()
        }
    })
}

pub fn json_to_py<'py>(py: Python<'py>, value: &serde_json::Value) -> PyResult<Bound<'py, PyAny>> {
    let node = Node::from_json(value).map_err(|error| PyValueError::new_err(error.to_string()))?;
    node_to_py(py, &node)
}

/// A state path from a sequence of `str` and `int`.
pub fn path_from_py(value: &Bound<'_, PyAny>) -> PyResult<Vec<String>> {
    if value.is_instance_of::<PyString>() {
        return Err(PyTypeError::new_err(
            "a state path must be a tuple such as (\"player\", \"health\"), not a string; \
             wrap a single key in a tuple",
        ));
    }
    let mut tokens = Vec::new();
    for item in value.try_iter()? {
        let item = item?;
        if let Ok(text) = item.cast::<PyString>() {
            tokens.push(text.to_cow()?.into_owned());
        } else if item.is_instance_of::<PyInt>() && !item.is_instance_of::<PyBool>() {
            let index: i64 = item.extract()?;
            if index < 0 {
                return Err(PyValueError::new_err(format!(
                    "the path index {index} is negative; array indexes start at 0"
                )));
            }
            tokens.push(index.to_string());
        } else {
            return Err(PyTypeError::new_err(
                "state path entries must be strings (object keys) or ints (array indexes)",
            ));
        }
    }
    Ok(tokens)
}

pub fn segments_to_py<'py>(py: Python<'py>, segments: &[Segment]) -> PyResult<Bound<'py, PyTuple>> {
    let mut items: Vec<Bound<'py, PyAny>> = Vec::with_capacity(segments.len());
    for segment in segments {
        items.push(match segment {
            Segment::Key(key) => PyString::new(py, key).into_any(),
            Segment::Index(index) => index.into_pyobject(py)?.into_any(),
        });
    }
    PyTuple::new(py, items)
}

pub fn tokens_to_py<'py>(py: Python<'py>, tokens: &[String]) -> PyResult<Bound<'py, PyTuple>> {
    PyTuple::new(py, tokens.iter().map(String::as_str))
}

pub fn paths_from_py(value: &Bound<'_, PyAny>) -> PyResult<Vec<Vec<String>>> {
    let mut paths = Vec::new();
    for item in value.try_iter()? {
        paths.push(path_from_py(&item?)?);
    }
    Ok(paths)
}

/// Rows of styled text from `str`, `StyledText` or a sequence of those.
pub fn text_lines(value: &Bound<'_, PyAny>) -> PyResult<Vec<Line>> {
    if let Ok(text) = value.cast::<PyString>() {
        return Ok(split_lines(&[Span::new(
            text.to_cow()?.into_owned(),
            xnano_terminal_runtime::style::Style::default(),
        )]));
    }
    if let Ok(styled) = value.extract::<PyRef<'_, PyStyledText>>() {
        return Ok(split_lines(&styled.spans));
    }
    let mut lines: Vec<Line> = Vec::new();
    let Ok(items) = value.try_iter() else {
        return Err(PyTypeError::new_err(format!(
            "text must be a str, a StyledText, or a sequence of those, not {}",
            value.get_type().name()?
        )));
    };
    for item in items {
        let item = item?;
        if let Ok(text) = item.cast::<PyString>() {
            lines.extend(split_lines(&[Span::new(
                text.to_cow()?.into_owned(),
                xnano_terminal_runtime::style::Style::default(),
            )]));
        } else if let Ok(styled) = item.extract::<PyRef<'_, PyStyledText>>() {
            lines.extend(split_lines(&styled.spans));
        } else {
            return Err(PyTypeError::new_err(format!(
                "each item of a text sequence must be a str or a StyledText, not {}",
                item.get_type().name()?
            )));
        }
    }
    Ok(lines)
}

pub fn scalar_to_py<'py>(py: Python<'py>, scalar: &Scalar) -> PyResult<Bound<'py, PyAny>> {
    Ok(match scalar {
        Scalar::Null => py.None().into_bound(py),
        Scalar::Bool(flag) => PyBool::new(py, *flag).to_owned().into_any(),
        Scalar::Integer(integer) => integer.into_pyobject(py)?.into_any(),
        Scalar::Float(float) => float.into_pyobject(py)?.into_any(),
        Scalar::Text(text) => PyString::new(py, text).into_any(),
        Scalar::Point(point) => Bound::new(py, PyPoint { inner: *point })?.into_any(),
        Scalar::Size(size) => Bound::new(py, PySize { inner: *size })?.into_any(),
        Scalar::Rectangle(rectangle) => {
            Bound::new(py, PyRectangle { inner: *rectangle })?.into_any()
        }
        Scalar::Json(value) => json_to_py(py, value)?,
    })
}

pub fn scalar_from_py(value: &Bound<'_, PyAny>) -> PyResult<Scalar> {
    if value.is_none() {
        return Ok(Scalar::Null);
    }
    if let Ok(flag) = value.cast::<PyBool>() {
        return Ok(Scalar::Bool(flag.is_true()));
    }
    if value.is_instance_of::<PyInt>() {
        return Ok(Scalar::Integer(value.extract()?));
    }
    if let Ok(float) = value.cast::<PyFloat>() {
        return Ok(Scalar::Float(float.value()));
    }
    if let Ok(text) = value.cast::<PyString>() {
        return Ok(Scalar::Text(text.to_cow()?.into_owned()));
    }
    if let Ok(point) = value.extract::<PyPoint>() {
        return Ok(Scalar::Point(point.inner));
    }
    if let Ok(size) = value.extract::<PySize>() {
        return Ok(Scalar::Size(size.inner));
    }
    if let Ok(rectangle) = value.extract::<PyRectangle>() {
        return Ok(Scalar::Rectangle(rectangle.inner));
    }
    let node = node_from_py(value)?;
    Ok(Scalar::from_node(&node))
}
