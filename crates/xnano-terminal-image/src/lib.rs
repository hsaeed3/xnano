//! `xnano-image`: image and animation loading, processing and conversion
//! to terminal cells for xnano.
//!
//! It is decoupled from `xnano-core`: the two packages exchange plain bytes in
//! the cell grid (`XCG1`) and cell animation (`XCA1`) formats of the shared
//! `xnano-terminal-cells` crate, because PyO3 extension modules cannot share
//! `#[pyclass]` types.

mod animation;
mod fit;
mod protocol;
mod xni;

use std::io::IsTerminal;
use std::path::PathBuf;
use std::sync::Arc;

use pyo3::create_exception;
use pyo3::exceptions::{PyOSError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyList};
use ratatui_core::buffer::Buffer;
use ratatui_image::picker::{Picker, ProtocolType};
use xnano_terminal_cells::{
    AnimationFrame, CellAnimation, FormatError, MAX_ANIMATION_CELLS, MAX_CELLS, MAX_FRAMES,
};

use crate::animation::{Animation, ResamplingFilter, python_float};
use crate::fit::{Fit, Options, Plan};
use crate::protocol::ProtocolFrame;

create_exception!(
    xnano_image._xnano_image,
    TerminalImageError,
    PyValueError,
    "Raised when image data or an argument is invalid, or an image cannot be processed."
);

create_exception!(
    xnano_image._xnano_image,
    TerminalQueryError,
    PyOSError,
    "Raised when the terminal cannot be asked for its graphics capabilities."
);

/// Longest error message passed to Python; decoder messages can be huge.
const MAX_MESSAGE_CHARACTERS: usize = 400;
/// Largest terminal cell size accepted, in pixels per side.
const MAX_CELL_SIZE_IN_PIXELS: u16 = 1000;

/// Make error text safe to show: control characters (decoders echo raw chunk
/// types and header bytes, and arguments are echoed back) become visible
/// escapes, so an error can never move the cursor or inject terminal
/// sequences.
fn clean_message(message: &str) -> String {
    use std::fmt::Write;
    let mut output = String::with_capacity(message.len().min(MAX_MESSAGE_CHARACTERS) + 8);
    for (count, character) in message.chars().enumerate() {
        if count >= MAX_MESSAGE_CHARACTERS {
            output.push_str("...");
            break;
        }
        match character {
            '\n' | '\t' => output.push(' '),
            character if character.is_control() => {
                let _ = write!(output, "\\x{:02x}", u32::from(character));
            }
            character => output.push(character),
        }
    }
    output
}

fn image_error(message: impl Into<String>) -> PyErr {
    TerminalImageError::new_err(clean_message(&message.into()))
}

fn format_error(operation: &str, error: &FormatError) -> String {
    format!("{operation} failed: {error}.")
}

fn bytes<'py>(py: Python<'py>, data: &[u8]) -> Bound<'py, PyBytes> {
    PyBytes::new(py, data)
}

// ------------------------------------------------------- terminal graphics

/// Terminal graphics capabilities: the protocol to draw with and the cell
/// size in pixels.
#[pyclass(name = "TerminalGraphics", module = "xnano_image._xnano_image", frozen)]
pub struct PyTerminalGraphics {
    graphics: Picker,
}

impl PyTerminalGraphics {
    fn cell_size(&self) -> (u16, u16) {
        let size = self.graphics.font_size();
        (size.width, size.height)
    }
}

#[pymethods]
impl PyTerminalGraphics {
    #[staticmethod]
    fn half_blocks() -> Self {
        Self {
            graphics: Picker::halfblocks(),
        }
    }

    #[staticmethod]
    fn detect(py: Python<'_>) -> PyResult<Self> {
        if !(std::io::stdin().is_terminal() && std::io::stdout().is_terminal()) {
            return Err(TerminalQueryError::new_err(
                "Cannot detect the terminal's graphics capabilities because standard input and \
                 output are not connected to a terminal. Run this call from a program attached \
                 to a terminal, or build the capabilities with \
                 TerminalGraphics.from_capabilities() or TerminalGraphics.half_blocks().",
            ));
        }
        py.detach(Picker::from_query_stdio)
            .map(|graphics| Self { graphics })
            .map_err(|error| {
                TerminalQueryError::new_err(clean_message(&format!(
                    "Cannot detect the terminal's graphics capabilities: {error}. Call \
                     TerminalGraphics.detect() from a program attached to a terminal, \
                     before starting a full-screen session, or build the capabilities with \
                     TerminalGraphics.from_capabilities() or \
                     TerminalGraphics.half_blocks()."
                )))
            })
    }

    #[staticmethod]
    #[pyo3(signature = (*, protocol, cell_size_in_pixels))]
    fn from_capabilities(protocol: &str, cell_size_in_pixels: (u16, u16)) -> PyResult<Self> {
        let protocol = protocol::parse_protocol(protocol).map_err(image_error)?;
        let (width, height) = cell_size_in_pixels;
        let valid = 1..=MAX_CELL_SIZE_IN_PIXELS;
        if !valid.contains(&width) || !valid.contains(&height) {
            return Err(image_error(format!(
                "cell_size_in_pixels must be a (width, height) pair with each side between 1 \
                 and {MAX_CELL_SIZE_IN_PIXELS} pixels, but ({width}, {height}) was given."
            )));
        }
        #[allow(deprecated)]
        let mut graphics = Picker::from_fontsize((width, height).into());
        graphics.set_protocol_type(protocol);
        Ok(Self { graphics })
    }

    #[getter]
    fn protocol(&self) -> &'static str {
        protocol::protocol_name(self.graphics.protocol_type())
    }

    fn with_protocol(&self, protocol: &str) -> PyResult<Self> {
        let mut graphics = self.graphics.clone();
        graphics.set_protocol_type(protocol::parse_protocol(protocol).map_err(image_error)?);
        Ok(Self { graphics })
    }

    #[getter]
    fn cell_size_in_pixels(&self) -> (u16, u16) {
        self.cell_size()
    }

    #[getter]
    fn capabilities(&self) -> Vec<&'static str> {
        self.graphics
            .capabilities()
            .iter()
            .map(protocol::capability_name)
            .collect()
    }

    fn __repr__(&self) -> String {
        let (width, height) = self.cell_size();
        format!(
            "TerminalGraphics(protocol='{}', cell_size_in_pixels=({width}, {height}))",
            self.protocol()
        )
    }

    fn __eq__(&self, other: &Self) -> bool {
        self.graphics.protocol_type() == other.graphics.protocol_type()
            && self.cell_size() == other.cell_size()
    }

    fn __hash__(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        self.protocol().hash(&mut hasher);
        self.cell_size().hash(&mut hasher);
        hasher.finish()
    }

    fn __copy__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __deepcopy__<'py>(slf: PyRef<'py, Self>, _memo: &Bound<'py, PyAny>) -> PyRef<'py, Self> {
        slf
    }
}

// ------------------------------------------------------------- rendering

/// Which frames a conversion renders.
#[derive(Clone, Copy)]
enum FrameSelection {
    One(usize),
    All,
}

fn check_grid_plan(animation: &Animation, plan: &Plan, operation: &str) -> Result<(), String> {
    let cells = u64::from(plan.columns) * u64::from(plan.rows);
    let fits_format = u16::try_from(plan.columns).is_ok()
        && u16::try_from(plan.rows).is_ok()
        && cells <= MAX_CELLS as u64;
    if !fits_format {
        return Err(format!(
            "{operation} cannot convert the {}x{} pixel image: the cell grid would be {}x{} \
             cells ({cells} cells), and a cell grid holds at most {MAX_CELLS} cells. Pass \
             smaller columns or rows, or shrink the image with TerminalImage.resize first.",
            animation.width, animation.height, plan.columns, plan.rows
        ));
    }
    Ok(())
}

fn check_animation_plan(animation: &Animation, plan: &Plan) -> Result<(), String> {
    let frame_count = animation.frames.len();
    if frame_count > MAX_FRAMES {
        return Err(format!(
            "TerminalImage.to_cell_animation cannot convert an image of {frame_count} frames: a \
             cell animation holds at most {MAX_FRAMES} frames. Keep fewer frames with \
             TerminalImage.first_frames first."
        ));
    }
    let total_cells = u64::from(plan.columns) * u64::from(plan.rows) * frame_count as u64;
    if total_cells > MAX_ANIMATION_CELLS as u64 {
        return Err(format!(
            "TerminalImage.to_cell_animation cannot convert {frame_count} frames of {}x{} cells: \
             that is {total_cells} cells in total, and a cell animation holds at most \
             {MAX_ANIMATION_CELLS} cells. Pass smaller columns or rows, or keep fewer frames \
             with TerminalImage.first_frames.",
            plan.columns, plan.rows
        ));
    }
    Ok(())
}

/// Everything one conversion to cells needs.
struct Conversion {
    options: Options,
    graphics: Option<Picker>,
    /// Whether the frames form one cell animation: its size limits apply and
    /// kitty frames share one image id.
    is_cell_animation: bool,
    operation: &'static str,
}

impl Conversion {
    fn render(
        &self,
        animation: &Animation,
        selection: FrameSelection,
    ) -> Result<Vec<Buffer>, String> {
        let plan = fit::plan(animation.width, animation.height, &self.options)?;
        check_grid_plan(animation, &plan, self.operation)?;
        if self.is_cell_animation {
            check_animation_plan(animation, &plan)?;
        }
        let frame_indexes: Vec<usize> = match selection {
            FrameSelection::One(index) if index >= animation.frames.len() => {
                return Err(animation.frame_index_error(index));
            }
            FrameSelection::One(index) => vec![index],
            FrameSelection::All => (0..animation.frames.len()).collect(),
        };
        if let Some(graphics) = &self.graphics {
            let flat = animation.flatten(self.options.background)?;
            let frame = ProtocolFrame {
                graphics,
                columns: plan.columns,
                rows: plan.rows,
                fit: self.options.fit,
                resampling_filter: self.options.resampling_filter,
                kitty_image_id: self.is_cell_animation.then(protocol::new_kitty_image_id),
            };
            return frame_indexes
                .into_iter()
                .map(|index| frame.render(&flat, index))
                .collect();
        }
        let still;
        let selected = match selection {
            FrameSelection::One(index) => {
                still = animation.still_frame(index)?;
                &still
            }
            FrameSelection::All => animation,
        };
        let canvas = fit::apply(selected, &self.options, &plan)?;
        Ok(canvas
            .frames
            .iter()
            .map(|frame| {
                fit::half_blocks(
                    &frame.rgba,
                    canvas.width,
                    canvas.height,
                    self.options.horizontal_pixels_per_cell,
                )
            })
            .collect())
    }
}

#[allow(clippy::too_many_arguments)]
fn conversion(
    operation: &'static str,
    columns: Option<u32>,
    rows: Option<u32>,
    fit_name: &str,
    horizontal_pixels_per_cell: u32,
    should_correct_aspect_ratio: bool,
    background: (u8, u8, u8),
    resampling_filter: &str,
    graphics: Option<&PyTerminalGraphics>,
) -> PyResult<Conversion> {
    Ok(Conversion {
        options: Options {
            columns,
            rows,
            fit: Fit::parse(fit_name).map_err(image_error)?,
            horizontal_pixels_per_cell,
            should_correct_aspect_ratio,
            background: [background.0, background.1, background.2],
            resampling_filter: ResamplingFilter::parse(resampling_filter).map_err(image_error)?,
        },
        graphics: graphics
            .map(|graphics| &graphics.graphics)
            .filter(|graphics| graphics.protocol_type() != ProtocolType::Halfblocks)
            .cloned(),
        is_cell_animation: false,
        operation,
    })
}

// ------------------------------------------------------------------ image

/// A decoded, immutable image or animation.
#[pyclass(name = "TerminalImage", module = "xnano_image._xnano_image", frozen)]
pub struct PyImage {
    animation: Arc<Animation>,
}

impl PyImage {
    fn wrap(animation: Animation) -> Self {
        Self {
            animation: Arc::new(animation),
        }
    }

    /// Run `work` on the animation without holding the GIL.
    fn transform(
        &self,
        py: Python<'_>,
        work: impl FnOnce(&Animation) -> Result<Animation, String> + Send,
    ) -> PyResult<Self> {
        let animation = Arc::clone(&self.animation);
        py.detach(move || work(&animation))
            .map(Self::wrap)
            .map_err(image_error)
    }

    fn render(
        &self,
        py: Python<'_>,
        conversion: Conversion,
        selection: FrameSelection,
    ) -> PyResult<Vec<Buffer>> {
        let animation = Arc::clone(&self.animation);
        py.detach(move || conversion.render(&animation, selection))
            .map_err(image_error)
    }
}

fn pack_grid(operation: &str, buffer: &Buffer) -> PyResult<Vec<u8>> {
    xnano_terminal_cells::pack(buffer).map_err(|error| image_error(format_error(operation, &error)))
}

fn check_scale(name: &str, value: f64) -> PyResult<()> {
    if value.is_finite() && value > 0.0 {
        Ok(())
    } else {
        Err(image_error(format!(
            "{name} must be a finite number greater than zero, but {} was given.",
            python_float(value)
        )))
    }
}

fn scaled_side(side: u32, factor: f64) -> u32 {
    let scaled = (f64::from(side) * factor).round();
    if scaled >= f64::from(u32::MAX) {
        u32::MAX
    } else {
        (scaled as u32).max(1)
    }
}

#[pymethods]
impl PyImage {
    // ------------------------------------------------------------ creation

    #[staticmethod]
    fn open(py: Python<'_>, path: PathBuf) -> PyResult<Self> {
        let data = std::fs::read(&path)?;
        Self::from_bytes(py, &data)
    }

    #[staticmethod]
    fn from_bytes(py: Python<'_>, data: &[u8]) -> PyResult<Self> {
        let owned = data.to_vec();
        py.detach(move || {
            if owned.starts_with(xni::MAGIC) {
                xni::decode(&owned)
            } else {
                Animation::decode(&owned)
            }
        })
        .map(Self::wrap)
        .map_err(image_error)
    }

    #[staticmethod]
    #[pyo3(signature = (width, height, pixels, *, duration_milliseconds = animation::DEFAULT_DURATION_MILLISECONDS))]
    fn from_rgba(
        width: u32,
        height: u32,
        pixels: Vec<u8>,
        duration_milliseconds: u32,
    ) -> PyResult<Self> {
        let frame = animation::Frame {
            rgba: pixels,
            duration_milliseconds,
        };
        Animation::new(width, height, vec![frame])
            .map(Self::wrap)
            .map_err(image_error)
    }

    #[staticmethod]
    fn from_frames(frames: Vec<PyRef<'_, PyImage>>) -> PyResult<Self> {
        let first = frames.first().ok_or_else(|| {
            image_error(
                "TerminalImage.from_frames needs at least one image, but the list is empty. Pass \
                 a list of TerminalImage objects that share one size.",
            )
        })?;
        let (width, height) = (first.animation.width, first.animation.height);
        let mut all_frames = Vec::new();
        for (index, image) in frames.iter().enumerate() {
            if (image.animation.width, image.animation.height) != (width, height) {
                return Err(image_error(format!(
                    "TerminalImage.from_frames needs images that share one size, but image {index} \
                     is {}x{} pixels and the first is {width}x{height}. Resize the images to \
                     one size first.",
                    image.animation.width, image.animation.height
                )));
            }
            all_frames.extend(image.animation.frames.iter().cloned());
        }
        Animation::new(width, height, all_frames)
            .map(Self::wrap)
            .map_err(image_error)
    }

    #[staticmethod]
    fn from_xni(data: &[u8]) -> PyResult<Self> {
        xni::decode(data).map(Self::wrap).map_err(image_error)
    }

    // ---------------------------------------------------------- properties

    #[getter]
    fn width(&self) -> u32 {
        self.animation.width
    }

    #[getter]
    fn height(&self) -> u32 {
        self.animation.height
    }

    #[getter]
    fn frame_count(&self) -> usize {
        self.animation.frames.len()
    }

    #[getter]
    fn duration_milliseconds(&self) -> u64 {
        self.animation.total_duration_milliseconds()
    }

    #[getter]
    fn is_animated(&self) -> bool {
        self.animation.frames.len() > 1
    }

    #[getter]
    fn is_opaque(&self) -> bool {
        self.animation.is_opaque()
    }

    fn frame_durations(&self) -> Vec<u32> {
        self.animation
            .frames
            .iter()
            .map(|frame| frame.duration_milliseconds)
            .collect()
    }

    #[pyo3(signature = (elapsed_milliseconds, *, should_loop = true))]
    fn frame_index_at(&self, elapsed_milliseconds: f64, should_loop: bool) -> PyResult<usize> {
        if !elapsed_milliseconds.is_finite() {
            return Err(image_error(format!(
                "elapsed_milliseconds must be a finite number, but {} was given.",
                python_float(elapsed_milliseconds)
            )));
        }
        Ok(self
            .animation
            .frame_index_at(elapsed_milliseconds, should_loop))
    }

    #[pyo3(signature = (frame_index = 0))]
    fn to_rgba<'py>(&self, py: Python<'py>, frame_index: usize) -> PyResult<Bound<'py, PyBytes>> {
        let frame = self
            .animation
            .frames
            .get(frame_index)
            .ok_or_else(|| image_error(self.animation.frame_index_error(frame_index)))?;
        Ok(bytes(py, &frame.rgba))
    }

    // ----------------------------------------------------------- transforms

    #[pyo3(signature = (width, height, *, resampling_filter = "lanczos3"))]
    fn resize(
        &self,
        py: Python<'_>,
        width: u32,
        height: u32,
        resampling_filter: &str,
    ) -> PyResult<Self> {
        let resampling_filter = ResamplingFilter::parse(resampling_filter).map_err(image_error)?;
        self.transform(py, move |animation| {
            animation.resize(width, height, resampling_filter)
        })
    }

    #[pyo3(signature = (factor, *, resampling_filter = "lanczos3"))]
    fn scale(&self, py: Python<'_>, factor: f64, resampling_filter: &str) -> PyResult<Self> {
        check_scale("factor", factor)?;
        let resampling_filter = ResamplingFilter::parse(resampling_filter).map_err(image_error)?;
        self.transform(py, move |animation| {
            animation.resize(
                scaled_side(animation.width, factor),
                scaled_side(animation.height, factor),
                resampling_filter,
            )
        })
    }

    fn crop(&self, py: Python<'_>, left: u32, top: u32, width: u32, height: u32) -> PyResult<Self> {
        self.transform(py, move |animation| {
            animation.crop(left, top, width, height)
        })
    }

    #[pyo3(signature = (width, height, *, background = (0, 0, 0), left = None, top = None))]
    fn fit_to_canvas(
        &self,
        py: Python<'_>,
        width: u32,
        height: u32,
        background: (u8, u8, u8),
        left: Option<i64>,
        top: Option<i64>,
    ) -> PyResult<Self> {
        self.transform(py, move |animation| {
            animation.fit_to_canvas(
                width,
                height,
                [background.0, background.1, background.2, 255],
                left,
                top,
                1,
            )
        })
    }

    #[pyo3(signature = (
        width, height, *, scale = 1.0, left = None, top = None,
        background = (0, 0, 0), resampling_filter = "lanczos3",
    ))]
    #[allow(clippy::too_many_arguments)]
    fn focal_crop(
        &self,
        py: Python<'_>,
        width: u32,
        height: u32,
        scale: f64,
        left: Option<i64>,
        top: Option<i64>,
        background: (u8, u8, u8),
        resampling_filter: &str,
    ) -> PyResult<Self> {
        check_scale("scale", scale)?;
        let resampling_filter = ResamplingFilter::parse(resampling_filter).map_err(image_error)?;
        self.transform(py, move |animation| {
            let flat = animation.flatten([background.0, background.1, background.2])?;
            let scaled = if (scale - 1.0).abs() < f64::EPSILON {
                flat
            } else {
                flat.resize(
                    scaled_side(animation.width, scale),
                    scaled_side(animation.height, scale),
                    resampling_filter,
                )?
            };
            scaled.fit_to_canvas(
                width,
                height,
                [background.0, background.1, background.2, 255],
                left,
                top,
                1,
            )
        })
    }

    #[pyo3(signature = (background = (0, 0, 0)))]
    fn flatten(&self, py: Python<'_>, background: (u8, u8, u8)) -> PyResult<Self> {
        self.transform(py, move |animation| {
            animation.flatten([background.0, background.1, background.2])
        })
    }

    #[pyo3(signature = (colors = 64, *, should_dither = false))]
    fn quantize(&self, py: Python<'_>, colors: u16, should_dither: bool) -> PyResult<Self> {
        self.transform(py, move |animation| {
            animation.quantize(colors, should_dither)
        })
    }

    fn first_frames(&self, py: Python<'_>, count: usize) -> PyResult<Self> {
        self.transform(py, move |animation| animation.first_frames(count))
    }

    fn still_frame(&self, py: Python<'_>, frame_index: usize) -> PyResult<Self> {
        self.transform(py, move |animation| animation.still_frame(frame_index))
    }

    fn with_frames_per_second(&self, py: Python<'_>, frames_per_second: f64) -> PyResult<Self> {
        self.transform(py, move |animation| {
            animation.with_frames_per_second(frames_per_second)
        })
    }

    fn with_speed(&self, py: Python<'_>, factor: f64) -> PyResult<Self> {
        self.transform(py, move |animation| animation.with_speed(factor))
    }

    // --------------------------------------------------- terminal rendering

    #[pyo3(signature = (
        columns = None, rows = None, *, fit = "contain",
        horizontal_pixels_per_cell = 1, should_correct_aspect_ratio = false,
        background = (0, 0, 0), resampling_filter = "lanczos3", frame_index = 0,
        graphics = None,
    ))]
    #[allow(clippy::too_many_arguments)]
    fn to_cell_grid<'py>(
        &self,
        py: Python<'py>,
        columns: Option<u32>,
        rows: Option<u32>,
        fit: &str,
        horizontal_pixels_per_cell: u32,
        should_correct_aspect_ratio: bool,
        background: (u8, u8, u8),
        resampling_filter: &str,
        frame_index: usize,
        graphics: Option<PyRef<'_, PyTerminalGraphics>>,
    ) -> PyResult<Bound<'py, PyBytes>> {
        const OPERATION: &str = "TerminalImage.to_cell_grid";
        let conversion = conversion(
            OPERATION,
            columns,
            rows,
            fit,
            horizontal_pixels_per_cell,
            should_correct_aspect_ratio,
            background,
            resampling_filter,
            graphics.as_deref(),
        )?;
        let buffers = self.render(py, conversion, FrameSelection::One(frame_index))?;
        Ok(bytes(py, &pack_grid(OPERATION, &buffers[0])?))
    }

    #[pyo3(signature = (
        columns = None, rows = None, *, fit = "contain",
        horizontal_pixels_per_cell = 1, should_correct_aspect_ratio = false,
        background = (0, 0, 0), resampling_filter = "lanczos3", graphics = None,
    ))]
    #[allow(clippy::too_many_arguments)]
    fn to_cell_grids<'py>(
        &self,
        py: Python<'py>,
        columns: Option<u32>,
        rows: Option<u32>,
        fit: &str,
        horizontal_pixels_per_cell: u32,
        should_correct_aspect_ratio: bool,
        background: (u8, u8, u8),
        resampling_filter: &str,
        graphics: Option<PyRef<'_, PyTerminalGraphics>>,
    ) -> PyResult<Bound<'py, PyList>> {
        const OPERATION: &str = "TerminalImage.to_cell_grids";
        let conversion = conversion(
            OPERATION,
            columns,
            rows,
            fit,
            horizontal_pixels_per_cell,
            should_correct_aspect_ratio,
            background,
            resampling_filter,
            graphics.as_deref(),
        )?;
        let buffers = self.render(py, conversion, FrameSelection::All)?;
        let grids = buffers
            .iter()
            .map(|buffer| pack_grid(OPERATION, buffer).map(|grid| bytes(py, &grid)))
            .collect::<PyResult<Vec<_>>>()?;
        PyList::new(py, grids)
    }

    #[pyo3(signature = (
        columns = None, rows = None, *, should_loop = true, fit = "contain",
        horizontal_pixels_per_cell = 1, should_correct_aspect_ratio = false,
        background = (0, 0, 0), resampling_filter = "lanczos3", graphics = None,
    ))]
    #[allow(clippy::too_many_arguments)]
    fn to_cell_animation<'py>(
        &self,
        py: Python<'py>,
        columns: Option<u32>,
        rows: Option<u32>,
        should_loop: bool,
        fit: &str,
        horizontal_pixels_per_cell: u32,
        should_correct_aspect_ratio: bool,
        background: (u8, u8, u8),
        resampling_filter: &str,
        graphics: Option<PyRef<'_, PyTerminalGraphics>>,
    ) -> PyResult<Bound<'py, PyBytes>> {
        const OPERATION: &str = "TerminalImage.to_cell_animation";
        let mut conversion = conversion(
            OPERATION,
            columns,
            rows,
            fit,
            horizontal_pixels_per_cell,
            should_correct_aspect_ratio,
            background,
            resampling_filter,
            graphics.as_deref(),
        )?;
        conversion.is_cell_animation = true;
        let animation = Arc::clone(&self.animation);
        let packed = py
            .detach(move || {
                let buffers = conversion.render(&animation, FrameSelection::All)?;
                let frames = buffers
                    .into_iter()
                    .zip(&animation.frames)
                    .map(|(grid, frame)| AnimationFrame {
                        grid,
                        duration_milliseconds: frame.duration_milliseconds,
                    })
                    .collect();
                xnano_terminal_cells::pack_animation(&CellAnimation {
                    frames,
                    should_loop,
                })
                .map_err(|error| format_error(OPERATION, &error))
            })
            .map_err(image_error)?;
        Ok(bytes(py, &packed))
    }

    #[pyo3(signature = (
        columns = None, rows = None, *, fit = "contain",
        horizontal_pixels_per_cell = 1, should_correct_aspect_ratio = false,
        background = (0, 0, 0), resampling_filter = "lanczos3", frame_index = 0,
    ))]
    #[allow(clippy::too_many_arguments)]
    fn to_ansi(
        &self,
        py: Python<'_>,
        columns: Option<u32>,
        rows: Option<u32>,
        fit: &str,
        horizontal_pixels_per_cell: u32,
        should_correct_aspect_ratio: bool,
        background: (u8, u8, u8),
        resampling_filter: &str,
        frame_index: usize,
    ) -> PyResult<String> {
        let conversion = conversion(
            "TerminalImage.to_ansi",
            columns,
            rows,
            fit,
            horizontal_pixels_per_cell,
            should_correct_aspect_ratio,
            background,
            resampling_filter,
            None,
        )?;
        let buffers = self.render(py, conversion, FrameSelection::One(frame_index))?;
        Ok(xnano_terminal_cells::ansi(&buffers[0]))
    }

    // -------------------------------------------------------------- export

    #[pyo3(signature = (image_format = "png"))]
    fn encode<'py>(&self, py: Python<'py>, image_format: &str) -> PyResult<Bound<'py, PyBytes>> {
        let animation = Arc::clone(&self.animation);
        let image_format = image_format.to_string();
        let data = py
            .detach(move || animation.encode(&image_format))
            .map_err(image_error)?;
        Ok(bytes(py, &data))
    }

    fn save(&self, py: Python<'_>, path: PathBuf) -> PyResult<()> {
        let extension = path
            .extension()
            .and_then(|extension| extension.to_str())
            .unwrap_or_default()
            .to_ascii_lowercase();
        if extension != "png" && extension != "gif" {
            return Err(image_error(format!(
                "Cannot save to '{}': the file extension must be .png (first frame) or .gif \
                 (every frame). Change the extension, or call TerminalImage.encode and write the \
                 bytes yourself.",
                path.display()
            )));
        }
        let animation = Arc::clone(&self.animation);
        let data = py
            .detach(move || animation.encode(&extension))
            .map_err(image_error)?;
        std::fs::write(&path, data)?;
        Ok(())
    }

    #[pyo3(signature = (colors = 64))]
    fn to_xni<'py>(&self, py: Python<'py>, colors: u16) -> PyResult<Bound<'py, PyBytes>> {
        let animation = Arc::clone(&self.animation);
        let data = py
            .detach(move || xni::encode(&animation, colors))
            .map_err(image_error)?;
        Ok(bytes(py, &data))
    }

    fn __len__(&self) -> usize {
        self.animation.frames.len()
    }

    fn __repr__(&self) -> String {
        format!(
            "TerminalImage({}x{}, {} frame{}, {} ms)",
            self.animation.width,
            self.animation.height,
            self.animation.frames.len(),
            if self.animation.frames.len() == 1 {
                ""
            } else {
                "s"
            },
            self.animation.total_duration_milliseconds()
        )
    }

    fn __eq__(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.animation, &other.animation)
            || (self.animation.width == other.animation.width
                && self.animation.height == other.animation.height
                && self.animation.frames.len() == other.animation.frames.len()
                && self
                    .animation
                    .frames
                    .iter()
                    .zip(&other.animation.frames)
                    .all(|(left, right)| {
                        left.duration_milliseconds == right.duration_milliseconds
                            && left.rgba == right.rgba
                    }))
    }

    /// Cheap but consistent with `__eq__`: geometry, timing and the start of
    /// each frame (hashing every pixel of a large animation would be slow).
    fn __hash__(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        self.animation.width.hash(&mut hasher);
        self.animation.height.hash(&mut hasher);
        for frame in &self.animation.frames {
            frame.duration_milliseconds.hash(&mut hasher);
            frame.rgba[..frame.rgba.len().min(256)].hash(&mut hasher);
        }
        hasher.finish()
    }

    fn __copy__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __deepcopy__<'py>(slf: PyRef<'py, Self>, _memo: &Bound<'py, PyAny>) -> PyRef<'py, Self> {
        slf
    }
}

// ------------------------------------------------------- cell grid helpers

fn unpack_grid(operation: &str, cell_grid: &[u8]) -> PyResult<Buffer> {
    xnano_terminal_cells::unpack(cell_grid)
        .map_err(|error| image_error(format_error(operation, &error)))
}

#[pyfunction]
fn cell_grid_size(cell_grid: &[u8]) -> PyResult<(u16, u16)> {
    // Validate the whole grid: a header that claims 65535 x 65535 over
    // truncated data is not a grid.
    let buffer = unpack_grid("cell_grid_size", cell_grid)?;
    Ok((buffer.area.width, buffer.area.height))
}

#[pyfunction]
fn cell_grid_to_text(cell_grid: &[u8]) -> PyResult<Vec<String>> {
    unpack_grid("cell_grid_to_text", cell_grid).map(|buffer| xnano_terminal_cells::text(&buffer))
}

#[pyfunction]
fn cell_grid_to_ansi(cell_grid: &[u8]) -> PyResult<String> {
    unpack_grid("cell_grid_to_ansi", cell_grid).map(|buffer| xnano_terminal_cells::ansi(&buffer))
}

#[pymodule(gil_used = false)]
fn _xnano_image(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add("__version__", env!("CARGO_PKG_VERSION"))?;
    module.add(
        "TerminalImageError",
        module.py().get_type::<TerminalImageError>(),
    )?;
    module.add(
        "TerminalQueryError",
        module.py().get_type::<TerminalQueryError>(),
    )?;
    module.add_class::<PyImage>()?;
    module.add_class::<PyTerminalGraphics>()?;
    module.add_function(wrap_pyfunction!(cell_grid_size, module)?)?;
    module.add_function(wrap_pyfunction!(cell_grid_to_text, module)?)?;
    module.add_function(wrap_pyfunction!(cell_grid_to_ansi, module)?)?;
    Ok(())
}
