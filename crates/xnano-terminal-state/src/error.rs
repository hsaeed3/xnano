//! Errors raised by state operations.

use std::fmt;

/// One reason a value failed validation.
#[derive(Debug, Clone, PartialEq)]
pub struct Issue {
    /// Where in the value the problem is, as path tokens.
    pub path: Vec<String>,
    /// A full-sentence description of the problem.
    pub message: String,
    /// The schema keyword (or `patch`, `path`, `access`) that was violated.
    pub constraint: String,
}

impl Issue {
    pub fn new(path: &[String], constraint: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            path: path.to_vec(),
            message: message.into(),
            constraint: constraint.into(),
        }
    }
}

impl fmt::Display for Issue {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "at {}: {}",
            crate::node::to_pointer(&self.path),
            self.message
        )
    }
}

/// Why a state operation failed.
#[derive(Debug, Clone, PartialEq)]
pub enum Error {
    /// The value, patch or schema was rejected; nothing was published.
    Validation(Vec<Issue>),
    /// The state changed since the caller last looked at it.
    Conflict { expected: u64, actual: u64 },
    /// The operation is outside the branches the caller was granted.
    Access(String),
}

impl Error {
    pub fn validation(
        path: &[String],
        constraint: impl Into<String>,
        message: impl Into<String>,
    ) -> Self {
        Self::Validation(vec![Issue::new(path, constraint, message)])
    }
}

impl fmt::Display for Error {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Validation(issues) => {
                formatter.write_str("the state change was rejected")?;
                if issues.is_empty() {
                    return Ok(());
                }
                formatter.write_str(": ")?;
                for (index, issue) in issues.iter().take(5).enumerate() {
                    if index > 0 {
                        formatter.write_str("; ")?;
                    }
                    write!(formatter, "{issue}")?;
                }
                if issues.len() > 5 {
                    write!(formatter, "; and {} more issues", issues.len() - 5)?;
                }
                Ok(())
            }
            Self::Conflict { expected, actual } => write!(
                formatter,
                "the state changed since revision {expected}; it is now at revision {actual}. \
                 Read the state again and retry the change"
            ),
            Self::Access(message) => formatter.write_str(message),
        }
    }
}

impl std::error::Error for Error {}
