//! The value tree: finite JSON-compatible values that share unchanged branches.

use std::sync::Arc;

use indexmap::IndexMap;
use serde_json::Value;

use crate::error::{Error, Issue};

/// One value of a state tree.
///
/// Containers are reference counted, so cloning a node is cheap and a modified tree
/// shares every branch the modification did not touch.
#[derive(Debug, Clone)]
pub enum Node {
    Null,
    Bool(bool),
    Integer(i64),
    Float(f64),
    String(Arc<str>),
    Array(Arc<Vec<Node>>),
    Object(Arc<IndexMap<Arc<str>, Node>>),
}

/// One step of a path whose container type is known.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Segment {
    Key(String),
    Index(usize),
}

impl Segment {
    /// The token form used by JSON Pointer.
    pub fn token(&self) -> String {
        match self {
            Self::Key(key) => key.clone(),
            Self::Index(index) => index.to_string(),
        }
    }
}

impl PartialEq for Node {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (Self::Null, Self::Null) => true,
            (Self::Bool(left), Self::Bool(right)) => left == right,
            (Self::Integer(left), Self::Integer(right)) => left == right,
            (Self::Float(left), Self::Float(right)) => left == right,
            (Self::Integer(left), Self::Float(right))
            | (Self::Float(right), Self::Integer(left)) => {
                (*left as f64) == *right && right.fract() == 0.0
            }
            (Self::String(left), Self::String(right)) => left == right,
            (Self::Array(left), Self::Array(right)) => Arc::ptr_eq(left, right) || left == right,
            (Self::Object(left), Self::Object(right)) => Arc::ptr_eq(left, right) || left == right,
            _ => false,
        }
    }
}

impl Node {
    pub fn string(value: &str) -> Self {
        Self::String(Arc::from(value))
    }

    pub fn array(items: Vec<Node>) -> Self {
        Self::Array(Arc::new(items))
    }

    pub fn object(entries: IndexMap<Arc<str>, Node>) -> Self {
        Self::Object(Arc::new(entries))
    }

    /// The JSON Schema name of this value's type.
    pub fn type_name(&self) -> &'static str {
        match self {
            Self::Null => "null",
            Self::Bool(_) => "boolean",
            Self::Integer(_) => "integer",
            Self::Float(_) => "number",
            Self::String(_) => "string",
            Self::Array(_) => "array",
            Self::Object(_) => "object",
        }
    }

    /// Whether both nodes are the very same shared allocation (or equal scalars).
    pub fn is_same(&self, other: &Self) -> bool {
        match (self, other) {
            (Self::Array(left), Self::Array(right)) => Arc::ptr_eq(left, right),
            (Self::Object(left), Self::Object(right)) => Arc::ptr_eq(left, right),
            (Self::String(left), Self::String(right)) => Arc::ptr_eq(left, right),
            _ => self == other,
        }
    }

    /// Convert from parsed JSON, rejecting values the state tree cannot hold.
    pub fn from_json(value: &Value) -> Result<Self, Error> {
        Self::from_json_at(value, &mut Vec::new())
    }

    fn from_json_at(value: &Value, path: &mut Vec<String>) -> Result<Self, Error> {
        Ok(match value {
            Value::Null => Self::Null,
            Value::Bool(flag) => Self::Bool(*flag),
            Value::Number(number) => {
                if let Some(integer) = number.as_i64() {
                    Self::Integer(integer)
                } else if number.is_u64() {
                    return Err(Error::validation(
                        path,
                        "type",
                        "the integer is larger than the largest supported value, 9223372036854775807",
                    ));
                } else {
                    let float = number.as_f64().unwrap_or(f64::NAN);
                    if !float.is_finite() {
                        return Err(Error::validation(path, "type", "the number is not finite"));
                    }
                    Self::Float(float)
                }
            }
            Value::String(text) => Self::string(text),
            Value::Array(items) => {
                let mut nodes = Vec::with_capacity(items.len());
                for (index, item) in items.iter().enumerate() {
                    path.push(index.to_string());
                    nodes.push(Self::from_json_at(item, path)?);
                    path.pop();
                }
                Self::array(nodes)
            }
            Value::Object(entries) => {
                let mut nodes = IndexMap::with_capacity(entries.len());
                for (key, item) in entries {
                    path.push(key.clone());
                    nodes.insert(Arc::from(key.as_str()), Self::from_json_at(item, path)?);
                    path.pop();
                }
                Self::object(nodes)
            }
        })
    }

    /// Convert to JSON.
    pub fn to_json(&self) -> Value {
        match self {
            Self::Null => Value::Null,
            Self::Bool(flag) => Value::Bool(*flag),
            Self::Integer(integer) => Value::from(*integer),
            Self::Float(float) => {
                serde_json::Number::from_f64(*float).map_or(Value::Null, Value::Number)
            }
            Self::String(text) => Value::String(text.to_string()),
            Self::Array(items) => Value::Array(items.iter().map(Self::to_json).collect()),
            Self::Object(entries) => Value::Object(
                entries
                    .iter()
                    .map(|(key, item)| (key.to_string(), item.to_json()))
                    .collect(),
            ),
        }
    }

    /// The child reached by one path token, if there is one.
    pub fn child(&self, token: &str) -> Option<&Node> {
        match self {
            Self::Object(entries) => entries.get(token),
            Self::Array(items) => parse_index(token).and_then(|index| items.get(index)),
            _ => None,
        }
    }

    /// The node at `path`, if it exists.
    pub fn get(&self, path: &[String]) -> Option<&Node> {
        let mut current = self;
        for token in path {
            current = current.child(token)?;
        }
        Some(current)
    }

    /// The path with array tokens resolved to indexes, when the path exists up to the end.
    pub fn resolve(&self, path: &[String]) -> Vec<Segment> {
        let mut current = Some(self);
        let mut segments = Vec::with_capacity(path.len());
        for token in path {
            let segment = match current {
                Some(Self::Array(_)) => {
                    parse_index(token).map_or_else(|| Segment::Key(token.clone()), Segment::Index)
                }
                _ => Segment::Key(token.clone()),
            };
            current = current.and_then(|node| node.child(token));
            segments.push(segment);
        }
        segments
    }

    /// A copy of this tree with `value` at `path`.
    ///
    /// The parent must exist. An object key is inserted or replaced; an array index must
    /// exist already (use [`Node::inserted`] to grow an array).
    pub fn with_value(&self, path: &[String], value: Node) -> Result<Node, Error> {
        let Some((token, rest)) = path.split_first() else {
            return Ok(value);
        };
        match self {
            Self::Object(entries) => {
                let mut copy = (**entries).clone();
                let updated = match entries.get(token.as_str()) {
                    Some(child) => child.with_value(rest, value)?,
                    None if rest.is_empty() => value,
                    None => return Err(missing(path, token)),
                };
                copy.insert(Arc::from(token.as_str()), updated);
                Ok(Self::object(copy))
            }
            Self::Array(items) => {
                let index = array_index(token, items.len(), path)?;
                let mut copy = (**items).clone();
                copy[index] = items[index].with_value(rest, value)?;
                Ok(Self::array(copy))
            }
            _ => Err(missing(path, token)),
        }
    }

    /// A copy of this tree without the entry at `path`.
    pub fn without(&self, path: &[String]) -> Result<Node, Error> {
        let Some((token, rest)) = path.split_first() else {
            return Err(Error::validation(
                path,
                "path",
                "the root of the state cannot be removed; replace it with a new value instead",
            ));
        };
        match self {
            Self::Object(entries) => {
                let Some(child) = entries.get(token.as_str()) else {
                    return Err(missing(path, token));
                };
                let mut copy = (**entries).clone();
                if rest.is_empty() {
                    copy.shift_remove(token.as_str());
                } else {
                    copy.insert(Arc::from(token.as_str()), child.without(rest)?);
                }
                Ok(Self::object(copy))
            }
            Self::Array(items) => {
                let index = array_index(token, items.len(), path)?;
                let mut copy = (**items).clone();
                if rest.is_empty() {
                    copy.remove(index);
                } else {
                    copy[index] = items[index].without(rest)?;
                }
                Ok(Self::array(copy))
            }
            _ => Err(missing(path, token)),
        }
    }

    /// A copy of this tree where `value` is added at `path`, shifting array entries.
    ///
    /// The final token of an array path may be `-` to append.
    pub fn inserted(&self, path: &[String], value: Node) -> Result<Node, Error> {
        let Some((token, rest)) = path.split_first() else {
            return Ok(value);
        };
        match self {
            Self::Object(entries) => {
                let mut copy = (**entries).clone();
                if rest.is_empty() {
                    copy.insert(Arc::from(token.as_str()), value);
                } else {
                    let Some(child) = entries.get(token.as_str()) else {
                        return Err(missing(path, token));
                    };
                    copy.insert(Arc::from(token.as_str()), child.inserted(rest, value)?);
                }
                Ok(Self::object(copy))
            }
            Self::Array(items) => {
                let mut copy = (**items).clone();
                if rest.is_empty() {
                    let index = if token == "-" {
                        items.len()
                    } else {
                        let index = parse_index(token).ok_or_else(|| bad_index(path, token))?;
                        if index > items.len() {
                            return Err(Error::validation(
                                path,
                                "path",
                                format!(
                                    "the index {index} is past the end of an array of {} items",
                                    items.len()
                                ),
                            ));
                        }
                        index
                    };
                    copy.insert(index, value);
                } else {
                    let index = array_index(token, items.len(), path)?;
                    copy[index] = items[index].inserted(rest, value)?;
                }
                Ok(Self::array(copy))
            }
            _ => Err(missing(path, token)),
        }
    }

    /// The paths where `after` differs from `self`, as the smallest changed branches.
    pub fn diff(&self, after: &Node) -> Vec<Vec<Segment>> {
        let mut changes = Vec::new();
        diff_into(self, after, &mut Vec::new(), &mut changes);
        changes
    }

    /// Greatest nesting depth of containers in this value.
    pub fn depth(&self) -> usize {
        match self {
            Self::Array(items) => 1 + items.iter().map(Self::depth).max().unwrap_or(0),
            Self::Object(entries) => 1 + entries.values().map(Self::depth).max().unwrap_or(0),
            _ => 0,
        }
    }
}

fn diff_into(
    before: &Node,
    after: &Node,
    path: &mut Vec<Segment>,
    changes: &mut Vec<Vec<Segment>>,
) {
    if before.is_same(after) {
        return;
    }
    match (before, after) {
        (Node::Object(left), Node::Object(right)) => {
            for (key, left_child) in left.iter() {
                path.push(Segment::Key(key.to_string()));
                match right.get(key) {
                    Some(right_child) => diff_into(left_child, right_child, path, changes),
                    None => changes.push(path.clone()),
                }
                path.pop();
            }
            for key in right.keys() {
                if !left.contains_key(key) {
                    path.push(Segment::Key(key.to_string()));
                    changes.push(path.clone());
                    path.pop();
                }
            }
        }
        (Node::Array(left), Node::Array(right)) if left.len() == right.len() => {
            for (index, (left_child, right_child)) in left.iter().zip(right.iter()).enumerate() {
                path.push(Segment::Index(index));
                diff_into(left_child, right_child, path, changes);
                path.pop();
            }
        }
        _ => changes.push(path.clone()),
    }
}

fn missing(path: &[String], token: &str) -> Error {
    Error::validation(
        path,
        "path",
        format!(
            "there is nothing at \"{token}\" in {}; check the path exists before changing it",
            to_pointer(path)
        ),
    )
}

fn bad_index(path: &[String], token: &str) -> Error {
    Error::validation(
        path,
        "path",
        format!("\"{token}\" is not a valid array index; use a whole number, or \"-\" to append"),
    )
}

fn array_index(token: &str, length: usize, path: &[String]) -> Result<usize, Error> {
    let index = parse_index(token).ok_or_else(|| bad_index(path, token))?;
    if index >= length {
        return Err(Error::validation(
            path,
            "path",
            format!("the index {index} is outside an array of {length} items"),
        ));
    }
    Ok(index)
}

/// Parse an array index token: decimal digits without a leading zero.
pub fn parse_index(token: &str) -> Option<usize> {
    if token.is_empty() || (token.len() > 1 && token.starts_with('0')) {
        return None;
    }
    if !token.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    token.parse().ok()
}

/// Escape one token for use in a JSON Pointer.
fn escape(token: &str) -> String {
    token.replace('~', "~0").replace('/', "~1")
}

/// The JSON Pointer for `path` (`""` for the root).
pub fn to_pointer(path: &[String]) -> String {
    let mut pointer = String::new();
    for token in path {
        pointer.push('/');
        pointer.push_str(&escape(token));
    }
    pointer
}

/// Parse a JSON Pointer into path tokens.
pub fn parse_pointer(pointer: &str) -> Result<Vec<String>, Issue> {
    if pointer.is_empty() {
        return Ok(Vec::new());
    }
    let Some(rest) = pointer.strip_prefix('/') else {
        return Err(Issue::new(
            &[],
            "path",
            format!(
                "\"{pointer}\" is not a JSON Pointer; it must be empty or start with \"/\", \
                 for example \"/player/health\""
            ),
        ));
    };
    Ok(rest
        .split('/')
        .map(|token| token.replace("~1", "/").replace("~0", "~"))
        .collect())
}
