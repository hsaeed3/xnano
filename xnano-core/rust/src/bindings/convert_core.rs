use ratatui::buffer::Buffer as RtBuffer;
use ratatui::layout::{Margin as RtMargin, Rect as RtRect};
use ratatui_core::layout::Margin as CoreMargin;
use ratatui::style::{Color as RtColor, Modifier as RtModifier, Style as RtStyle};
use ratatui_core::buffer::{Buffer as CoreBuffer, CellDiffOption};
use ratatui_core::layout::Rect as CoreRect;
use ratatui_core::style::{Color as CoreColor, Modifier as CoreModifier, Style as CoreStyle};

pub fn to_core_color(color: RtColor) -> CoreColor {
    match color {
        RtColor::Reset => CoreColor::Reset,
        RtColor::Black => CoreColor::Black,
        RtColor::Red => CoreColor::Red,
        RtColor::Green => CoreColor::Green,
        RtColor::Yellow => CoreColor::Yellow,
        RtColor::Blue => CoreColor::Blue,
        RtColor::Magenta => CoreColor::Magenta,
        RtColor::Cyan => CoreColor::Cyan,
        RtColor::Gray => CoreColor::Gray,
        RtColor::DarkGray => CoreColor::DarkGray,
        RtColor::LightRed => CoreColor::LightRed,
        RtColor::LightGreen => CoreColor::LightGreen,
        RtColor::LightYellow => CoreColor::LightYellow,
        RtColor::LightBlue => CoreColor::LightBlue,
        RtColor::LightMagenta => CoreColor::LightMagenta,
        RtColor::LightCyan => CoreColor::LightCyan,
        RtColor::White => CoreColor::White,
        RtColor::Indexed(i) => CoreColor::Indexed(i),
        RtColor::Rgb(r, g, b) => CoreColor::Rgb(r, g, b),
    }
}

pub fn from_core_color(color: CoreColor) -> RtColor {
    match color {
        CoreColor::Reset => RtColor::Reset,
        CoreColor::Black => RtColor::Black,
        CoreColor::Red => RtColor::Red,
        CoreColor::Green => RtColor::Green,
        CoreColor::Yellow => RtColor::Yellow,
        CoreColor::Blue => RtColor::Blue,
        CoreColor::Magenta => RtColor::Magenta,
        CoreColor::Cyan => RtColor::Cyan,
        CoreColor::Gray => RtColor::Gray,
        CoreColor::DarkGray => RtColor::DarkGray,
        CoreColor::LightRed => RtColor::LightRed,
        CoreColor::LightGreen => RtColor::LightGreen,
        CoreColor::LightYellow => RtColor::LightYellow,
        CoreColor::LightBlue => RtColor::LightBlue,
        CoreColor::LightMagenta => RtColor::LightMagenta,
        CoreColor::LightCyan => RtColor::LightCyan,
        CoreColor::White => RtColor::White,
        CoreColor::Indexed(i) => RtColor::Indexed(i),
        CoreColor::Rgb(r, g, b) => RtColor::Rgb(r, g, b),
    }
}

fn to_core_modifier(modifier: RtModifier) -> CoreModifier {
    CoreModifier::from_bits_truncate(modifier.bits())
}

fn from_core_modifier(modifier: CoreModifier) -> RtModifier {
    RtModifier::from_bits_truncate(modifier.bits())
}

pub fn to_core_style(style: RtStyle) -> CoreStyle {
    CoreStyle {
        fg: style.fg.map(to_core_color),
        bg: style.bg.map(to_core_color),
        add_modifier: to_core_modifier(style.add_modifier),
        sub_modifier: to_core_modifier(style.sub_modifier),
    }
}

pub fn from_core_style(style: CoreStyle) -> RtStyle {
    let mut rt = RtStyle::default();
    if let Some(c) = style.fg {
        rt.fg = Some(from_core_color(c));
    }
    if let Some(c) = style.bg {
        rt.bg = Some(from_core_color(c));
    }
    rt.add_modifier = from_core_modifier(style.add_modifier);
    rt.sub_modifier = from_core_modifier(style.sub_modifier);
    rt
}

pub fn to_core_rect(rect: RtRect) -> CoreRect {
    CoreRect::new(rect.x, rect.y, rect.width, rect.height)
}

pub fn to_core_margin(margin: RtMargin) -> CoreMargin {
    CoreMargin {
        horizontal: margin.horizontal,
        vertical: margin.vertical,
    }
}

fn sync_cell_to_core(src: &ratatui::buffer::Cell, dst: &mut ratatui_core::buffer::Cell) {
    dst.set_symbol(src.symbol());
    dst.set_style(to_core_style(src.style()));
    if src.skip {
        dst.set_diff_option(CellDiffOption::Skip);
    } else {
        dst.set_diff_option(CellDiffOption::None);
    }
}

fn sync_cell_from_core(src: &ratatui_core::buffer::Cell, dst: &mut ratatui::buffer::Cell) {
    dst.set_symbol(src.symbol());
    dst.set_style(from_core_style(src.style()));
    dst.set_skip(matches!(src.diff_option, CellDiffOption::Skip));
}

pub fn sync_to_core_buffer(src: &RtBuffer) -> CoreBuffer {
    let mut dst = CoreBuffer::empty(to_core_rect(src.area));
    for y in 0..src.area.height {
        for x in 0..src.area.width {
            sync_cell_to_core(&src[(x, y)], &mut dst[(x, y)]);
        }
    }
    dst
}

pub fn sync_from_core_buffer(src: &CoreBuffer, dst: &mut RtBuffer) {
    let area = to_core_rect(dst.area);
    for y in 0..area.height.min(src.area.height) {
        for x in 0..area.width.min(src.area.width) {
            sync_cell_from_core(&src[(x, y)], &mut dst[(x, y)]);
        }
    }
}