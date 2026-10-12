//! What a terminal offers, as plain data.
//!
//! These types describe a terminal and its modes. They are always compiled, so offscreen
//! runtimes (and WebAssembly builds, which leave out the `terminal` feature) can report them
//! without linking the live terminal.

/// A status that may not be known.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Status {
    Supported,
    Unsupported,
    Unknown,
}

impl Status {
    pub fn name(self) -> &'static str {
        match self {
            Self::Supported => "supported",
            Self::Unsupported => "unsupported",
            Self::Unknown => "unknown",
        }
    }
}

/// What the terminal running this process supports.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TerminalInfo {
    pub is_terminal: bool,
    pub is_live_terminal_available: bool,
    pub color_profile: &'static str,
    pub graphics_protocol: &'static str,
    pub cell_size_in_pixels: Option<(u16, u16)>,
    pub synchronized_output: Status,
}

/// The keyboard protocol the terminal offers.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct KeyboardInfo {
    pub enhancement: Status,
    pub unavailable_reason: Option<String>,
}

/// The modes a session actually turned on.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct DeviceModes {
    pub is_raw_mode_enabled: bool,
    pub is_mouse_capture_enabled: bool,
    pub is_bracketed_paste_enabled: bool,
    pub is_focus_reporting_enabled: bool,
    pub is_alternate_screen_enabled: bool,
    pub keyboard_features: Vec<&'static str>,
}
