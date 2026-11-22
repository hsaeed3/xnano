//! Fonts made of characters or pixels, text written in them, and terminal frames as images.
//!
//! - [`font`]: FIGlet (`.flf`) and BDF (`.bdf`) fonts, and the built-in pixel fonts, which
//!   are the public domain xorg misc-misc fonts.
//! - [`text`]: text written in a font, as rows of characters a terminal can show.
//! - [`image`]: a ratatui buffer drawn as RGB pixels and encoded as PNG.
//!
//! The crate knows nothing about Python.

pub mod font;
pub mod image;
pub mod text;

pub use font::{BUILTIN_FONT_NAMES, Font, FontError, FontKind};
pub use image::{Pixmap, render_buffer};
pub use text::{measure_text, render_text};
