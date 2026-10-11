//! Fitting an image into a grid of terminal cells, and the half-block encoder.
//!
//! A terminal cell is about twice as tall as it is wide, so one cell holds two
//! vertically stacked pixels (`▀`: foreground = upper, background = lower) and
//! either one or two horizontal pixels (`horizontal_pixels_per_cell`). With
//! one pixel per cell, pixels are square; with two they are half as wide as
//! tall, so a faithful picture must be stretched horizontally by two
//! (`should_correct_aspect_ratio`).

use ratatui_core::buffer::Buffer;
use ratatui_core::layout::Rect;
use ratatui_core::style::Color;

use crate::animation::{Animation, ResamplingFilter};

/// Most columns or rows a caller may request.
const MAX_REQUESTED_CELLS: u32 = 1000;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Fit {
    /// Never resize: center, crop or pad at native pixels.
    Crop,
    /// Scale to fit entirely inside, padding the rest.
    Contain,
    /// Scale to fill entirely, cropping the overflow.
    Cover,
    /// Scale each axis independently to fill exactly.
    Stretch,
    /// `Cover` when the aspect ratios nearly match, otherwise `Contain`.
    Smart,
}

impl Fit {
    pub fn parse(name: &str) -> Result<Self, String> {
        match name {
            "crop" => Ok(Self::Crop),
            "contain" => Ok(Self::Contain),
            "cover" => Ok(Self::Cover),
            "stretch" => Ok(Self::Stretch),
            "smart" => Ok(Self::Smart),
            other => Err(format!(
                "Unknown fit '{other}'. Choose one of 'crop', 'contain', 'cover', 'stretch' \
                 or 'smart'."
            )),
        }
    }
}

/// Where an image lands on the cell grid.
#[derive(Debug, PartialEq)]
pub struct Plan {
    /// Grid size in cells.
    pub columns: u32,
    pub rows: u32,
    /// Size the source is resized to, in grid pixels, before being centered
    /// on the canvas. `None` keeps native size.
    pub scaled: Option<(u32, u32)>,
    /// Canvas size in grid pixels. An axis the caller fixed is exactly
    /// `columns * horizontal_pixels_per_cell` / `rows * 2`; a derived axis fits
    /// the picture with no padding (an odd final pixel row is duplicated by
    /// the cell encoder).
    pub canvas: (u32, u32),
}

/// Everything that decides how an image maps onto cells.
#[derive(Clone)]
pub struct Options {
    pub columns: Option<u32>,
    pub rows: Option<u32>,
    pub fit: Fit,
    /// Horizontal source pixels per cell: 1 or 2.
    pub horizontal_pixels_per_cell: u32,
    pub should_correct_aspect_ratio: bool,
    pub background: [u8; 3],
    pub resampling_filter: ResamplingFilter,
}

pub fn plan(width: u32, height: u32, options: &Options) -> Result<Plan, String> {
    let pixels_per_cell = options.horizontal_pixels_per_cell;
    if !(1..=2).contains(&pixels_per_cell) {
        return Err(format!(
            "horizontal_pixels_per_cell must be 1 or 2, but {pixels_per_cell} was given."
        ));
    }
    for (name, value) in [("columns", options.columns), ("rows", options.rows)] {
        if let Some(value) = value
            && !(1..=MAX_REQUESTED_CELLS).contains(&value)
        {
            return Err(format!(
                "{name} must be between 1 and {MAX_REQUESTED_CELLS}, but {value} was given. \
                 Pass None to derive it from the image's aspect ratio."
            ));
        }
    }
    // Source extent in grid pixels at scale 1.
    let horizontal_stretch = if options.should_correct_aspect_ratio {
        f64::from(pixels_per_cell)
    } else {
        1.0
    };
    let (grid_width, grid_height) = (f64::from(width) * horizontal_stretch, f64::from(height));
    let fit = match (options.fit, options.columns, options.rows) {
        (Fit::Smart, Some(columns), Some(rows)) => {
            let source = grid_width / grid_height;
            let target = f64::from(columns * pixels_per_cell) / f64::from(rows * 2);
            if (source / target).max(target / source) <= 1.2 {
                Fit::Cover
            } else {
                Fit::Contain
            }
        }
        (Fit::Smart, _, _) => Fit::Contain,
        (fit, _, _) => fit,
    };

    let cells = |pixels: f64, per_cell: u32| ((pixels / f64::from(per_cell)).ceil() as u32).max(1);
    let round = |value: f64| value.round().max(1.0) as u32;
    let natural = (round(grid_width), round(grid_height));
    let is_stretched = horizontal_stretch != 1.0;
    match (options.columns, options.rows) {
        (None, None) => Ok(Plan {
            columns: cells(grid_width, pixels_per_cell),
            rows: cells(grid_height, 2),
            scaled: is_stretched.then_some(natural),
            canvas: natural,
        }),
        (Some(columns), None) => {
            let scale = if fit == Fit::Crop {
                1.0
            } else {
                f64::from(columns * pixels_per_cell) / grid_width
            };
            let scaled = (round(grid_width * scale), round(grid_height * scale));
            Ok(Plan {
                columns,
                rows: cells(f64::from(scaled.1), 2),
                scaled: (fit != Fit::Crop || is_stretched).then_some(scaled),
                canvas: (columns * pixels_per_cell, scaled.1),
            })
        }
        (None, Some(rows)) => {
            let scale = if fit == Fit::Crop {
                1.0
            } else {
                f64::from(rows * 2) / grid_height
            };
            let scaled = (round(grid_width * scale), round(grid_height * scale));
            Ok(Plan {
                columns: cells(f64::from(scaled.0), pixels_per_cell),
                rows,
                scaled: (fit != Fit::Crop || is_stretched).then_some(scaled),
                canvas: (scaled.0, rows * 2),
            })
        }
        (Some(columns), Some(rows)) => {
            let (target_width, target_height) =
                (f64::from(columns * pixels_per_cell), f64::from(rows * 2));
            let scaled = match fit {
                Fit::Crop => is_stretched.then_some(natural),
                Fit::Stretch => Some((target_width as u32, target_height as u32)),
                Fit::Contain | Fit::Smart => {
                    let scale = (target_width / grid_width).min(target_height / grid_height);
                    Some((round(grid_width * scale), round(grid_height * scale)))
                }
                Fit::Cover => {
                    let scale = (target_width / grid_width).max(target_height / grid_height);
                    Some((round(grid_width * scale), round(grid_height * scale)))
                }
            };
            Ok(Plan {
                columns,
                rows,
                scaled,
                canvas: (columns * pixels_per_cell, rows * 2),
            })
        }
    }
}

/// Resize and place every frame on the planned canvas, fully opaque.
pub fn apply(animation: &Animation, options: &Options, plan: &Plan) -> Result<Animation, String> {
    let background = options.background;
    let flat = animation.flatten(background)?;
    let sized = match plan.scaled {
        Some((width, height)) => flat.resize(width, height, options.resampling_filter)?,
        None => flat,
    };
    sized.fit_to_canvas(
        plan.canvas.0,
        plan.canvas.1,
        [background[0], background[1], background[2], 255],
        None,
        None,
        2,
    )
}

/// Map an opaque RGBA canvas (`horizontal_pixels_per_cell * columns` wide,
/// `rows * 2` tall) onto half-block cells.
pub fn half_blocks(
    rgba: &[u8],
    width: u32,
    height: u32,
    horizontal_pixels_per_cell: u32,
) -> Buffer {
    let columns = width.div_ceil(horizontal_pixels_per_cell);
    let rows = height.div_ceil(2);
    let mut buffer = Buffer::empty(Rect::new(0, 0, columns as u16, rows as u16));
    let average = |column: u32, pixel_row: u32| -> Color {
        let (mut red, mut green, mut blue) = (0_u32, 0_u32, 0_u32);
        for offset in 0..horizontal_pixels_per_cell {
            let pixel_column = (column * horizontal_pixels_per_cell + offset).min(width - 1);
            let position = ((pixel_row * width + pixel_column) * 4) as usize;
            red += u32::from(rgba[position]);
            green += u32::from(rgba[position + 1]);
            blue += u32::from(rgba[position + 2]);
        }
        let count = horizontal_pixels_per_cell;
        Color::Rgb(
            ((red + count / 2) / count) as u8,
            ((green + count / 2) / count) as u8,
            ((blue + count / 2) / count) as u8,
        )
    };
    for row in 0..rows {
        let upper = row * 2;
        let lower = (upper + 1).min(height - 1);
        for column in 0..columns {
            let cell = &mut buffer[(column as u16, row as u16)];
            cell.set_symbol("▀");
            cell.fg = average(column, upper);
            cell.bg = average(column, lower);
        }
    }
    buffer
}
