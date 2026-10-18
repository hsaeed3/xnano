//! A `repr` built from an object's own properties.

use pyo3::prelude::*;

/// `Name(first=..., second=...)` from the named properties of `object`.
///
/// A name that starts with `#` shows how many items the property holds instead of the items,
/// and a property that cannot be read at this moment, such as on a closed device, is left out.
pub fn described(object: &Bound<'_, PyAny>, properties: &[&str]) -> PyResult<String> {
    let name = object.get_type().name()?;
    let mut parts = Vec::with_capacity(properties.len());
    for property in properties {
        let (field, is_count) = match property.strip_prefix('#') {
            Some(field) => (field, true),
            None => (*property, false),
        };
        let Ok(value) = object.getattr(field) else {
            continue;
        };
        let shown = if is_count {
            value.len()?.to_string()
        } else {
            value.repr()?.to_string()
        };
        parts.push(format!("{field}={shown}"));
    }
    Ok(format!("{name}({})", parts.join(", ")))
}

/// The values of every readable property of `object`'s class, in the order they are defined.
fn property_values<'py>(object: &Bound<'py, PyAny>) -> PyResult<Vec<Bound<'py, PyAny>>> {
    let class = object.get_type();
    let namespace = class.getattr("__dict__")?;
    let mut values = Vec::new();
    for item in namespace.call_method0("items")?.try_iter()? {
        let (name, attribute): (String, Bound<'py, PyAny>) = item?.extract()?;
        if name.starts_with('_') || attribute.get_type().name()? != "getset_descriptor" {
            continue;
        }
        values.push(object.getattr(name.as_str())?);
    }
    Ok(values)
}

/// `==` and `!=` for a value class: two objects of the same class are equal when every
/// readable property is equal. Other comparisons are not supported.
pub fn compare_by_properties(
    object: &Bound<'_, PyAny>,
    other: &Bound<'_, PyAny>,
    operation: pyo3::basic::CompareOp,
) -> PyResult<Py<PyAny>> {
    let py = object.py();
    let is_same_class = other.get_type().is(object.get_type());
    let is_equality = matches!(
        operation,
        pyo3::basic::CompareOp::Eq | pyo3::basic::CompareOp::Ne
    );
    if !is_same_class || !is_equality {
        return Ok(py.NotImplemented());
    }
    let mine = pyo3::types::PyTuple::new(py, property_values(object)?)?;
    let theirs = pyo3::types::PyTuple::new(py, property_values(other)?)?;
    let is_equal = mine.eq(theirs)?;
    let answer = if matches!(operation, pyo3::basic::CompareOp::Eq) {
        is_equal
    } else {
        !is_equal
    };
    Ok(pyo3::types::PyBool::new(py, answer)
        .to_owned()
        .into_any()
        .unbind())
}

/// The hash of a value class, from every readable property; an unhashable property, such
/// as a list, is hashed by its `repr`, so equal objects still hash the same.
pub fn hash_by_properties(object: &Bound<'_, PyAny>) -> PyResult<isize> {
    let py = object.py();
    let mut parts = Vec::new();
    for value in property_values(object)? {
        parts.push(match value.hash() {
            Ok(hash) => hash.into_pyobject(py)?.into_any(),
            Err(_) => value.repr()?.into_any(),
        });
    }
    pyo3::types::PyTuple::new(py, parts)?.hash()
}
