use ratatui::layout::Position;
use ratatui::Frame;

/// Clear the frame's deferred cursor so ratatui hides it after the draw pass.
///
/// Ratatui does not expose a public `Frame::hide_cursor`; when `cursor_position`
/// is `None` the terminal hides the cursor once the frame diff is flushed.
pub(crate) fn frame_hide_cursor(frame: &mut Frame<'_>) {
    // SAFETY: In ratatui 0.29, `cursor_position` is the first field of `Frame`.
    // We only write `None`, matching ratatui's own post-draw behavior.
    unsafe {
        let cursor_ptr = frame as *mut Frame<'_> as *mut Option<Position>;
        *cursor_ptr = None;
    }
}
