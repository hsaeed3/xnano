//! The live terminal: capability queries, input, modes and frame presentation.
//!
//! Everything that touches the real terminal lives here, behind the `terminal` feature, so
//! offscreen runtimes (and WebAssembly builds) never link it.

use std::io::{self, IsTerminal, Read, Write, stdout};
use std::sync::atomic::AtomicUsize;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Once};
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

use crossterm::cursor::{MoveTo, SetCursorStyle, Show};
use crossterm::event::{
    DisableBracketedPaste, DisableFocusChange, EnableBracketedPaste, EnableFocusChange,
    KeyboardEnhancementFlags, PopKeyboardEnhancementFlags, PushKeyboardEnhancementFlags,
};
use crossterm::style::{Attribute, ResetColor, SetAttribute};
use crossterm::terminal::{
    BeginSynchronizedUpdate, EnableLineWrap, EndSynchronizedUpdate, EnterAlternateScreen,
    LeaveAlternateScreen, disable_raw_mode, enable_raw_mode,
};
use crossterm::{ExecutableCommand, QueueableCommand};
use ratatui::backend::CrosstermBackend;
use ratatui::{Terminal, TerminalOptions as RatatuiOptions, Viewport};
use ratatui_core::layout::Rect;
use termprofile::{DetectorSettings, TermProfile};

use crate::event::{Event, EventKind, EventPayload, terminal::from_crossterm};
use crate::geometry::{Point, Size};
use crate::grid::{Grid, is_protocol_cell};

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

/// What the terminal said when asked.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct Replies {
    pub is_kitty_graphics_supported: bool,
    pub is_sixel_supported: bool,
    pub cell_size_in_pixels: Option<(u16, u16)>,
    pub is_synchronized_output_supported: Option<bool>,
    /// The kitty keyboard protocol flags the terminal reported, when it answered.
    pub keyboard_flags: Option<u32>,
    /// Whether the primary device attributes reply, which ends every exchange, arrived.
    pub did_finish: bool,
}

/// Whether `data` holds a primary device attributes reply (`ESC [ ? attributes c`).
fn has_device_attributes_reply(data: &str) -> bool {
    data.split("\x1b[?").skip(1).any(|part| {
        let end = part
            .find(|character: char| !(character.is_ascii_digit() || character == ';'))
            .unwrap_or(part.len());
        part[end..].starts_with('c')
    })
}

/// Parse everything the terminal sent back.
pub fn parse_replies(data: &str) -> Replies {
    let mut replies = Replies::default();
    if data.contains("\x1b_Gi=31;OK") {
        replies.is_kitty_graphics_supported = true;
    }
    for part in data.split("\x1b[?").skip(1) {
        if let Some(end) = part.find('c') {
            let attributes = &part[..end];
            if attributes
                .chars()
                .all(|character| character.is_ascii_digit() || character == ';')
            {
                if attributes.split(';').any(|attribute| attribute == "4") {
                    replies.is_sixel_supported = true;
                }
                replies.did_finish = true;
            }
        }
        if let Some(rest) = part.strip_prefix("2026;")
            && let Some(state) = rest.split('$').next()
        {
            replies.is_synchronized_output_supported = Some(matches!(state, "1" | "2" | "3"));
        }
        // Kitty keyboard protocol: ESC [ ? flags u
        let digits: String = part.chars().take_while(char::is_ascii_digit).collect();
        if !digits.is_empty() && part[digits.len()..].starts_with('u') {
            replies.keyboard_flags = digits.parse().ok();
        }
    }
    if let Some(start) = data.find("\x1b[6;") {
        let rest = &data[start + 4..];
        if let Some(end) = rest.find('t') {
            let mut numbers = rest[..end]
                .split(';')
                .filter_map(|value| value.parse::<u16>().ok());
            if let (Some(height), Some(width)) = (numbers.next(), numbers.next())
                && width > 0
                && height > 0
            {
                replies.cell_size_in_pixels = Some((width, height));
            }
        }
    }
    replies
}

/// Wait up to `timeout` for input on standard input.
#[cfg(unix)]
fn wait_for_input(timeout: Duration) -> bool {
    use rustix::event::{PollFd, PollFlags, Timespec, poll};
    let stdin = io::stdin();
    let mut descriptors = [PollFd::new(&stdin, PollFlags::IN)];
    let timeout = Timespec {
        tv_sec: timeout.as_secs() as _,
        tv_nsec: i64::from(timeout.subsec_nanos()) as _,
    };
    matches!(poll(&mut descriptors, Some(&timeout)), Ok(count) if count > 0)
}

#[cfg(not(unix))]
fn wait_for_input(timeout: Duration) -> bool {
    crossterm::event::poll(timeout).unwrap_or(false)
}

/// Ask the terminal about graphics, synchronized output, cell size and the keyboard.
///
/// Returns `None` when there is no terminal to ask. The exchange ends with the primary
/// device attributes request, which every terminal answers, so a terminal that does not
/// know the other queries still ends the wait early.
#[cfg(unix)]
pub fn query_terminal(timeout: Duration) -> Option<Replies> {
    if !(stdout().is_terminal() && io::stdin().is_terminal()) {
        return None;
    }
    let was_raw = crossterm::terminal::is_raw_mode_enabled().unwrap_or(false);
    if !was_raw {
        enable_raw_mode().ok()?;
    }
    let query = "\x1b_Gi=31,s=1,v=1,a=q,t=d,f=24;AAAA\x1b\\\x1b[?2026$p\x1b[16t\x1b[?u\x1b[c";
    let mut output = stdout();
    let written = output
        .write_all(query.as_bytes())
        .and_then(|()| output.flush());
    let mut received = Vec::new();
    if written.is_ok() {
        let deadline = Instant::now() + timeout;
        let mut chunk = [0_u8; 512];
        loop {
            let remaining = deadline.saturating_duration_since(Instant::now());
            if remaining.is_zero() || !wait_for_input(remaining) {
                break;
            }
            match io::stdin().lock().read(&mut chunk) {
                Ok(0) | Err(_) => break,
                Ok(count) => received.extend_from_slice(&chunk[..count]),
            }
            if has_device_attributes_reply(&String::from_utf8_lossy(&received)) {
                break;
            }
        }
    }
    if !was_raw {
        let _ = disable_raw_mode();
    }
    written.ok()?;
    Some(parse_replies(&String::from_utf8_lossy(&received)))
}

#[cfg(not(unix))]
pub fn query_terminal(_timeout: Duration) -> Option<Replies> {
    None
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

fn color_profile_name(profile: TermProfile) -> &'static str {
    match profile {
        TermProfile::NoTty => "no_terminal",
        TermProfile::NoColor => "no_color",
        TermProfile::Ansi16 => "ansi16",
        TermProfile::Ansi256 => "ansi256",
        TermProfile::TrueColor => "truecolor",
    }
}

/// The keyboard protocol the terminal offers.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct KeyboardInfo {
    pub enhancement: Status,
    pub unavailable_reason: Option<String>,
}

/// Everything one terminal query learns.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Probe {
    pub terminal: TerminalInfo,
    pub keyboard: KeyboardInfo,
}

fn keyboard_from(is_terminal: bool, replies: Option<&Replies>, timeout: Duration) -> KeyboardInfo {
    if !is_terminal {
        return KeyboardInfo {
            enhancement: Status::Unsupported,
            unavailable_reason: Some(
                "standard input and output are not a terminal, so there is no keyboard to query"
                    .to_owned(),
            ),
        };
    }
    match replies {
        None => KeyboardInfo {
            enhancement: Status::Unknown,
            unavailable_reason: Some("the terminal could not be queried".to_owned()),
        },
        Some(replies) if replies.keyboard_flags.is_some() => KeyboardInfo {
            enhancement: Status::Supported,
            unavailable_reason: None,
        },
        Some(replies) if replies.did_finish => KeyboardInfo {
            enhancement: Status::Unsupported,
            unavailable_reason: Some(
                "the terminal answered but does not support the kitty keyboard protocol".to_owned(),
            ),
        },
        Some(_) => KeyboardInfo {
            enhancement: Status::Unknown,
            unavailable_reason: Some(format!(
                "the terminal did not answer within {} milliseconds",
                timeout.as_millis()
            )),
        },
    }
}

/// Ask the terminal what it supports, falling back to the environment when it is silent.
///
/// A terminal that never answers yields `Unknown` statuses, never an error.
pub fn probe(timeout: Duration) -> Probe {
    let is_terminal = stdout().is_terminal() && io::stdin().is_terminal();
    let profile = TermProfile::detect(&stdout(), DetectorSettings::default());
    let is_inside_tmux = std::env::var_os("TMUX").is_some();
    let replies = if is_terminal {
        query_terminal(timeout)
    } else {
        None
    };
    let known = replies.clone().unwrap_or_default();
    let program = std::env::var("TERM_PROGRAM").unwrap_or_default();
    let is_iterm2_like = matches!(program.as_str(), "iTerm.app" | "WezTerm" | "vscode")
        || std::env::var_os("ITERM_SESSION_ID").is_some();
    let graphics_protocol = if !is_terminal || is_inside_tmux {
        "half_blocks"
    } else if known.is_kitty_graphics_supported {
        "kitty"
    } else if known.is_sixel_supported {
        "sixel"
    } else if is_iterm2_like {
        "iterm2"
    } else {
        "half_blocks"
    };
    Probe {
        terminal: TerminalInfo {
            is_terminal,
            is_live_terminal_available: true,
            color_profile: color_profile_name(profile),
            graphics_protocol,
            cell_size_in_pixels: known.cell_size_in_pixels,
            synchronized_output: match known.is_synchronized_output_supported {
                Some(true) => Status::Supported,
                Some(false) => Status::Unsupported,
                None => Status::Unknown,
            },
        },
        keyboard: keyboard_from(is_terminal, replies.as_ref(), timeout),
    }
}

/// Find out what the terminal supports.
pub fn detect_terminal(timeout: Duration) -> TerminalInfo {
    probe(timeout).terminal
}

/// Ask whether the terminal supports richer key reporting. Asking enables nothing.
pub fn query_keyboard(timeout: Duration) -> KeyboardInfo {
    probe(timeout).keyboard
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MouseCapture {
    Off,
    Buttons,
    Motion,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum KeyboardMode {
    Basic,
    Disambiguated,
    ReleaseEvents,
}

/// How a live session sets up the terminal.
#[derive(Debug, Clone)]
pub struct SessionOptions {
    pub mouse: MouseCapture,
    pub bracketed_paste: bool,
    pub focus_reporting: bool,
    pub keyboard: KeyboardMode,
    pub capability_timeout: Duration,
    pub alternate_screen: bool,
    pub raw_mode: bool,
    pub drain_reports_on_exit: bool,
    pub drain_timeout: Duration,
    pub inline_height: Option<u16>,
    pub should_handle_exit_signals: bool,
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

/// Rolls back terminal modes if taking over the terminal fails halfway through.
#[derive(Default)]
struct TerminalSetupGuard {
    modes: DeviceModes,
    armed: bool,
}

impl Drop for TerminalSetupGuard {
    fn drop(&mut self) {
        if !self.armed {
            return;
        }
        let mut output = stdout();
        if self.modes.is_alternate_screen_enabled {
            let _ = output.execute(LeaveAlternateScreen);
        }
        if self.modes.is_raw_mode_enabled {
            let _ = disable_raw_mode();
        }
        emit_reset_sequences();
        let _ = output.flush();
    }
}

pub type EventSink = Arc<dyn Fn(Event) + Send + Sync>;

/// Best-effort reset used on every exit path. Errors are ignored.
const RESET_BLOB: &[u8] = b"\
\x1b[!p\x0f\x1b(B\x1b)B\x1b[0m\x1b[39m\x1b[49m\x1b[59m\x1b[?25h\x1b[0 q\x1b[?7h\
\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1005l\x1b[?1006l\x1b[?1015l\x1b[?1004l\
\x1b[?2004l\x1b[?2026l";

/// Leave every private mode the session may have armed.
pub fn emit_reset_sequences() {
    let mut out = stdout();
    let _ = out.execute(EndSynchronizedUpdate);
    let _ = out.execute(DisableBracketedPaste);
    let _ = out.execute(DisableFocusChange);
    let _ = out.execute(PopKeyboardEnhancementFlags);
    let _ = out.execute(Show);
    let _ = out.execute(SetCursorStyle::DefaultUserShape);
    let _ = out.execute(EnableLineWrap);
    let _ = out.execute(ResetColor);
    let _ = out.execute(SetAttribute(Attribute::Reset));
    let _ = out.write_all(RESET_BLOB);
    let _ = out.flush();
}

thread_local! {
    static IS_PANIC_GUARDED: std::cell::Cell<bool> = const { std::cell::Cell::new(false) };
}

/// Restore the previous panic-suppression state, including across nested guards.
struct PanicScope(bool);

impl PanicScope {
    fn enter() -> Self {
        Self(IS_PANIC_GUARDED.with(|flag| flag.replace(true)))
    }
}

impl Drop for PanicScope {
    fn drop(&mut self) {
        IS_PANIC_GUARDED.with(|flag| flag.set(self.0));
    }
}

/// Run `body` so a panic inside it is reported to the caller instead of resetting the
/// terminal under the interface.
pub fn guard_panics<T>(body: impl FnOnce() -> T) -> Result<T, String> {
    let _scope = PanicScope::enter();
    let outcome = std::panic::catch_unwind(std::panic::AssertUnwindSafe(body));
    outcome.map_err(|payload| {
        payload
            .downcast_ref::<&str>()
            .map(|message| (*message).to_owned())
            .or_else(|| payload.downcast_ref::<String>().cloned())
            .unwrap_or_else(|| "an unknown internal error".to_owned())
    })
}

type PanicHook = Arc<dyn Fn(&std::panic::PanicHookInfo<'_>) + Sync + Send>;

static PANIC_HOOK_INSTALL: Once = Once::new();
static ACTIVE_TERMINAL_SESSIONS: AtomicUsize = AtomicUsize::new(0);

/// Puts the terminal back when a panic escapes while a live session exists.
struct PanicGuard;

impl PanicGuard {
    fn install() -> Self {
        PANIC_HOOK_INSTALL.call_once(|| {
            let previous: PanicHook = Arc::from(std::panic::take_hook());
            let hook = Arc::clone(&previous);
            std::panic::set_hook(Box::new(move |info| {
                if IS_PANIC_GUARDED.with(std::cell::Cell::get) {
                    return;
                }
                if ACTIVE_TERMINAL_SESSIONS.load(Ordering::SeqCst) > 0 {
                    let _ = disable_raw_mode();
                    let _ = stdout().execute(LeaveAlternateScreen);
                    emit_reset_sequences();
                }
                hook(info);
            }));
        });
        ACTIVE_TERMINAL_SESSIONS.fetch_add(1, Ordering::SeqCst);
        Self
    }
}

impl Drop for PanicGuard {
    fn drop(&mut self) {
        ACTIVE_TERMINAL_SESSIONS.fetch_sub(1, Ordering::SeqCst);
    }
}

#[cfg(unix)]
mod exit_signals {
    //! `SIGTERM` and `SIGHUP` while a live session is open.
    //!
    //! The first becomes an `exit_requested` event so the application can shut down; a
    //! second restores the terminal and exits.

    use super::{Event, EventKind, EventPayload, EventSink, emit_reset_sequences};
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::sync::{Arc, Mutex, Once, Weak};

    use signal_hook::consts::{SIGHUP, SIGTERM};
    use signal_hook::iterator::Signals;

    static SINKS: Mutex<Vec<Weak<dyn Fn(Event) + Send + Sync>>> = Mutex::new(Vec::new());
    static IS_EXIT_REQUESTED: AtomicBool = AtomicBool::new(false);
    static LISTENER: Once = Once::new();

    fn live_sinks() -> Vec<EventSink> {
        let mut sinks = SINKS
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        sinks.retain(|sink| sink.strong_count() > 0);
        sinks.iter().filter_map(Weak::upgrade).collect()
    }

    fn handle(signal: i32) {
        let sinks = live_sinks();
        if sinks.is_empty() {
            let _ = signal_hook::low_level::emulate_default_handler(signal);
            return;
        }
        if IS_EXIT_REQUESTED.swap(true, Ordering::SeqCst) {
            let _ = crossterm::terminal::disable_raw_mode();
            emit_reset_sequences();
            std::process::exit(128 + signal);
        }
        for sink in sinks {
            sink(Event::new(
                EventKind::ExitRequested,
                EventPayload::Signal(signal),
            ));
        }
    }

    pub fn register(sink: &EventSink) {
        LISTENER.call_once(|| {
            if let Ok(mut signals) = Signals::new([SIGTERM, SIGHUP]) {
                let _ = std::thread::Builder::new()
                    .name("xnano-exit-signals".into())
                    .spawn(move || {
                        for signal in signals.forever() {
                            handle(signal);
                        }
                    });
            }
        });
        SINKS
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .push(Arc::downgrade(sink));
    }

    pub fn unregister(sink: &EventSink) {
        let mut sinks = SINKS
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        sinks.retain(|candidate| {
            candidate
                .upgrade()
                .is_some_and(|other| !Arc::ptr_eq(&other, sink))
        });
        if sinks.is_empty() {
            IS_EXIT_REQUESTED.store(false, Ordering::SeqCst);
        }
    }
}

/// Reads terminal input on its own thread and hands each event to the sink.
struct InputReader {
    should_stop: Arc<AtomicBool>,
    handle: Option<JoinHandle<()>>,
}

impl InputReader {
    fn spawn(sink: EventSink) -> Self {
        let should_stop = Arc::new(AtomicBool::new(false));
        let flag = Arc::clone(&should_stop);
        let handle = std::thread::Builder::new()
            .name("xnano-input".into())
            .spawn(move || {
                while !flag.load(Ordering::SeqCst) {
                    match crossterm::event::poll(Duration::from_millis(20)) {
                        Ok(true) => match crossterm::event::read() {
                            Ok(event) => {
                                if let Some(event) = from_crossterm(event) {
                                    sink(event);
                                }
                            }
                            Err(_) => break,
                        },
                        Ok(false) => {}
                        Err(_) => break,
                    }
                }
            })
            .ok();
        Self {
            should_stop,
            handle,
        }
    }

    fn stop(&mut self) {
        self.should_stop.store(true, Ordering::SeqCst);
        if let Some(handle) = self.handle.take() {
            let _ = handle.join();
        }
    }
}

impl Drop for InputReader {
    fn drop(&mut self) {
        self.stop();
    }
}

/// A fingerprint of the terminal graphics images in a frame.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
struct GraphicsSignature {
    area: (u16, u16, u16, u16),
    anchors: u64,
    cells: u64,
}

fn graphics_signature(grid: &Grid) -> Option<GraphicsSignature> {
    use std::hash::{Hash, Hasher};
    let buffer = grid.buffer();
    let (mut left, mut top, mut right, mut bottom) = (u16::MAX, u16::MAX, 0_u16, 0_u16);
    let mut anchors = std::collections::hash_map::DefaultHasher::new();
    let mut found = false;
    for y in 0..grid.height() {
        for x in 0..grid.width() {
            let Some(cell) = buffer.cell((x, y)) else {
                continue;
            };
            if is_protocol_cell(cell) {
                found = true;
                left = left.min(x);
                top = top.min(y);
                right = right.max(x + 1);
                bottom = bottom.max(y + 1);
                if cell.symbol().starts_with('\x1b') {
                    (x, y, cell.symbol()).hash(&mut anchors);
                }
            }
        }
    }
    if !found {
        return None;
    }
    let mut cells = std::collections::hash_map::DefaultHasher::new();
    for y in top..bottom {
        for x in left..right {
            if let Some(cell) = buffer.cell((x, y)) {
                cell.symbol().hash(&mut cells);
                cell.style().hash(&mut cells);
            }
        }
    }
    Some(GraphicsSignature {
        area: (left, top, right, bottom),
        anchors: anchors.finish(),
        cells: cells.finish(),
    })
}

/// A live terminal session.
pub struct TerminalSession {
    terminal: Terminal<CrosstermBackend<io::Stdout>>,
    options: SessionOptions,
    modes: DeviceModes,
    input: Option<InputReader>,
    sink: EventSink,
    last_graphics: Option<GraphicsSignature>,
    last_area: Rect,
    _panic_guard: PanicGuard,
}

impl TerminalSession {
    /// Take over the terminal.
    pub fn open(
        options: SessionOptions,
        keyboard: Option<&KeyboardInfo>,
        sink: EventSink,
    ) -> io::Result<Self> {
        let panic_guard = PanicGuard::install();
        let mut setup = TerminalSetupGuard::default();
        setup.armed = true;
        let mut output = stdout();
        if options.raw_mode {
            enable_raw_mode()?;
            setup.modes.is_raw_mode_enabled = true;
        }
        let is_inline = options.inline_height.is_some();
        if options.alternate_screen && !is_inline {
            output.execute(EnterAlternateScreen)?;
            setup.modes.is_alternate_screen_enabled = true;
        }
        match options.mouse {
            MouseCapture::Off => {}
            MouseCapture::Buttons => {
                output.write_all(b"\x1b[?1000h\x1b[?1002h\x1b[?1006h")?;
                setup.modes.is_mouse_capture_enabled = true;
            }
            MouseCapture::Motion => {
                output.write_all(b"\x1b[?1000h\x1b[?1002h\x1b[?1003h\x1b[?1006h")?;
                setup.modes.is_mouse_capture_enabled = true;
            }
        }
        if options.bracketed_paste {
            output.execute(EnableBracketedPaste)?;
            setup.modes.is_bracketed_paste_enabled = true;
        }
        if options.focus_reporting {
            output.execute(EnableFocusChange)?;
            setup.modes.is_focus_reporting_enabled = true;
        }
        if options.keyboard != KeyboardMode::Basic
            && keyboard.is_some_and(|info| info.enhancement == Status::Supported)
        {
            let (flags, names): (KeyboardEnhancementFlags, Vec<&'static str>) =
                match options.keyboard {
                    KeyboardMode::Disambiguated => (
                        KeyboardEnhancementFlags::DISAMBIGUATE_ESCAPE_CODES,
                        vec!["disambiguate"],
                    ),
                    _ => (
                        KeyboardEnhancementFlags::DISAMBIGUATE_ESCAPE_CODES
                            | KeyboardEnhancementFlags::REPORT_EVENT_TYPES
                            | KeyboardEnhancementFlags::REPORT_ALL_KEYS_AS_ESCAPE_CODES,
                        vec!["disambiguate", "event_types", "all_keys"],
                    ),
                };
            output.execute(PushKeyboardEnhancementFlags(flags))?;
            setup.modes.keyboard_features = names;
        }
        output.flush()?;
        let viewport = match options.inline_height {
            Some(height) => Viewport::Inline(height.max(1)),
            None => Viewport::Fullscreen,
        };
        let terminal =
            Terminal::with_options(CrosstermBackend::new(stdout()), RatatuiOptions { viewport })?;
        let modes = std::mem::take(&mut setup.modes);
        setup.armed = false;
        let input = Some(InputReader::spawn(Arc::clone(&sink)));
        #[cfg(unix)]
        if options.should_handle_exit_signals {
            exit_signals::register(&sink);
        }
        Ok(Self {
            terminal,
            options,
            modes,
            input,
            sink,
            last_graphics: None,
            last_area: Rect::default(),
            _panic_guard: panic_guard,
        })
    }

    pub fn modes(&self) -> &DeviceModes {
        &self.modes
    }

    pub fn is_inline(&self) -> bool {
        self.options.inline_height.is_some()
    }

    /// The size of the area frames are drawn into, following any terminal resize.
    pub fn viewport(&mut self) -> io::Result<Size> {
        self.terminal.autoresize()?;
        let area = self.terminal.get_frame().area();
        self.last_area = area;
        Ok(Size::new(i32::from(area.width), i32::from(area.height)))
    }

    /// The size of the whole terminal window in cells.
    pub fn window_size(&mut self) -> io::Result<Size> {
        let size = self.terminal.size()?;
        Ok(Size::new(i32::from(size.width), i32::from(size.height)))
    }

    /// Show `frame` in one synchronized update.
    pub fn present(&mut self, frame: &Grid, cursor: Option<Point>) -> io::Result<()> {
        let signature = graphics_signature(frame);
        let needs_full_redraw = match (self.last_graphics, signature) {
            (Some(previous), Some(current)) => {
                previous.area == current.area
                    && previous.anchors == current.anchors
                    && previous.cells != current.cells
            }
            _ => false,
        };
        self.last_graphics = signature;
        if needs_full_redraw {
            self.terminal.clear()?;
        }
        self.terminal.backend_mut().queue(BeginSynchronizedUpdate)?;
        let result = self.terminal.draw(|terminal_frame| {
            let target = terminal_frame.buffer_mut();
            let source = frame.buffer();
            if target.area == source.area {
                target.content.clone_from_slice(&source.content);
            } else {
                let shared = target.area.intersection(source.area);
                for y in shared.top()..shared.bottom() {
                    for x in shared.left()..shared.right() {
                        if let (Some(from), Some(to)) =
                            (source.cell((x, y)), target.cell_mut((x, y)))
                        {
                            to.clone_from(from);
                        }
                    }
                }
            }
            if let Some(position) = cursor
                && position.x >= 0
                && position.y >= 0
            {
                terminal_frame.set_cursor_position((position.x as u16, position.y as u16));
            }
        });
        let drawn = result.map(|_| ());
        self.terminal.backend_mut().execute(EndSynchronizedUpdate)?;
        drawn
    }

    pub fn clear(&mut self) -> io::Result<()> {
        self.terminal.clear()
    }

    /// Give the terminal back, optionally swallowing late replies from the terminal.
    pub fn close(mut self) {
        if let Some(mut reader) = self.input.take() {
            reader.stop();
        }
        #[cfg(unix)]
        if self.options.should_handle_exit_signals {
            exit_signals::unregister(&self.sink);
        }
        emit_reset_sequences();
        let mut output = stdout();
        if self.modes.is_alternate_screen_enabled {
            let _ = output.execute(LeaveAlternateScreen);
        }
        if self.is_inline() {
            let _ = output.execute(MoveTo(0, self.last_area.bottom()));
        }
        if self.options.drain_reports_on_exit {
            let deadline = Instant::now() + self.options.drain_timeout;
            while Instant::now() < deadline && wait_for_input(Duration::from_millis(15)) {
                let _ = crossterm::event::read();
            }
        }
        if self.modes.is_raw_mode_enabled {
            let _ = disable_raw_mode();
        }
        emit_reset_sequences();
        let _ = output.flush();
    }
}

#[cfg(test)]
mod panic_scope_tests {
    use super::{IS_PANIC_GUARDED, guard_panics};

    #[test]
    fn nested_panic_guards_restore_their_parent_state() {
        let result = guard_panics(|| {
            assert!(IS_PANIC_GUARDED.with(std::cell::Cell::get));
            let nested = guard_panics(|| assert!(IS_PANIC_GUARDED.with(std::cell::Cell::get)));
            assert!(nested.is_ok());
            assert!(IS_PANIC_GUARDED.with(std::cell::Cell::get));
        });

        assert!(result.is_ok());
        assert!(!IS_PANIC_GUARDED.with(std::cell::Cell::get));
    }

    #[test]
    fn panic_guard_restores_state_when_body_panics() {
        let result = guard_panics(|| panic!("test panic"));

        assert_eq!(result.unwrap_err(), "test panic");
        assert!(!IS_PANIC_GUARDED.with(std::cell::Cell::get));
    }
}
