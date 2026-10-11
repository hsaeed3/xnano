//! The xnano terminal UI engine.
//!
//! Nothing here depends on Python. The crate provides:
//!
//! - [`geometry`], [`style`] and [`text`]: the value types everything else is built on;
//! - [`grid`], [`pixel`] and [`buffer`]: cells, pixels and the tree of retained buffers;
//! - [`expression`] and [`operation`]: symbolic reads and composable changes;
//! - [`layout`], [`components`], [`drawing`] and [`effects`]: arrangement, ready-made
//!   components, schema-validated drawings and animated effects;
//! - [`clock`] and [`event`]: time and normalized input;
//! - [`terminal`]: the live terminal, behind the `terminal` feature.

pub mod buffer;
pub mod clock;
pub mod components;
pub mod drawing;
pub mod dynamic;
pub mod effects;
pub mod event;
pub mod expression;
pub mod geometry;
pub mod grid;
pub mod layout;
pub mod operation;
pub mod painter;
pub mod pixel;
pub mod style;
pub mod text;
pub mod widgets;

#[cfg(feature = "terminal")]
pub mod terminal;
