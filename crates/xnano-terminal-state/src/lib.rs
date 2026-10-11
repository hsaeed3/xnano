//! Persistent, schema-validated state for xnano.
//!
//! State is independent of terminals, cells, devices and Python. A state tree holds
//! finite JSON-compatible values ([`Node`]); every commit is validated against a compiled
//! [`Schema`], published atomically and numbered with a revision. Branches that did not
//! change are shared between revisions, so a snapshot is cheap to keep.
//!
//! - [`node`]: the value tree, paths and JSON Pointer helpers.
//! - [`schema`]: the supported JSON Schema vocabulary, compiled once and validated natively.
//! - [`patch`]: JSON Patch (RFC 6902) documents.
//! - [`store`]: the [`Store`] that owns the tree, with transactions, subscriptions and
//!   observations.

pub mod error;
pub mod node;
pub mod patch;
pub mod schema;
pub mod store;

pub use error::{Error, Issue};
pub use node::{Node, Segment, parse_pointer, to_pointer};
pub use patch::{Patch, PatchOperation};
pub use schema::{Schema, SemanticRule, register_semantic_rule};
pub use store::{
    Change, Listener, Observation, Selection, Snapshot, Store, SubscriptionHandle, Transaction,
};
