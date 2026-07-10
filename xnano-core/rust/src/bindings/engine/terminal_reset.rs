//! Best-effort host terminal reset used on every session exit path.
//!
//! A live xnano session can leave private modes (mouse, paste, synchronized
//! output, keyboard protocol) and SGR attributes armed. If those are not fully
//! cleared, a later ratatui app in the same terminal may paint with sticky
//! colors or fail to redraw cells until the emulator is forced to repaint
//! (for example by selecting text).

use std::io::{stdout, Write};

use crossterm::cursor::{SetCursorStyle, Show};
use crossterm::style::{Attribute, ResetColor, SetAttribute};
use crossterm::terminal::EnableLineWrap;
use crossterm::ExecutableCommand;

use super::super::event_setup::{
    disable_bracketed_paste_impl, disable_focus_change_impl, disable_mouse_capture_impl,
    pop_keyboard_enhancement_flags_impl,
};
use super::super::terminal_device::end_synchronized_update_impl;

/// Comprehensive private-mode / SGR reset sequence.
///
/// Written in addition to typed crossterm commands so emulators that only
/// partially honor one form still recover. Sequences that were never enabled
/// are ignored by compliant hosts.
const TERMINAL_RESET_BLOB: &[u8] = b"\
\x1b[0m\
\x1b[39m\
\x1b[49m\
\x1b[59m\
\x1b[?25h\
\x1b[0 q\
\x1b[?7h\
\x1b[?1000l\
\x1b[?1002l\
\x1b[?1003l\
\x1b[?1005l\
\x1b[?1006l\
\x1b[?1015l\
\x1b[?1004l\
\x1b[?2004l\
\x1b[?2026l\
";

/// Emit every known teardown sequence. Best-effort: errors are ignored.
pub(crate) fn emit_terminal_reset_sequences() {
    // End synchronized output first so later writes are actually shown.
    let _ = end_synchronized_update_impl();
    // Second end covers hosts that nest or ignore a single disable.
    let _ = end_synchronized_update_impl();

    let _ = disable_mouse_capture_impl();
    let _ = disable_bracketed_paste_impl();
    let _ = disable_focus_change_impl();
    // Safe even when enhancement flags were never pushed.
    let _ = pop_keyboard_enhancement_flags_impl();

    let mut out = stdout();
    let _ = out.execute(Show);
    let _ = out.execute(SetCursorStyle::DefaultUserShape);
    let _ = out.execute(EnableLineWrap);
    let _ = out.execute(ResetColor);
    let _ = out.execute(SetAttribute(Attribute::Reset));
    let _ = out.write_all(TERMINAL_RESET_BLOB);
    let _ = out.flush();
}
