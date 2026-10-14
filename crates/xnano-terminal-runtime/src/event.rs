//! Normalized input and scheduling events, with no backend-specific types.

use crate::geometry::{Point, Size};

/// The modifier keys held during a key event.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
pub struct KeyModifiers(pub u8);

impl KeyModifiers {
    pub const CONTROL: u8 = 1;
    pub const SHIFT: u8 = 2;
    pub const ALT: u8 = 4;
    pub const SUPER: u8 = 8;
    pub const META: u8 = 16;
    pub const HYPER: u8 = 32;

    pub const NAMES: [(&'static str, u8); 6] = [
        ("control", Self::CONTROL),
        ("shift", Self::SHIFT),
        ("alt", Self::ALT),
        ("super", Self::SUPER),
        ("meta", Self::META),
        ("hyper", Self::HYPER),
    ];

    pub fn contains(self, flag: u8) -> bool {
        self.0 & flag == flag
    }

    pub fn insert(&mut self, flag: u8) {
        self.0 |= flag;
    }

    pub fn names(self) -> Vec<&'static str> {
        Self::NAMES
            .iter()
            .filter(|(_, flag)| self.contains(*flag))
            .map(|(name, _)| *name)
            .collect()
    }

    pub fn from_name(name: &str) -> Option<u8> {
        let normalized = name.trim().to_ascii_lowercase();
        Some(match normalized.as_str() {
            "ctrl" | "control" | "ctl" => Self::CONTROL,
            "shift" => Self::SHIFT,
            "alt" | "option" | "opt" => Self::ALT,
            "super" | "cmd" | "command" | "win" | "windows" => Self::SUPER,
            "meta" => Self::META,
            "hyper" => Self::HYPER,
            _ => return None,
        })
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum KeyKind {
    Press,
    Repeat,
    Release,
}

impl KeyKind {
    pub fn name(self) -> &'static str {
        match self {
            Self::Press => "press",
            Self::Repeat => "repeat",
            Self::Release => "release",
        }
    }

    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "press" => Self::Press,
            "repeat" => Self::Repeat,
            "release" => Self::Release,
            _ => return None,
        })
    }
}

/// A key press, repeat or release.
///
/// `key` is the key's name: a lowercase character (`"a"`, `"?"`), or one of `enter`,
/// `tab`, `backspace`, `delete`, `escape`, `space`, `up`, `down`, `left`, `right`, `home`,
/// `end`, `page_up`, `page_down`, `insert` and `f1` to `f24`. `text` holds what the key
/// types, when it types something.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct KeyEvent {
    pub key: String,
    pub text: Option<String>,
    pub modifiers: KeyModifiers,
    pub kind: KeyKind,
}

/// A key (and modifiers) to match against key events.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct KeyBinding {
    pub key: String,
    pub modifiers: KeyModifiers,
}

fn canonical_key_name(name: &str) -> String {
    let lowered = name.to_ascii_lowercase();
    match lowered.as_str() {
        "esc" => "escape".to_owned(),
        "return" | "cr" => "enter".to_owned(),
        "del" => "delete".to_owned(),
        "ins" => "insert".to_owned(),
        "pgup" | "pageup" | "page up" => "page_up".to_owned(),
        "pgdn" | "pagedown" | "page down" => "page_down".to_owned(),
        "spacebar" | " " => "space".to_owned(),
        "bs" => "backspace".to_owned(),
        "arrowup" => "up".to_owned(),
        "arrowdown" => "down".to_owned(),
        "arrowleft" => "left".to_owned(),
        "arrowright" => "right".to_owned(),
        _ => lowered,
    }
}

impl KeyBinding {
    /// Parse text such as `"q"`, `"ctrl+c"`, `"shift+tab"`, `"alt+enter"` or `"ctrl++"`.
    pub fn parse(text: &str) -> Result<Self, String> {
        let trimmed = text.trim_matches(|character: char| character == '\t' || character == '\n');
        if trimmed.is_empty() {
            return Err(
                "a key binding cannot be empty; use a key such as \"q\" or \"ctrl+c\"".to_owned(),
            );
        }
        let (modifier_text, key_text) = if trimmed == "+" {
            ("", "+")
        } else if let Some(prefix) = trimmed.strip_suffix("++") {
            (prefix, "+")
        } else if let Some(position) = trimmed.rfind('+') {
            (&trimmed[..position], &trimmed[position + 1..])
        } else {
            ("", trimmed)
        };
        let mut modifiers = KeyModifiers::default();
        if !modifier_text.is_empty() {
            for part in modifier_text.split('+') {
                let flag = KeyModifiers::from_name(part).ok_or_else(|| {
                    format!(
                        "\"{part}\" in the key binding \"{text}\" is not a modifier; use ctrl, \
                         shift, alt, super, meta or hyper"
                    )
                })?;
                modifiers.insert(flag);
            }
        }
        if key_text.is_empty() {
            return Err(format!(
                "the key binding \"{text}\" has no key after its modifiers; end it with a key such as \"c\""
            ));
        }
        let mut key = canonical_key_name(key_text);
        if key == "backtab" {
            "tab".clone_into(&mut key);
            modifiers.insert(KeyModifiers::SHIFT);
        }
        let mut characters = key_text.chars();
        if let (Some(character), None) = (characters.next(), characters.next())
            && character.is_alphabetic()
            && character.is_uppercase()
        {
            modifiers.insert(KeyModifiers::SHIFT);
        }
        Ok(Self { key, modifiers })
    }

    pub fn matches(&self, event: &KeyEvent) -> bool {
        self.key == event.key && self.modifiers == event.modifiers
    }
}

impl KeyEvent {
    /// Build the event for a binding string such as `"ctrl+c"`.
    pub fn from_binding(binding: &str, kind: KeyKind) -> Result<Self, String> {
        let parsed = KeyBinding::parse(binding)?;
        let is_plain = parsed.modifiers.0 & !KeyModifiers::SHIFT == 0;
        let text = if is_plain {
            if parsed.key == "space" {
                Some(" ".to_owned())
            } else if parsed.key.chars().count() == 1 {
                let character = parsed.key.chars().next().unwrap_or(' ');
                Some(if parsed.modifiers.contains(KeyModifiers::SHIFT) {
                    character.to_uppercase().collect()
                } else {
                    character.to_string()
                })
            } else {
                None
            }
        } else {
            None
        };
        Ok(Self {
            key: parsed.key,
            text: if kind == KeyKind::Release { None } else { text },
            modifiers: parsed.modifiers,
            kind,
        })
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MouseKind {
    Press,
    Release,
    Drag,
    Move,
    Scroll,
}

impl MouseKind {
    pub fn name(self) -> &'static str {
        match self {
            Self::Press => "press",
            Self::Release => "release",
            Self::Drag => "drag",
            Self::Move => "move",
            Self::Scroll => "scroll",
        }
    }

    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "press" => Self::Press,
            "release" => Self::Release,
            "drag" => Self::Drag,
            "move" => Self::Move,
            "scroll" => Self::Scroll,
            _ => return None,
        })
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MouseButton {
    Left,
    Right,
    Middle,
}

impl MouseButton {
    pub fn name(self) -> &'static str {
        match self {
            Self::Left => "left",
            Self::Right => "right",
            Self::Middle => "middle",
        }
    }

    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "left" => Self::Left,
            "right" => Self::Right,
            "middle" => Self::Middle,
            _ => return None,
        })
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MouseEvent {
    pub column: i32,
    pub row: i32,
    pub kind: MouseKind,
    pub button: Option<MouseButton>,
    pub scroll_horizontal: i32,
    pub scroll_vertical: i32,
}

impl MouseEvent {
    pub fn position(&self) -> Point {
        Point::new(self.column, self.row)
    }
}

/// What kind of event this is.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum EventKind {
    Key,
    Mouse,
    Paste,
    Resize,
    FocusGained,
    FocusLost,
    Tick,
    Timer,
    Frame,
    Wake,
    ExitRequested,
    /// An event an application defines and injects itself.
    Custom,
}

impl EventKind {
    pub const ALL: [(&'static str, Self); 12] = [
        ("key", Self::Key),
        ("mouse", Self::Mouse),
        ("paste", Self::Paste),
        ("resize", Self::Resize),
        ("focus_gained", Self::FocusGained),
        ("focus_lost", Self::FocusLost),
        ("tick", Self::Tick),
        ("timer", Self::Timer),
        ("frame", Self::Frame),
        ("wake", Self::Wake),
        ("exit_requested", Self::ExitRequested),
        ("custom", Self::Custom),
    ];

    pub fn name(self) -> &'static str {
        Self::ALL
            .iter()
            .find(|(_, kind)| *kind == self)
            .map_or("unknown", |(name, _)| name)
    }

    pub fn from_name(name: &str) -> Option<Self> {
        Self::ALL
            .iter()
            .find(|(candidate, _)| *candidate == name)
            .map(|(_, kind)| *kind)
    }

    /// Whether the event comes from the person using the terminal.
    pub fn is_input(self) -> bool {
        matches!(self, Self::Key | Self::Mouse | Self::Paste)
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum EventPayload {
    None,
    Key(KeyEvent),
    Mouse(MouseEvent),
    Paste(String),
    Size(Size),
    Timer(String),
    Signal(i32),
    /// A named application event with optional text data.
    Custom {
        name: String,
        data: Option<String>,
    },
}

/// One thing that happened, with the time it was queued.
#[derive(Debug, Clone, PartialEq)]
pub struct Event {
    pub kind: EventKind,
    pub timestamp_seconds: f64,
    pub payload: EventPayload,
}

impl Event {
    pub fn new(kind: EventKind, payload: EventPayload) -> Self {
        Self {
            kind,
            timestamp_seconds: 0.0,
            payload,
        }
    }

    pub fn key(&self) -> Option<&KeyEvent> {
        match &self.payload {
            EventPayload::Key(key) => Some(key),
            _ => None,
        }
    }

    pub fn mouse(&self) -> Option<&MouseEvent> {
        match &self.payload {
            EventPayload::Mouse(mouse) => Some(mouse),
            _ => None,
        }
    }
}

#[cfg(feature = "terminal")]
pub mod terminal {
    //! Conversion from crossterm events.

    use super::{
        Event, EventKind, EventPayload, KeyEvent, KeyKind, KeyModifiers, MouseButton, MouseEvent,
        MouseKind,
    };
    use crate::geometry::Size;
    use crossterm::event as ct;

    fn modifiers(source: ct::KeyModifiers) -> KeyModifiers {
        let mut result = KeyModifiers::default();
        for (flag, ours) in [
            (ct::KeyModifiers::CONTROL, KeyModifiers::CONTROL),
            (ct::KeyModifiers::SHIFT, KeyModifiers::SHIFT),
            (ct::KeyModifiers::ALT, KeyModifiers::ALT),
            (ct::KeyModifiers::SUPER, KeyModifiers::SUPER),
            (ct::KeyModifiers::META, KeyModifiers::META),
            (ct::KeyModifiers::HYPER, KeyModifiers::HYPER),
        ] {
            if source.contains(flag) {
                result.insert(ours);
            }
        }
        result
    }

    fn mouse_button(button: ct::MouseButton) -> MouseButton {
        match button {
            ct::MouseButton::Left => MouseButton::Left,
            ct::MouseButton::Right => MouseButton::Right,
            ct::MouseButton::Middle => MouseButton::Middle,
        }
    }

    fn key_event(source: ct::KeyEvent) -> KeyEvent {
        let mut held = modifiers(source.modifiers);
        let (key, text) = match source.code {
            ct::KeyCode::Char(' ') => ("space".to_owned(), Some(" ".to_owned())),
            ct::KeyCode::Char(character) => {
                if !character.is_alphabetic() {
                    // Shift is already part of a symbol such as "?".
                    held.0 &= !KeyModifiers::SHIFT;
                } else if character.is_uppercase() {
                    held.insert(KeyModifiers::SHIFT);
                }
                (
                    character.to_lowercase().collect::<String>(),
                    Some(character.to_string()),
                )
            }
            ct::KeyCode::Enter => ("enter".to_owned(), None),
            ct::KeyCode::Tab => ("tab".to_owned(), None),
            ct::KeyCode::BackTab => {
                held.insert(KeyModifiers::SHIFT);
                ("tab".to_owned(), None)
            }
            ct::KeyCode::Backspace => ("backspace".to_owned(), None),
            ct::KeyCode::Delete => ("delete".to_owned(), None),
            ct::KeyCode::Esc => ("escape".to_owned(), None),
            ct::KeyCode::Up => ("up".to_owned(), None),
            ct::KeyCode::Down => ("down".to_owned(), None),
            ct::KeyCode::Left => ("left".to_owned(), None),
            ct::KeyCode::Right => ("right".to_owned(), None),
            ct::KeyCode::Home => ("home".to_owned(), None),
            ct::KeyCode::End => ("end".to_owned(), None),
            ct::KeyCode::PageUp => ("page_up".to_owned(), None),
            ct::KeyCode::PageDown => ("page_down".to_owned(), None),
            ct::KeyCode::Insert => ("insert".to_owned(), None),
            ct::KeyCode::F(number) => (format!("f{number}"), None),
            ct::KeyCode::CapsLock => ("caps_lock".to_owned(), None),
            ct::KeyCode::ScrollLock => ("scroll_lock".to_owned(), None),
            ct::KeyCode::NumLock => ("num_lock".to_owned(), None),
            ct::KeyCode::PrintScreen => ("print_screen".to_owned(), None),
            ct::KeyCode::Pause => ("pause".to_owned(), None),
            ct::KeyCode::Menu => ("menu".to_owned(), None),
            ct::KeyCode::Null => ("null".to_owned(), None),
            _ => ("unknown".to_owned(), None),
        };
        let kind = match source.kind {
            ct::KeyEventKind::Press => KeyKind::Press,
            ct::KeyEventKind::Repeat => KeyKind::Repeat,
            ct::KeyEventKind::Release => KeyKind::Release,
        };
        // Control and alt chords type nothing.
        let text = if held.contains(KeyModifiers::CONTROL) || held.contains(KeyModifiers::ALT) {
            None
        } else {
            text
        };
        KeyEvent {
            key,
            text: if kind == KeyKind::Release { None } else { text },
            modifiers: held,
            kind,
        }
    }

    /// Convert a crossterm event, or `None` for events xnano does not report.
    pub fn from_crossterm(source: ct::Event) -> Option<Event> {
        Some(match source {
            ct::Event::Key(key) => Event::new(EventKind::Key, EventPayload::Key(key_event(key))),
            ct::Event::Mouse(mouse) => {
                let (kind, button, horizontal, vertical) = match mouse.kind {
                    ct::MouseEventKind::Down(button) => {
                        (MouseKind::Press, Some(mouse_button(button)), 0, 0)
                    }
                    ct::MouseEventKind::Up(button) => {
                        (MouseKind::Release, Some(mouse_button(button)), 0, 0)
                    }
                    ct::MouseEventKind::Drag(button) => {
                        (MouseKind::Drag, Some(mouse_button(button)), 0, 0)
                    }
                    ct::MouseEventKind::Moved => (MouseKind::Move, None, 0, 0),
                    ct::MouseEventKind::ScrollUp => (MouseKind::Scroll, None, 0, -1),
                    ct::MouseEventKind::ScrollDown => (MouseKind::Scroll, None, 0, 1),
                    ct::MouseEventKind::ScrollLeft => (MouseKind::Scroll, None, -1, 0),
                    ct::MouseEventKind::ScrollRight => (MouseKind::Scroll, None, 1, 0),
                };
                Event::new(
                    EventKind::Mouse,
                    EventPayload::Mouse(MouseEvent {
                        column: i32::from(mouse.column),
                        row: i32::from(mouse.row),
                        kind,
                        button,
                        scroll_horizontal: horizontal,
                        scroll_vertical: vertical,
                    }),
                )
            }
            ct::Event::Paste(text) => Event::new(EventKind::Paste, EventPayload::Paste(text)),
            ct::Event::Resize(width, height) => Event::new(
                EventKind::Resize,
                EventPayload::Size(Size::new(i32::from(width), i32::from(height))),
            ),
            ct::Event::FocusGained => Event::new(EventKind::FocusGained, EventPayload::None),
            ct::Event::FocusLost => Event::new(EventKind::FocusLost, EventPayload::None),
        })
    }
}
