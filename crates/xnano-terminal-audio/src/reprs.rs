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
