//! Portable mirrors of `crossterm::event` types for Emscripten builds.
//!
//! crossterm's `events` feature cannot compile for
//! `wasm32-unknown-emscripten` (mio has no WebAssembly support), so
//! Pyodide builds compile the event *types* from this module instead.
//! Variant sets and bitflag values are copied verbatim from
//! crossterm 0.28 so that key/mouse event data stays wire-compatible
//! with native builds. No event *source* exists on Emscripten; these
//! types only keep the binding structs and key-binding parser
//! compiling.

/// Mirror of `crossterm::event::KeyModifiers` (bitflags over `u8`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct KeyModifiers {
    bits: u8,
}

impl KeyModifiers {
    pub const SHIFT: Self = Self { bits: 0b0000_0001 };
    pub const CONTROL: Self = Self { bits: 0b0000_0010 };
    pub const ALT: Self = Self { bits: 0b0000_0100 };
    pub const SUPER: Self = Self { bits: 0b0000_1000 };
    pub const HYPER: Self = Self { bits: 0b0001_0000 };
    pub const META: Self = Self { bits: 0b0010_0000 };
    pub const NONE: Self = Self { bits: 0b0000_0000 };

    const ALL_BITS: u8 = 0b0011_1111;

    pub const fn bits(&self) -> u8 {
        self.bits
    }

    pub const fn from_bits_truncate(bits: u8) -> Self {
        Self {
            bits: bits & Self::ALL_BITS,
        }
    }

    pub const fn contains(&self, other: Self) -> bool {
        (self.bits & other.bits) == other.bits
    }
}

/// Mirror of `crossterm::event::KeyEventState` (bitflags over `u8`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct KeyEventState {
    bits: u8,
}

impl KeyEventState {
    pub const KEYPAD: Self = Self { bits: 0b0000_0001 };
    pub const CAPS_LOCK: Self = Self { bits: 0b0000_0010 };
    pub const NUM_LOCK: Self = Self { bits: 0b0000_0100 };
    pub const NONE: Self = Self { bits: 0b0000_0000 };

    const ALL_BITS: u8 = 0b0000_0111;

    pub const fn bits(&self) -> u8 {
        self.bits
    }

    pub const fn from_bits_truncate(bits: u8) -> Self {
        Self {
            bits: bits & Self::ALL_BITS,
        }
    }

    pub const fn contains(&self, other: Self) -> bool {
        (self.bits & other.bits) == other.bits
    }
}

/// Mirror of `crossterm::event::KeyEventKind`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum KeyEventKind {
    Press,
    Repeat,
    Release,
}

/// Mirror of `crossterm::event::MediaKeyCode`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MediaKeyCode {
    Play,
    Pause,
    PlayPause,
    Reverse,
    Stop,
    FastForward,
    Rewind,
    TrackNext,
    TrackPrevious,
    Record,
    LowerVolume,
    RaiseVolume,
    MuteVolume,
}

/// Mirror of `crossterm::event::ModifierKeyCode`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ModifierKeyCode {
    LeftShift,
    LeftControl,
    LeftAlt,
    LeftSuper,
    LeftHyper,
    LeftMeta,
    RightShift,
    RightControl,
    RightAlt,
    RightSuper,
    RightHyper,
    RightMeta,
    IsoLevel3Shift,
    IsoLevel5Shift,
}

/// Mirror of `crossterm::event::KeyCode`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum KeyCode {
    Backspace,
    Enter,
    Left,
    Right,
    Up,
    Down,
    Home,
    End,
    PageUp,
    PageDown,
    Tab,
    BackTab,
    Delete,
    Insert,
    F(u8),
    Char(char),
    Null,
    Esc,
    CapsLock,
    ScrollLock,
    NumLock,
    PrintScreen,
    Pause,
    Menu,
    KeypadBegin,
    Media(MediaKeyCode),
    Modifier(ModifierKeyCode),
}

/// Mirror of `crossterm::event::KeyEvent`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct KeyEvent {
    pub code: KeyCode,
    pub modifiers: KeyModifiers,
    pub kind: KeyEventKind,
    pub state: KeyEventState,
}

/// Mirror of `crossterm::event::MouseButton`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MouseButton {
    Left,
    Right,
    Middle,
}

/// Mirror of `crossterm::event::MouseEventKind`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MouseEventKind {
    Down(MouseButton),
    Up(MouseButton),
    Drag(MouseButton),
    Moved,
    ScrollDown,
    ScrollUp,
    ScrollLeft,
    ScrollRight,
}

/// Mirror of `crossterm::event::MouseEvent`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MouseEvent {
    pub kind: MouseEventKind,
    pub column: u16,
    pub row: u16,
    pub modifiers: KeyModifiers,
}
