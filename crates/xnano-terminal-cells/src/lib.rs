//! The renderer-neutral frame formats shared by xnano's native packages.
//!
//! PyO3 extension modules cannot share `#[pyclass]` types, so `xnano-core` and
//! `xnano-image` exchange plain bytes instead:
//!
//! - a **cell grid** (`XCG1`) is one terminal frame: symbols, colors and
//!   modifiers for every cell;
//! - a **cell animation** (`XCA1`) is a sequence of cell grids, each with its
//!   display time.
//!
//! Both packages depend on this crate, so the formats can never drift apart.
//!
//! Cell grid layout, all little-endian:
//!
//! ```text
//! "XCG1" | u16 width | u16 height | cell * (width * height), row-major
//! cell   = u8 diff | [u16 width if diff = 3] | varint symbol length
//!          | symbol (UTF-8) | color foreground | color background
//!          | color underline | u16 modifier bits
//! diff   = 0 none | 1 skip | 2 always update | 3 forced width
//! color  = u8 tag, u8 a, u8 b, u8 c
//!          tag 0 reset | 1..=16 named | 17 indexed (a) | 18 rgb (a, b, c)
//! ```
//!
//! Cell animation layout, all little-endian:
//!
//! ```text
//! "XCA1" | u8 flags (bit 0: loops) | u32 frame count
//!        | frame * count
//! frame  = u32 duration in milliseconds | u32 grid length | cell grid
//! ```

use std::fmt::Write as _;
use std::num::NonZeroU16;

use ratatui_core::buffer::{Buffer, Cell, CellDiffOption, CellWidth};
use ratatui_core::layout::Rect;
use ratatui_core::style::{Color, Modifier};

/// Magic bytes that start a cell grid.
pub const GRID_MAGIC: &[u8; 4] = b"XCG1";
/// Magic bytes that start a cell animation.
pub const ANIMATION_MAGIC: &[u8; 4] = b"XCA1";
/// Most cells one grid may hold, to bound allocation from untrusted bytes.
pub const MAX_CELLS: usize = 4_000_000;
/// Most cells one animation may hold across all of its frames.
pub const MAX_ANIMATION_CELLS: usize = 64_000_000;
/// Most frames one animation may hold.
pub const MAX_FRAMES: usize = 100_000;
/// Longest symbol one cell may hold. Graphics protocol payloads (sixel,
/// kitty, iTerm2) are stored in a single anchor cell and can be large.
pub const MAX_SYMBOL_BYTES: usize = 64 * 1024 * 1024;

const NAMED: [Color; 16] = [
    Color::Black,
    Color::Red,
    Color::Green,
    Color::Yellow,
    Color::Blue,
    Color::Magenta,
    Color::Cyan,
    Color::Gray,
    Color::DarkGray,
    Color::LightRed,
    Color::LightGreen,
    Color::LightYellow,
    Color::LightBlue,
    Color::LightMagenta,
    Color::LightCyan,
    Color::White,
];

/// Why bytes could not be read as a cell grid or cell animation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FormatError(String);

impl FormatError {
    fn new(message: impl Into<String>) -> Self {
        Self(message.into())
    }
}

impl std::fmt::Display for FormatError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl std::error::Error for FormatError {}

fn encode_color(color: Color) -> [u8; 4] {
    match color {
        Color::Rgb(red, green, blue) => [18, red, green, blue],
        Color::Indexed(index) => [17, index, 0, 0],
        Color::Reset => [0, 0, 0, 0],
        Color::Black => [1, 0, 0, 0],
        Color::Red => [2, 0, 0, 0],
        Color::Green => [3, 0, 0, 0],
        Color::Yellow => [4, 0, 0, 0],
        Color::Blue => [5, 0, 0, 0],
        Color::Magenta => [6, 0, 0, 0],
        Color::Cyan => [7, 0, 0, 0],
        Color::Gray => [8, 0, 0, 0],
        Color::DarkGray => [9, 0, 0, 0],
        Color::LightRed => [10, 0, 0, 0],
        Color::LightGreen => [11, 0, 0, 0],
        Color::LightYellow => [12, 0, 0, 0],
        Color::LightBlue => [13, 0, 0, 0],
        Color::LightMagenta => [14, 0, 0, 0],
        Color::LightCyan => [15, 0, 0, 0],
        Color::White => [16, 0, 0, 0],
    }
}

fn decode_color(bytes: [u8; 4]) -> Result<Color, FormatError> {
    match bytes[0] {
        0 => Ok(Color::Reset),
        tag @ 1..=16 => Ok(NAMED[usize::from(tag) - 1]),
        17 => Ok(Color::Indexed(bytes[1])),
        18 => Ok(Color::Rgb(bytes[1], bytes[2], bytes[3])),
        tag => Err(FormatError::new(format!(
            "the cell grid is corrupt: unknown color tag {tag}"
        ))),
    }
}

fn write_varint(output: &mut Vec<u8>, mut value: usize) {
    while value >= 0x80 {
        output.push((value & 0x7f) as u8 | 0x80);
        value >>= 7;
    }
    output.push(value as u8);
}

/// Check that a `width` x `height` grid is within [`MAX_CELLS`].
pub fn check_grid_size(width: u16, height: u16) -> Result<(), FormatError> {
    let count = usize::from(width) * usize::from(height);
    if count > MAX_CELLS {
        return Err(FormatError::new(format!(
            "a cell grid of {width}x{height} cells ({count} cells) is larger than the \
             limit of {MAX_CELLS} cells; use fewer columns or rows"
        )));
    }
    Ok(())
}

fn pack_into(buffer: &Buffer, output: &mut Vec<u8>) {
    let area = buffer.area;
    output.extend_from_slice(GRID_MAGIC);
    output.extend_from_slice(&area.width.to_le_bytes());
    output.extend_from_slice(&area.height.to_le_bytes());
    for cell in &buffer.content {
        match cell.diff_option {
            CellDiffOption::None => output.push(0),
            CellDiffOption::Skip => output.push(1),
            CellDiffOption::AlwaysUpdate => output.push(2),
            CellDiffOption::ForcedWidth(width) => {
                output.push(3);
                output.extend_from_slice(&width.get().to_le_bytes());
            }
        }
        let symbol = cell.symbol().as_bytes();
        if let [byte] = symbol {
            // The common one-byte symbol: its length and byte in one write.
            output.extend_from_slice(&[1, *byte]);
        } else {
            write_varint(output, symbol.len());
            output.extend_from_slice(symbol);
        }
        output.extend_from_slice(&encode_color(cell.fg));
        output.extend_from_slice(&encode_color(cell.bg));
        output.extend_from_slice(&encode_color(cell.underline_color));
        output.extend_from_slice(&cell.modifier.bits().to_le_bytes());
    }
}

/// Serialize `buffer` into a cell grid.
///
/// Fails when the buffer holds more than [`MAX_CELLS`] cells, so a grid that
/// could never be read back is never written.
pub fn pack(buffer: &Buffer) -> Result<Vec<u8>, FormatError> {
    check_grid_size(buffer.area.width, buffer.area.height)?;
    let mut output = Vec::with_capacity(8 + buffer.content.len() * 18);
    pack_into(buffer, &mut output);
    Ok(output)
}

struct Reader<'a> {
    data: &'a [u8],
    position: usize,
}

impl<'a> Reader<'a> {
    fn take(&mut self, count: usize) -> Result<&'a [u8], FormatError> {
        let end = self
            .position
            .checked_add(count)
            .filter(|&end| end <= self.data.len())
            .ok_or_else(|| FormatError::new("the data ends before the cell grid is complete"))?;
        let bytes = &self.data[self.position..end];
        self.position = end;
        Ok(bytes)
    }

    fn array<const N: usize>(&mut self) -> Result<[u8; N], FormatError> {
        let mut output = [0; N];
        output.copy_from_slice(self.take(N)?);
        Ok(output)
    }

    fn varint(&mut self) -> Result<usize, FormatError> {
        let (mut value, mut shift) = (0_usize, 0_u32);
        loop {
            let byte = self.take(1)?[0];
            value |= usize::from(byte & 0x7f) << shift;
            if byte & 0x80 == 0 {
                return Ok(value);
            }
            shift += 7;
            if shift > 28 {
                return Err(FormatError::new(
                    "the cell grid is corrupt: a symbol length is too large",
                ));
            }
        }
    }
}

/// Read only the `(width, height)` of a cell grid.
pub fn grid_size(data: &[u8]) -> Result<(u16, u16), FormatError> {
    let mut reader = Reader { data, position: 0 };
    if data.len() < 4 || reader.take(4)? != GRID_MAGIC {
        return Err(FormatError::new(
            "the bytes are not a cell grid; pass the bytes returned by a cell grid \
             conversion such as TerminalImage.to_cell_grid",
        ));
    }
    let width = u16::from_le_bytes(reader.array()?);
    let height = u16::from_le_bytes(reader.array()?);
    Ok((width, height))
}

fn unpack_from(reader: &mut Reader<'_>) -> Result<Buffer, FormatError> {
    if reader.take(4)? != GRID_MAGIC {
        return Err(FormatError::new(
            "the bytes are not a cell grid; pass the bytes returned by a cell grid \
             conversion such as TerminalImage.to_cell_grid",
        ));
    }
    let width = u16::from_le_bytes(reader.array()?);
    let height = u16::from_le_bytes(reader.array()?);
    check_grid_size(width, height)?;
    let count = usize::from(width) * usize::from(height);
    let mut content = Vec::with_capacity(count);
    for _ in 0..count {
        let diff = match reader.take(1)?[0] {
            0 => CellDiffOption::None,
            1 => CellDiffOption::Skip,
            2 => CellDiffOption::AlwaysUpdate,
            3 => CellDiffOption::ForcedWidth(
                NonZeroU16::new(u16::from_le_bytes(reader.array()?)).ok_or_else(|| {
                    FormatError::new("the cell grid is corrupt: a cell has a zero width")
                })?,
            ),
            other => {
                return Err(FormatError::new(format!(
                    "the cell grid is corrupt: unknown cell kind {other}"
                )));
            }
        };
        let length = reader.varint()?;
        if length > MAX_SYMBOL_BYTES {
            return Err(FormatError::new(format!(
                "the cell grid is corrupt: a cell symbol of {length} bytes is larger than \
                 the limit of {MAX_SYMBOL_BYTES} bytes"
            )));
        }
        let symbol_bytes = reader.take(length)?;
        let mut decoded = Cell::default();
        match symbol_bytes {
            // One ASCII byte is always valid UTF-8, so it skips the validation.
            [byte] if byte.is_ascii() => {
                decoded.set_symbol(char::from(*byte).encode_utf8(&mut [0; 4]));
            }
            _ => {
                let symbol = std::str::from_utf8(symbol_bytes).map_err(|_| {
                    FormatError::new("the cell grid is corrupt: a cell symbol is not valid UTF-8")
                })?;
                decoded.set_symbol(symbol);
            }
        }
        let tail = reader.take(14)?;
        decoded.fg = decode_color([tail[0], tail[1], tail[2], tail[3]])?;
        decoded.bg = decode_color([tail[4], tail[5], tail[6], tail[7]])?;
        decoded.underline_color = decode_color([tail[8], tail[9], tail[10], tail[11]])?;
        decoded.modifier = Modifier::from_bits_truncate(u16::from_le_bytes([tail[12], tail[13]]));
        decoded.diff_option = diff;
        content.push(decoded);
    }
    Ok(Buffer {
        area: Rect::new(0, 0, width, height),
        content,
    })
}

/// Deserialize a cell grid. Malformed input is an error, never a panic.
pub fn unpack(data: &[u8]) -> Result<Buffer, FormatError> {
    let mut reader = Reader { data, position: 0 };
    let buffer = unpack_from(&mut reader)?;
    if reader.position != data.len() {
        return Err(FormatError::new(
            "the cell grid is corrupt: there are extra bytes after the last cell",
        ));
    }
    Ok(buffer)
}

/// One frame of a cell animation.
#[derive(Debug, Clone, PartialEq)]
pub struct AnimationFrame {
    /// The frame's cells.
    pub grid: Buffer,
    /// How long the frame is shown, in milliseconds.
    pub duration_milliseconds: u32,
}

/// A decoded cell animation.
#[derive(Debug, Clone, PartialEq)]
pub struct CellAnimation {
    /// The frames, in playback order.
    pub frames: Vec<AnimationFrame>,
    /// Whether playback starts over after the last frame.
    pub should_loop: bool,
}

impl CellAnimation {
    /// Total playback time of one pass, in milliseconds.
    pub fn duration_milliseconds(&self) -> u64 {
        self.frames
            .iter()
            .map(|frame| u64::from(frame.duration_milliseconds))
            .sum()
    }

    /// Index of the frame showing `elapsed_milliseconds` into playback.
    ///
    /// Negative times show the first frame. Without looping, playback holds
    /// the last frame.
    pub fn frame_index_at(&self, elapsed_milliseconds: i64) -> usize {
        if self.frames.is_empty() || elapsed_milliseconds <= 0 {
            return 0;
        }
        let total = self.duration_milliseconds();
        if total == 0 {
            return 0;
        }
        let elapsed = elapsed_milliseconds as u64;
        let position = if self.should_loop {
            elapsed % total
        } else if elapsed >= total {
            return self.frames.len() - 1;
        } else {
            elapsed
        };
        let mut start = 0_u64;
        for (index, frame) in self.frames.iter().enumerate() {
            start += u64::from(frame.duration_milliseconds);
            if position < start {
                return index;
            }
        }
        self.frames.len() - 1
    }

    /// Milliseconds from `elapsed_milliseconds` until the next frame change, or
    /// `None` when the frame never changes again.
    pub fn milliseconds_until_next_frame(&self, elapsed_milliseconds: i64) -> Option<u64> {
        if self.frames.len() < 2 {
            return None;
        }
        let total = self.duration_milliseconds();
        if total == 0 {
            return None;
        }
        let elapsed = elapsed_milliseconds.max(0) as u64;
        if !self.should_loop && elapsed >= total {
            return None;
        }
        let position = elapsed % total;
        let mut start = 0_u64;
        for frame in &self.frames {
            start += u64::from(frame.duration_milliseconds);
            if position < start {
                return Some((start - position).max(1));
            }
        }
        Some(1)
    }
}

/// Serialize frames into a cell animation.
pub fn pack_animation(animation: &CellAnimation) -> Result<Vec<u8>, FormatError> {
    if animation.frames.is_empty() {
        return Err(FormatError::new(
            "a cell animation needs at least one frame",
        ));
    }
    if animation.frames.len() > MAX_FRAMES {
        return Err(FormatError::new(format!(
            "a cell animation of {} frames is longer than the limit of {MAX_FRAMES} frames",
            animation.frames.len()
        )));
    }
    let mut total_cells = 0_usize;
    for frame in &animation.frames {
        check_grid_size(frame.grid.area.width, frame.grid.area.height)?;
        total_cells += frame.grid.content.len();
    }
    if total_cells > MAX_ANIMATION_CELLS {
        return Err(FormatError::new(format!(
            "a cell animation of {total_cells} cells in total is larger than the limit of \
             {MAX_ANIMATION_CELLS} cells; use fewer frames, columns or rows"
        )));
    }
    let mut output = Vec::new();
    output.extend_from_slice(ANIMATION_MAGIC);
    output.push(u8::from(animation.should_loop));
    output.extend_from_slice(&(animation.frames.len() as u32).to_le_bytes());
    let mut grid = Vec::new();
    for frame in &animation.frames {
        grid.clear();
        pack_into(&frame.grid, &mut grid);
        output.extend_from_slice(&frame.duration_milliseconds.to_le_bytes());
        output.extend_from_slice(&(grid.len() as u32).to_le_bytes());
        output.extend_from_slice(&grid);
    }
    Ok(output)
}

/// Deserialize a cell animation. Malformed input is an error, never a panic.
pub fn unpack_animation(data: &[u8]) -> Result<CellAnimation, FormatError> {
    let mut reader = Reader { data, position: 0 };
    if data.len() < 4 || reader.take(4)? != ANIMATION_MAGIC {
        return Err(FormatError::new(
            "the bytes are not a cell animation; pass the bytes returned by \
             TerminalImage.to_cell_animation",
        ));
    }
    let flags = reader.take(1)?[0];
    let count = u32::from_le_bytes(reader.array()?) as usize;
    if count == 0 || count > MAX_FRAMES {
        return Err(FormatError::new(format!(
            "the cell animation is corrupt: it declares {count} frames; an animation has \
             between 1 and {MAX_FRAMES} frames"
        )));
    }
    let mut frames = Vec::with_capacity(count.min(1024));
    let mut total_cells = 0_usize;
    for _ in 0..count {
        let duration_milliseconds = u32::from_le_bytes(reader.array()?);
        let length = u32::from_le_bytes(reader.array()?) as usize;
        let grid_bytes = reader.take(length)?;
        let (width, height) = grid_size(grid_bytes)?;
        total_cells += usize::from(width) * usize::from(height);
        if total_cells > MAX_ANIMATION_CELLS {
            return Err(FormatError::new(format!(
                "the cell animation holds more than the limit of {MAX_ANIMATION_CELLS} cells"
            )));
        }
        frames.push(AnimationFrame {
            grid: unpack(grid_bytes)?,
            duration_milliseconds,
        });
    }
    if reader.position != data.len() {
        return Err(FormatError::new(
            "the cell animation is corrupt: there are extra bytes after the last frame",
        ));
    }
    Ok(CellAnimation {
        frames,
        should_loop: flags & 1 == 1,
    })
}

/// Whether a cell carries a terminal graphics protocol payload (sixel, kitty
/// or iTerm2) or is covered by one.
///
/// Protocol images are drawn by an escape sequence stored in one anchor cell;
/// the other cells of the image are skipped. Such cells must not be restyled,
/// split or partially redrawn, or the image breaks.
pub fn is_graphics_protocol_cell(cell: &Cell) -> bool {
    cell.diff_option == CellDiffOption::Skip || cell.symbol().starts_with('\x1b')
}

/// Whether any cell of `buffer` carries a terminal graphics protocol payload.
pub fn has_graphics_protocol_cells(buffer: &Buffer) -> bool {
    buffer.content.iter().any(is_graphics_protocol_cell)
}

fn push_color(output: &mut String, color: Color, is_foreground: bool) {
    let base = if is_foreground { 30 } else { 40 };
    let code = match color {
        Color::Reset => return,
        Color::Rgb(red, green, blue) => {
            let _ = write!(output, ";{};2;{red};{green};{blue}", base + 8);
            return;
        }
        Color::Indexed(index) => {
            let _ = write!(output, ";{};5;{index}", base + 8);
            return;
        }
        named => NAMED
            .iter()
            .position(|&candidate| candidate == named)
            .unwrap_or(0) as u8,
    };
    let is_bright = code >= 8;
    let _ = write!(
        output,
        ";{}",
        base + u16::from(code % 8) + if is_bright { 60 } else { 0 }
    );
}

/// How many cells after `cell` a glyph covers (zero for a graphics anchor or a narrow glyph).
fn covered_after_head(cell: &Cell) -> usize {
    let symbol = cell.symbol();
    // A one-byte symbol is one column, so most cells never reach the width tables.
    if symbol.len() == 1 && cell.diff_option == CellDiffOption::None {
        return 0;
    }
    if symbol.starts_with('\x1b') {
        0
    } else {
        usize::from(cell.cell_width()).saturating_sub(1)
    }
}

/// Render `buffer` as ANSI text, for printing to a terminal.
///
/// Rows are separated by newlines, like [`text`], with no newline after the last row,
/// and every row ends by resetting the style.
pub fn ansi(buffer: &Buffer) -> String {
    let width = usize::from(buffer.area.width).max(1);
    // Every cell prints one symbol; style changes add a few bytes more.
    let mut output = String::with_capacity(buffer.content.len() + buffer.content.len() / 4 + 64);
    for (index, row) in buffer.content.chunks(width).enumerate() {
        if index > 0 {
            output.push('\n');
        }
        let mut last: Option<(Color, Color, Modifier)> = None;
        // A wide glyph fills its own cell; the cells it covers are not printed.
        let mut covered = 0_usize;
        for cell in row {
            if covered > 0 {
                covered -= 1;
                continue;
            }
            // A graphics protocol anchor covers no cells: the image's other
            // cells are skip cells of their own.
            covered = covered_after_head(cell);
            if cell.diff_option == CellDiffOption::Skip {
                continue;
            }
            let style = (cell.fg, cell.bg, cell.modifier);
            if last != Some(style) {
                output.push_str("\x1b[0");
                for (flag, code) in [
                    (Modifier::BOLD, 1),
                    (Modifier::DIM, 2),
                    (Modifier::ITALIC, 3),
                    (Modifier::UNDERLINED, 4),
                    (Modifier::REVERSED, 7),
                    (Modifier::CROSSED_OUT, 9),
                ] {
                    if cell.modifier.contains(flag) {
                        let _ = write!(output, ";{code}");
                    }
                }
                push_color(&mut output, cell.fg, true);
                push_color(&mut output, cell.bg, false);
                output.push('m');
                last = Some(style);
            }
            output.push_str(cell.symbol());
        }
        output.push_str("\x1b[0m");
    }
    output
}

/// Plain symbols only, one line per row (trailing spaces trimmed).
///
/// Graphics protocol payloads are shown as spaces, so the text never contains
/// escape sequences.
pub fn text(buffer: &Buffer) -> Vec<String> {
    let width = usize::from(buffer.area.width).max(1);
    buffer
        .content
        .chunks(width)
        .map(|row| {
            let mut covered = 0_usize;
            let mut line = String::with_capacity(width);
            for cell in row {
                if covered > 0 {
                    covered -= 1;
                    continue;
                }
                let is_protocol_anchor = cell.symbol().starts_with('\x1b');
                covered = covered_after_head(cell);
                if cell.diff_option == CellDiffOption::Skip || is_protocol_anchor {
                    line.push(' ');
                } else {
                    line.push_str(cell.symbol());
                }
            }
            line.trim_end().to_string()
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui_core::style::Style;

    fn sample(width: u16, height: u16) -> Buffer {
        let mut buffer = Buffer::empty(Rect::new(0, 0, width, height));
        buffer.set_string(
            0,
            0,
            "hé中",
            Style::default().fg(Color::Red).bg(Color::Rgb(1, 2, 3)),
        );
        buffer
    }

    #[test]
    fn grids_round_trip() {
        let buffer = sample(6, 2);
        let packed = pack(&buffer).unwrap();
        assert_eq!(grid_size(&packed).unwrap(), (6, 2));
        assert_eq!(unpack(&packed).unwrap(), buffer);
    }

    #[test]
    fn malformed_grids_are_errors() {
        let packed = pack(&sample(4, 2)).unwrap();
        for bad in [
            &packed[..packed.len() - 1],
            b"XCG1".as_slice(),
            b"",
            b"nope",
        ] {
            assert!(unpack(bad).is_err());
        }
        let mut trailing = packed.clone();
        trailing.push(0);
        assert!(unpack(&trailing).is_err());
    }

    #[test]
    fn oversized_grids_are_refused_on_both_sides() {
        let error = check_grid_size(4000, 1001).unwrap_err();
        assert!(error.to_string().contains("limit"));
        let mut header = GRID_MAGIC.to_vec();
        header.extend_from_slice(&4000_u16.to_le_bytes());
        header.extend_from_slice(&1001_u16.to_le_bytes());
        assert!(unpack(&header).is_err());
    }

    #[test]
    fn animations_round_trip_and_pick_frames_by_time() {
        let animation = CellAnimation {
            frames: vec![
                AnimationFrame {
                    grid: sample(3, 1),
                    duration_milliseconds: 100,
                },
                AnimationFrame {
                    grid: Buffer::empty(Rect::new(0, 0, 3, 1)),
                    duration_milliseconds: 50,
                },
            ],
            should_loop: true,
        };
        let packed = pack_animation(&animation).unwrap();
        let decoded = unpack_animation(&packed).unwrap();
        assert_eq!(decoded, animation);
        assert_eq!(decoded.frame_index_at(-5), 0);
        assert_eq!(decoded.frame_index_at(99), 0);
        assert_eq!(decoded.frame_index_at(100), 1);
        assert_eq!(decoded.frame_index_at(150), 0);
        assert_eq!(decoded.milliseconds_until_next_frame(40), Some(60));
        let once = CellAnimation {
            should_loop: false,
            ..animation
        };
        assert_eq!(once.frame_index_at(10_000), 1);
        assert_eq!(once.milliseconds_until_next_frame(10_000), None);
    }

    #[test]
    fn malformed_animations_are_errors() {
        assert!(unpack_animation(b"XCA1").is_err());
        assert!(unpack_animation(b"XCA1\x00\x00\x00\x00\x00").is_err());
        assert!(
            pack_animation(&CellAnimation {
                frames: vec![],
                should_loop: true
            })
            .is_err()
        );
    }

    #[test]
    fn text_never_contains_escape_sequences() {
        let mut buffer = Buffer::empty(Rect::new(0, 0, 3, 1));
        buffer[(0, 0)].set_symbol("\x1b_Gpayload\x1b\\");
        buffer[(1, 0)].diff_option = CellDiffOption::Skip;
        buffer[(2, 0)].set_symbol("x");
        assert!(has_graphics_protocol_cells(&buffer));
        assert_eq!(text(&buffer), vec!["  x".to_string()]);
    }

    #[test]
    fn ansi_rows_match_the_text_rows() {
        let mut buffer = Buffer::empty(Rect::new(0, 0, 2, 3));
        buffer.set_string(0, 0, "ab", Style::default().fg(Color::Red));
        buffer.set_string(0, 2, "cd", Style::default());
        let output = ansi(&buffer);
        assert!(!output.ends_with('\n'));
        assert!(output.ends_with("\x1b[0m"));
        assert_eq!(output.split('\n').count(), text(&buffer).len());
        assert_eq!(
            output,
            "\x1b[0;31mab\x1b[0m\n\x1b[0m  \x1b[0m\n\x1b[0mcd\x1b[0m"
        );
    }
}

/// The version of the cell grid and cell animation formats.
pub const FORMAT_VERSION: u32 = 1;

/// Upper bounds applied while reading untrusted bytes, before allocating for them.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Limits {
    /// Most cells one grid, or all frames of one animation, may hold.
    pub maximum_cells: usize,
    /// Most frames one animation may hold.
    pub maximum_frames: usize,
    /// Most bytes the packed data may take.
    pub maximum_payload_bytes: usize,
}

impl Default for Limits {
    fn default() -> Self {
        Self {
            maximum_cells: 16_000_000,
            maximum_frames: 10_000,
            maximum_payload_bytes: 268_435_456,
        }
    }
}

fn check_payload(data: &[u8], limits: &Limits) -> Result<(), FormatError> {
    if data.len() > limits.maximum_payload_bytes {
        return Err(FormatError::new(format!(
            "the data is {} bytes, which is over the limit of {} bytes; raise \
             maximum_payload_bytes or use a smaller image",
            data.len(),
            limits.maximum_payload_bytes
        )));
    }
    Ok(())
}

/// The terminal graphics protocol a buffer's cells need, if any.
pub fn required_protocol(buffer: &Buffer) -> Option<&'static str> {
    buffer.content.iter().find_map(|cell| {
        let symbol = cell.symbol();
        if symbol.starts_with("\x1b_G") {
            Some("kitty")
        } else if symbol.starts_with("\x1bP") {
            Some("sixel")
        } else if symbol.starts_with("\x1b]1337") {
            Some("iterm2")
        } else {
            None
        }
    })
}

/// What a cell grid holds.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GridInfo {
    pub columns: u16,
    pub rows: u16,
    pub has_graphics_protocol_cells: bool,
    pub required_protocol: Option<&'static str>,
}

/// Read a cell grid, refusing anything over `limits`.
pub fn unpack_limited(data: &[u8], limits: &Limits) -> Result<Buffer, FormatError> {
    check_payload(data, limits)?;
    let (width, height) = grid_size(data)?;
    let cells = usize::from(width) * usize::from(height);
    if cells > limits.maximum_cells {
        return Err(FormatError::new(format!(
            "the cell grid has {cells} cells, which is over the limit of {} cells",
            limits.maximum_cells
        )));
    }
    unpack(data)
}

/// Describe a cell grid after fully validating it.
pub fn inspect(data: &[u8], limits: &Limits) -> Result<GridInfo, FormatError> {
    let grid = unpack_limited(data, limits)?;
    Ok(GridInfo {
        columns: grid.area.width,
        rows: grid.area.height,
        has_graphics_protocol_cells: has_graphics_protocol_cells(&grid),
        required_protocol: required_protocol(&grid),
    })
}

/// What a cell animation holds.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct AnimationInfo {
    pub columns: u16,
    pub rows: u16,
    pub frame_count: usize,
    pub duration_milliseconds: u64,
    pub should_loop: bool,
}

/// Read a cell animation, refusing anything over `limits`.
pub fn unpack_animation_limited(
    data: &[u8],
    limits: &Limits,
) -> Result<CellAnimation, FormatError> {
    check_payload(data, limits)?;
    if data.len() >= 9 && &data[..4] == ANIMATION_MAGIC {
        let count = u32::from_le_bytes([data[5], data[6], data[7], data[8]]) as usize;
        if count > limits.maximum_frames {
            return Err(FormatError::new(format!(
                "the cell animation has {count} frames, which is over the limit of {} frames",
                limits.maximum_frames
            )));
        }
    }
    let animation = unpack_animation(data)?;
    let cells: usize = animation
        .frames
        .iter()
        .map(|frame| frame.grid.content.len())
        .sum();
    if cells > limits.maximum_cells {
        return Err(FormatError::new(format!(
            "the cell animation has {cells} cells in total, which is over the limit of {} cells",
            limits.maximum_cells
        )));
    }
    Ok(animation)
}

/// Describe a cell animation after fully validating it.
pub fn inspect_animation(data: &[u8], limits: &Limits) -> Result<AnimationInfo, FormatError> {
    let animation = unpack_animation_limited(data, limits)?;
    let first = animation.frames.first().map(|frame| frame.grid.area);
    Ok(AnimationInfo {
        columns: first.map_or(0, |area| area.width),
        rows: first.map_or(0, |area| area.height),
        frame_count: animation.frames.len(),
        duration_milliseconds: animation.duration_milliseconds(),
        should_loop: animation.should_loop,
    })
}
