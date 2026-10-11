//! JSON Patch (RFC 6902): ordered `add`, `remove`, `replace`, `move`, `copy` and `test` edits.

use serde_json::{Map, Value};

use crate::error::{Error, Issue};
use crate::node::{Node, parse_pointer, to_pointer};

/// One edit of a patch.
#[derive(Debug, Clone, PartialEq)]
pub enum PatchOperation {
    Add {
        path: Vec<String>,
        value: Node,
    },
    Remove {
        path: Vec<String>,
    },
    Replace {
        path: Vec<String>,
        value: Node,
    },
    Move {
        from: Vec<String>,
        path: Vec<String>,
    },
    Copy {
        from: Vec<String>,
        path: Vec<String>,
    },
    Test {
        path: Vec<String>,
        value: Node,
    },
}

impl PatchOperation {
    /// The branch this edit writes to.
    pub fn target(&self) -> &[String] {
        match self {
            Self::Add { path, .. }
            | Self::Remove { path }
            | Self::Replace { path, .. }
            | Self::Move { path, .. }
            | Self::Copy { path, .. }
            | Self::Test { path, .. } => path,
        }
    }

    fn to_json(&self) -> Value {
        let mut entries = Map::new();
        let name = match self {
            Self::Add { .. } => "add",
            Self::Remove { .. } => "remove",
            Self::Replace { .. } => "replace",
            Self::Move { .. } => "move",
            Self::Copy { .. } => "copy",
            Self::Test { .. } => "test",
        };
        entries.insert("op".into(), Value::String(name.into()));
        entries.insert("path".into(), Value::String(to_pointer(self.target())));
        match self {
            Self::Add { value, .. } | Self::Replace { value, .. } | Self::Test { value, .. } => {
                entries.insert("value".into(), value.to_json());
            }
            Self::Move { from, .. } | Self::Copy { from, .. } => {
                entries.insert("from".into(), Value::String(to_pointer(from)));
            }
            Self::Remove { .. } => {}
        }
        Value::Object(entries)
    }
}

/// An ordered list of edits that apply together or not at all.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct Patch {
    pub operations: Vec<PatchOperation>,
}

fn invalid(index: usize, message: impl Into<String>) -> Error {
    Error::Validation(vec![Issue::new(
        &[],
        "patch",
        format!(
            "operation {index} of the patch is invalid: {}",
            message.into()
        ),
    )])
}

impl Patch {
    /// Parse a patch from a JSON array of operation objects.
    pub fn from_json(document: &Value) -> Result<Self, Error> {
        let Value::Array(items) = document else {
            return Err(Error::validation(
                &[],
                "patch",
                "a patch must be a list of operations, for example \
                 [{\"op\": \"replace\", \"path\": \"/score\", \"value\": 3}]",
            ));
        };
        let mut operations = Vec::with_capacity(items.len());
        for (index, item) in items.iter().enumerate() {
            let Value::Object(entries) = item else {
                return Err(invalid(
                    index,
                    "it must be an object with \"op\" and \"path\"",
                ));
            };
            let name = entries.get("op").and_then(Value::as_str).ok_or_else(|| {
                invalid(
                    index,
                    "it needs an \"op\" of add, remove, replace, move, copy or test",
                )
            })?;
            let pointer = |key: &str| -> Result<Vec<String>, Error> {
                let text = entries.get(key).and_then(Value::as_str).ok_or_else(|| {
                    invalid(
                        index,
                        format!("\"{name}\" needs a \"{key}\" JSON Pointer string"),
                    )
                })?;
                parse_pointer(text).map_err(|issue| invalid(index, issue.message))
            };
            let value = |entries: &Map<String, Value>| -> Result<Node, Error> {
                let raw = entries
                    .get("value")
                    .ok_or_else(|| invalid(index, format!("\"{name}\" needs a \"value\"")))?;
                Node::from_json(raw)
            };
            operations.push(match name {
                "add" => PatchOperation::Add { path: pointer("path")?, value: value(entries)? },
                "remove" => PatchOperation::Remove { path: pointer("path")? },
                "replace" => PatchOperation::Replace { path: pointer("path")?, value: value(entries)? },
                "move" => PatchOperation::Move { from: pointer("from")?, path: pointer("path")? },
                "copy" => PatchOperation::Copy { from: pointer("from")?, path: pointer("path")? },
                "test" => PatchOperation::Test { path: pointer("path")?, value: value(entries)? },
                other => {
                    return Err(invalid(
                        index,
                        format!("\"{other}\" is not an operation; use add, remove, replace, move, copy or test"),
                    ));
                }
            });
        }
        Ok(Self { operations })
    }

    /// The patch as a JSON array.
    pub fn to_json(&self) -> Value {
        Value::Array(
            self.operations
                .iter()
                .map(PatchOperation::to_json)
                .collect(),
        )
    }

    /// The patch that turns `before` into `after` at the given changed branches.
    pub fn from_changes(
        before: &Node,
        after: &Node,
        changes: &[Vec<crate::node::Segment>],
    ) -> Self {
        let operations = changes
            .iter()
            .map(|segments| {
                let path: Vec<String> = segments.iter().map(crate::node::Segment::token).collect();
                match (before.get(&path), after.get(&path)) {
                    (Some(_), Some(value)) => PatchOperation::Replace {
                        path,
                        value: value.clone(),
                    },
                    (None, Some(value)) => PatchOperation::Add {
                        path,
                        value: value.clone(),
                    },
                    _ => PatchOperation::Remove { path },
                }
            })
            .collect();
        Self { operations }
    }

    /// Apply every edit to `root`, returning the new tree. Nothing is returned on failure.
    pub fn apply(&self, root: &Node) -> Result<Node, Error> {
        let mut current = root.clone();
        for (index, operation) in self.operations.iter().enumerate() {
            current = apply_operation(&current, operation).map_err(|error| match error {
                Error::Validation(mut issues) => {
                    for issue in &mut issues {
                        if issue.constraint == "path" || issue.constraint == "patch" {
                            issue.message = format!("operation {index} failed: {}", issue.message);
                        }
                    }
                    Error::Validation(issues)
                }
                other => other,
            })?;
        }
        Ok(current)
    }
}

fn require<'a>(root: &'a Node, path: &[String]) -> Result<&'a Node, Error> {
    root.get(path).ok_or_else(|| {
        Error::validation(
            path,
            "path",
            format!("there is nothing at {}", to_pointer(path)),
        )
    })
}

fn apply_operation(root: &Node, operation: &PatchOperation) -> Result<Node, Error> {
    match operation {
        PatchOperation::Add { path, value } => root.inserted(path, value.clone()),
        PatchOperation::Remove { path } => {
            require(root, path)?;
            root.without(path)
        }
        PatchOperation::Replace { path, value } => {
            require(root, path)?;
            root.with_value(path, value.clone())
        }
        PatchOperation::Move { from, path } => {
            let moved = require(root, from)?.clone();
            if path.len() > from.len() && path.starts_with(from) {
                return Err(Error::validation(
                    path,
                    "patch",
                    "a branch cannot be moved into itself",
                ));
            }
            root.without(from)?.inserted(path, moved)
        }
        PatchOperation::Copy { from, path } => {
            let copied = require(root, from)?.clone();
            root.inserted(path, copied)
        }
        PatchOperation::Test { path, value } => {
            let found = require(root, path)?;
            if found == value {
                Ok(root.clone())
            } else {
                Err(Error::validation(
                    path,
                    "patch",
                    format!(
                        "the test failed: {} holds {} instead of {}",
                        to_pointer(path),
                        found.to_json(),
                        value.to_json()
                    ),
                ))
            }
        }
    }
}

impl Patch {
    /// The patch with `prefix` added in front of every path, so it applies below a branch.
    #[must_use]
    pub fn with_prefix(&self, prefix: &[String]) -> Self {
        let lift = |path: &Vec<String>| {
            let mut lifted = prefix.to_vec();
            lifted.extend(path.iter().cloned());
            lifted
        };
        Self {
            operations: self
                .operations
                .iter()
                .map(|operation| match operation {
                    PatchOperation::Add { path, value } => PatchOperation::Add {
                        path: lift(path),
                        value: value.clone(),
                    },
                    PatchOperation::Remove { path } => PatchOperation::Remove { path: lift(path) },
                    PatchOperation::Replace { path, value } => PatchOperation::Replace {
                        path: lift(path),
                        value: value.clone(),
                    },
                    PatchOperation::Move { from, path } => PatchOperation::Move {
                        from: lift(from),
                        path: lift(path),
                    },
                    PatchOperation::Copy { from, path } => PatchOperation::Copy {
                        from: lift(from),
                        path: lift(path),
                    },
                    PatchOperation::Test { path, value } => PatchOperation::Test {
                        path: lift(path),
                        value: value.clone(),
                    },
                })
                .collect(),
        }
    }
}
