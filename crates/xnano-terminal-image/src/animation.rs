//! Decoded animations and the pixel-space operations on them.
//!
//! Every frame is straight (non-premultiplied) RGBA8. All operations return a
//! new [`Animation`]; nothing mutates in place.

use std::io::Cursor;

use fast_image_resize::images::Image;
use fast_image_resize::{FilterType, MulDiv, PixelType, ResizeAlg, ResizeOptions, Resizer};
use image::codecs::gif::{GifDecoder, GifEncoder, Repeat};
use image::codecs::png::PngEncoder;
use image::codecs::webp::WebPDecoder;
use image::{
    AnimationDecoder, Delay, ExtendedColorType, ImageDecoder, ImageEncoder, ImageFormat,
    ImageReader,
};
use quantette::{PaletteSize, Pipeline};

/// Longest side accepted, to bound memory from hostile files.
pub const MAX_SIDE: u32 = 16_384;
/// Cap on total decoded bytes (all frames).
const MAX_BYTES: usize = 1 << 30;
/// Largest canvas an animated file may declare. The decoders allocate a full
/// RGBA canvas per frame up front, so a 20-byte GIF could otherwise claim
/// gigabytes.
const MAX_ANIMATION_PIXELS: u64 = 1 << 26;
/// Most frames a decoded animated file may hold.
const MAX_DECODED_FRAMES: usize = 10_000;
/// Display time of a frame that declares none.
pub const DEFAULT_DURATION_MILLISECONDS: u32 = 100;
/// Shortest display time of any frame.
const MINIMUM_DURATION_MILLISECONDS: u32 = 10;

fn check_canvas(width: u32, height: u32) -> Result<usize, String> {
    if width == 0
        || height == 0
        || width > MAX_SIDE
        || height > MAX_SIDE
        || u64::from(width) * u64::from(height) > MAX_ANIMATION_PIXELS
    {
        return Err(format!(
            "Cannot decode the animation: its canvas of {width}x{height} pixels is too large. \
             An animated image may be at most {MAX_SIDE} pixels per side and \
             {MAX_ANIMATION_PIXELS} pixels in total. Resize the file before loading it."
        ));
    }
    Ok(width as usize * height as usize * 4)
}

/// One frame of an animation.
#[derive(Clone)]
pub struct Frame {
    /// `width * height * 4` straight RGBA bytes.
    pub rgba: Vec<u8>,
    /// How long the frame is shown.
    pub duration_milliseconds: u32,
}

/// A decoded image: one or more frames that share one size.
#[derive(Clone)]
pub struct Animation {
    pub width: u32,
    pub height: u32,
    pub frames: Vec<Frame>,
}

/// The resampling filter used when an image is resized.
#[derive(Clone, Copy)]
pub enum ResamplingFilter {
    Nearest,
    Bilinear,
    CatmullRom,
    Lanczos3,
}

impl ResamplingFilter {
    pub fn parse(name: &str) -> Result<Self, String> {
        match name {
            "nearest" => Ok(Self::Nearest),
            "bilinear" => Ok(Self::Bilinear),
            "catmull_rom" => Ok(Self::CatmullRom),
            "lanczos3" => Ok(Self::Lanczos3),
            other => Err(format!(
                "Unknown resampling_filter '{other}'. Choose one of 'nearest', 'bilinear', \
                 'catmull_rom' or 'lanczos3'."
            )),
        }
    }

    fn algorithm(self) -> ResizeAlg {
        match self {
            Self::Nearest => ResizeAlg::Nearest,
            Self::Bilinear => ResizeAlg::Convolution(FilterType::Bilinear),
            Self::CatmullRom => ResizeAlg::Convolution(FilterType::CatmullRom),
            Self::Lanczos3 => ResizeAlg::Convolution(FilterType::Lanczos3),
        }
    }

    /// The equivalent filter of the `image` crate, used by graphics protocols.
    pub fn image_filter(self) -> image::imageops::FilterType {
        match self {
            Self::Nearest => image::imageops::FilterType::Nearest,
            Self::Bilinear => image::imageops::FilterType::Triangle,
            Self::CatmullRom => image::imageops::FilterType::CatmullRom,
            Self::Lanczos3 => image::imageops::FilterType::Lanczos3,
        }
    }
}

/// GIF and browser convention: a zero delay means the default, and nothing
/// plays faster than [`MINIMUM_DURATION_MILLISECONDS`].
fn normalize_duration(milliseconds: u32) -> u32 {
    if milliseconds == 0 {
        DEFAULT_DURATION_MILLISECONDS
    } else {
        milliseconds.max(MINIMUM_DURATION_MILLISECONDS)
    }
}

/// A float written the way Python shows it: `0.0`, `nan`, `inf`.
pub fn python_float(value: f64) -> String {
    if value.is_nan() {
        "nan".to_string()
    } else if value.is_infinite() {
        if value > 0.0 { "inf" } else { "-inf" }.to_string()
    } else {
        format!("{value:?}")
    }
}

fn check_target_size(operation: &str, width: u32, height: u32) -> Result<(), String> {
    if width == 0 || height == 0 || width > MAX_SIDE || height > MAX_SIDE {
        return Err(format!(
            "Cannot {operation} to {width}x{height} pixels: each side must be between 1 and \
             {MAX_SIDE} pixels. Pass a width and height in that range."
        ));
    }
    Ok(())
}

impl Animation {
    pub fn single(width: u32, height: u32, rgba: Vec<u8>) -> Result<Self, String> {
        Self::new(
            width,
            height,
            vec![Frame {
                rgba,
                duration_milliseconds: DEFAULT_DURATION_MILLISECONDS,
            }],
        )
    }

    pub fn new(width: u32, height: u32, frames: Vec<Frame>) -> Result<Self, String> {
        if width == 0 || height == 0 || width > MAX_SIDE || height > MAX_SIDE {
            return Err(format!(
                "Cannot create an image of {width}x{height} pixels: each side must be between \
                 1 and {MAX_SIDE} pixels."
            ));
        }
        if frames.is_empty() {
            return Err("Cannot create an image without frames: pass at least one frame.".into());
        }
        let expected = width as usize * height as usize * 4;
        if frames.len().saturating_mul(expected) > MAX_BYTES {
            return Err(format!(
                "Cannot create an image of {} frames at {width}x{height} pixels: it would hold \
                 more than 1 GiB of pixels. Use fewer frames or a smaller size.",
                frames.len()
            ));
        }
        if let Some(index) = frames.iter().position(|frame| frame.rgba.len() != expected) {
            return Err(format!(
                "Cannot create an image of {width}x{height} pixels: frame {index} holds {} \
                 bytes, but each frame needs width * height * 4 = {expected} RGBA bytes.",
                frames[index].rgba.len()
            ));
        }
        Ok(Self {
            width,
            height,
            frames,
        })
    }

    pub fn total_duration_milliseconds(&self) -> u64 {
        self.frames
            .iter()
            .map(|frame| u64::from(frame.duration_milliseconds))
            .sum()
    }

    /// Index of the frame showing at `elapsed_milliseconds`, looping or
    /// holding the last frame.
    pub fn frame_index_at(&self, elapsed_milliseconds: f64, should_loop: bool) -> usize {
        let total = self.total_duration_milliseconds().max(1) as f64;
        let mut position = elapsed_milliseconds.max(0.0);
        if should_loop {
            position %= total;
        } else if position >= total {
            return self.frames.len() - 1;
        }
        let mut end = 0.0;
        for (index, frame) in self.frames.iter().enumerate() {
            end += f64::from(frame.duration_milliseconds);
            if position < end {
                return index;
            }
        }
        self.frames.len() - 1
    }

    pub fn is_opaque(&self) -> bool {
        self.frames.iter().all(|frame| {
            frame
                .rgba
                .as_chunks::<4>()
                .0
                .iter()
                .all(|pixel| pixel[3] == 255)
        })
    }

    fn map_frames(
        &self,
        width: u32,
        height: u32,
        mut transform: impl FnMut(&Frame) -> Result<Vec<u8>, String>,
    ) -> Result<Self, String> {
        let frames = self
            .frames
            .iter()
            .map(|frame| {
                Ok(Frame {
                    rgba: transform(frame)?,
                    duration_milliseconds: frame.duration_milliseconds,
                })
            })
            .collect::<Result<Vec<_>, String>>()?;
        Self::new(width, height, frames)
    }

    // --------------------------------------------------------------- decode

    pub fn decode(data: &[u8]) -> Result<Self, String> {
        let reader = ImageReader::new(Cursor::new(data))
            .with_guessed_format()
            .map_err(|error| format!("Cannot read the image data: {error}."))?;
        let format = reader.format().ok_or(
            "Cannot decode the data: it is not a PNG, JPEG, GIF, WebP or XNI1 image. \
             Check that the bytes or file hold one of those formats.",
        )?;
        let frames = match format {
            ImageFormat::Gif => {
                let decoder = GifDecoder::new(Cursor::new(data)).map_err(decode_error)?;
                let (width, height) = decoder.dimensions();
                collect_frames(decoder.into_frames(), check_canvas(width, height)?)?
            }
            ImageFormat::WebP => {
                let decoder = WebPDecoder::new(Cursor::new(data)).map_err(decode_error)?;
                if decoder.has_animation() {
                    let (width, height) = decoder.dimensions();
                    collect_frames(decoder.into_frames(), check_canvas(width, height)?)?
                } else {
                    return Self::decode_static(reader);
                }
            }
            _ => return Self::decode_static(reader),
        };
        let (width, height) = (frames[0].0.width(), frames[0].0.height());
        let frames = frames
            .into_iter()
            .map(|(buffer, milliseconds)| Frame {
                rgba: buffer.into_raw(),
                duration_milliseconds: normalize_duration(milliseconds),
            })
            .collect();
        Self::new(width, height, frames)
    }

    fn decode_static(reader: ImageReader<Cursor<&[u8]>>) -> Result<Self, String> {
        let decoded = reader.decode().map_err(decode_error)?.to_rgba8();
        Self::single(decoded.width(), decoded.height(), decoded.into_raw())
    }

    // --------------------------------------------------------------- encode

    pub fn encode(&self, image_format: &str) -> Result<Vec<u8>, String> {
        let mut output = Vec::new();
        match image_format {
            "png" => PngEncoder::new(&mut output)
                .write_image(
                    &self.frames[0].rgba,
                    self.width,
                    self.height,
                    ExtendedColorType::Rgba8,
                )
                .map_err(encode_error)?,
            "gif" => {
                let mut encoder = GifEncoder::new_with_speed(&mut output, 10);
                encoder.set_repeat(Repeat::Infinite).map_err(encode_error)?;
                let frames = self.frames.iter().map(|frame| {
                    let buffer =
                        image::RgbaImage::from_raw(self.width, self.height, frame.rgba.clone())
                            .expect("frame length was validated");
                    image::Frame::from_parts(
                        buffer,
                        0,
                        0,
                        Delay::from_numer_denom_ms(frame.duration_milliseconds, 1),
                    )
                });
                encoder.encode_frames(frames).map_err(encode_error)?;
            }
            other => {
                return Err(format!(
                    "Cannot encode the image as '{other}'. Choose image_format 'png' (first \
                     frame) or 'gif' (every frame)."
                ));
            }
        }
        Ok(output)
    }

    // ------------------------------------------------------------ transforms

    /// Resize every frame to exactly `width` x `height`.
    pub fn resize(
        &self,
        width: u32,
        height: u32,
        resampling_filter: ResamplingFilter,
    ) -> Result<Self, String> {
        check_target_size("resize", width, height)?;
        if (width, height) == (self.width, self.height) {
            return Ok(self.clone());
        }
        let is_opaque = self.is_opaque();
        let options = ResizeOptions::new().resize_alg(resampling_filter.algorithm());
        let mut resizer = Resizer::new();
        let alpha_math = MulDiv::default();
        self.map_frames(width, height, |frame| {
            let mut source =
                Image::from_vec_u8(self.width, self.height, frame.rgba.clone(), PixelType::U8x4)
                    .map_err(resize_error)?;
            if !is_opaque {
                alpha_math
                    .multiply_alpha_inplace(&mut source)
                    .map_err(resize_error)?;
            }
            let mut target = Image::new(width, height, PixelType::U8x4);
            resizer
                .resize(&source, &mut target, &options)
                .map_err(resize_error)?;
            if !is_opaque {
                alpha_math
                    .divide_alpha_inplace(&mut target)
                    .map_err(resize_error)?;
            }
            Ok(target.into_vec())
        })
    }

    /// Place every frame on a `width` x `height` canvas filled with
    /// `background`, centered (padding when smaller, cropping when larger).
    /// `crop_left`/`crop_top` give the source's top-left corner within the
    /// crop instead of centering it. Centered vertical offsets are snapped
    /// down to a multiple of `vertical_alignment` (2 keeps half-block pixels
    /// paired).
    pub fn fit_to_canvas(
        &self,
        width: u32,
        height: u32,
        background: [u8; 4],
        crop_left: Option<i64>,
        crop_top: Option<i64>,
        vertical_alignment: i64,
    ) -> Result<Self, String> {
        check_target_size("fit to a canvas", width, height)?;
        let (source_width, source_height) = (i64::from(self.width), i64::from(self.height));
        let (target_width, target_height) = (i64::from(width), i64::from(height));
        // Source window that is copied, and where it lands on the canvas.
        let clamp = |value: i64, maximum: i64| value.clamp(0, maximum.max(0));
        let snap = |value: i64| value - value % vertical_alignment.max(1);
        let source_left = clamp(
            crop_left.unwrap_or((source_width - target_width) / 2),
            source_width - target_width,
        );
        let source_top = clamp(
            crop_top.unwrap_or_else(|| snap((source_height - target_height) / 2)),
            source_height - target_height,
        );
        let destination_left = ((target_width - source_width) / 2).max(0);
        let destination_top = snap(((target_height - source_height) / 2).max(0));
        let copy_width = source_width.min(target_width);
        let copy_height = source_height.min(target_height);
        self.map_frames(width, height, |frame| {
            let mut output = background.repeat(width as usize * height as usize);
            for row in 0..copy_height {
                let from = (((source_top + row) * source_width + source_left) * 4) as usize;
                let to = (((destination_top + row) * target_width + destination_left) * 4) as usize;
                let length = (copy_width * 4) as usize;
                output[to..to + length].copy_from_slice(&frame.rgba[from..from + length]);
            }
            Ok(output)
        })
    }

    pub fn crop(&self, left: u32, top: u32, width: u32, height: u32) -> Result<Self, String> {
        if width == 0
            || height == 0
            || left.saturating_add(width) > self.width
            || top.saturating_add(height) > self.height
        {
            return Err(format!(
                "Cannot crop {width}x{height} pixels at ({left}, {top}): the rectangle must have \
                 a width and height of at least 1 and fit inside the {}x{} pixel image.",
                self.width, self.height
            ));
        }
        self.map_frames(width, height, |frame| {
            let mut output = Vec::with_capacity(width as usize * height as usize * 4);
            for row in top..top + height {
                let from = ((row * self.width + left) * 4) as usize;
                output.extend_from_slice(&frame.rgba[from..from + width as usize * 4]);
            }
            Ok(output)
        })
    }

    /// Composite onto a solid color, making every pixel opaque.
    pub fn flatten(&self, background: [u8; 3]) -> Result<Self, String> {
        if self.is_opaque() {
            return Ok(self.clone());
        }
        self.map_frames(self.width, self.height, |frame| {
            let mut output = frame.rgba.clone();
            for pixel in output.as_chunks_mut::<4>().0 {
                let alpha = u32::from(pixel[3]);
                for (channel, &background_channel) in pixel[..3].iter_mut().zip(&background) {
                    let blended = (u32::from(*channel) * alpha
                        + u32::from(background_channel) * (255 - alpha)
                        + 127)
                        / 255;
                    *channel = blended as u8;
                }
                pixel[3] = 255;
            }
            Ok(output)
        })
    }

    /// Reduce each frame to an adaptive palette of at most `colors` colors.
    pub fn quantize(&self, colors: u16, should_dither: bool) -> Result<Self, String> {
        if !(2..=256).contains(&colors) {
            return Err(format!(
                "Cannot quantize to {colors} colors: colors must be between 2 and 256."
            ));
        }
        let flat = self.flatten([0, 0, 0])?;
        let palette_size = PaletteSize::try_from_u16(colors).ok_or_else(|| {
            format!("Cannot quantize to {colors} colors: colors must be between 2 and 256.")
        })?;
        flat.map_frames(flat.width, flat.height, |frame| {
            let pixels: Vec<quantette::deps::palette::Srgb<u8>> = frame
                .rgba
                .as_chunks::<4>()
                .0
                .iter()
                .map(|pixel| quantette::deps::palette::Srgb::new(pixel[0], pixel[1], pixel[2]))
                .collect();
            let image = quantette::ImageBuf::new(flat.width, flat.height, pixels)
                .map_err(|error| format!("Cannot quantize the image: {error}."))?;
            let ditherer = if should_dither {
                Some(quantette::dither::FloydSteinberg::new())
            } else {
                None
            };
            let quantized = Pipeline::new()
                .palette_size(palette_size)
                .ditherer(ditherer)
                .input_image(image.as_ref())
                .output_srgb8_image();
            let mut output = Vec::with_capacity(frame.rgba.len());
            for pixel in quantized.as_slice() {
                output.extend_from_slice(&[pixel.red, pixel.green, pixel.blue, 255]);
            }
            Ok(output)
        })
    }

    /// Keep the first `count` frames.
    pub fn first_frames(&self, count: usize) -> Result<Self, String> {
        if count == 0 {
            return Err("Cannot keep the first 0 frames: count must be at least 1.".to_string());
        }
        let mut frames = self.frames.clone();
        frames.truncate(count);
        Self::new(self.width, self.height, frames)
    }

    /// Keep one frame.
    pub fn still_frame(&self, frame_index: usize) -> Result<Self, String> {
        let frame = self
            .frames
            .get(frame_index)
            .ok_or_else(|| self.frame_index_error(frame_index))?;
        Self::new(self.width, self.height, vec![frame.clone()])
    }

    /// The error for a frame index past the last frame.
    pub fn frame_index_error(&self, frame_index: usize) -> String {
        format!(
            "Frame index {frame_index} is out of range: this image has {} frame{}, so \
             frame_index must be between 0 and {}.",
            self.frames.len(),
            if self.frames.len() == 1 { "" } else { "s" },
            self.frames.len() - 1
        )
    }

    /// Give frames an even cadence of `frames_per_second`, keeping the order.
    pub fn with_frames_per_second(&self, frames_per_second: f64) -> Result<Self, String> {
        if !(frames_per_second.is_finite() && frames_per_second > 0.0) {
            return Err(format!(
                "Cannot play at {} frames per second: frames_per_second must be a finite \
                 number greater than zero.",
                python_float(frames_per_second)
            ));
        }
        let mut output = self.clone();
        for (index, frame) in output.frames.iter_mut().enumerate() {
            let start = (index as f64 * 1000.0 / frames_per_second).round();
            let end = ((index + 1) as f64 * 1000.0 / frames_per_second).round();
            frame.duration_milliseconds = ((end - start) as u32).max(MINIMUM_DURATION_MILLISECONDS);
        }
        Ok(output)
    }

    /// Play `factor` times faster (2.0 halves every duration).
    pub fn with_speed(&self, factor: f64) -> Result<Self, String> {
        if !(factor.is_finite() && factor > 0.0) {
            return Err(format!(
                "Cannot change the speed by a factor of {}: factor must be a finite number \
                 greater than zero (2.0 plays twice as fast).",
                python_float(factor)
            ));
        }
        let mut output = self.clone();
        for frame in &mut output.frames {
            frame.duration_milliseconds =
                ((f64::from(frame.duration_milliseconds) / factor).round() as u32)
                    .max(MINIMUM_DURATION_MILLISECONDS);
        }
        Ok(output)
    }
}

fn decode_error(error: image::ImageError) -> String {
    format!("Cannot decode the image data: {error}. The data is corrupt or unsupported.")
}

fn encode_error(error: image::ImageError) -> String {
    format!("Cannot encode the image: {error}.")
}

fn resize_error(error: impl std::fmt::Display) -> String {
    format!("Cannot resize the image: {error}.")
}

fn collect_frames(
    frames: image::Frames<'_>,
    bytes_per_frame: usize,
) -> Result<Vec<(image::RgbaImage, u32)>, String> {
    let mut output = Vec::new();
    for frame in frames {
        let frame = frame.map_err(decode_error)?;
        let (numerator, denominator) = frame.delay().numer_denom_ms();
        let milliseconds = (f64::from(numerator) / f64::from(denominator.max(1))).round() as u32;
        output.push((frame.into_buffer(), milliseconds));
        if output.len().saturating_mul(bytes_per_frame) > MAX_BYTES {
            return Err(
                "Cannot decode the animation: its frames hold more than 1 GiB of pixels. \
                 Shorten or resize the file before loading it."
                    .to_string(),
            );
        }
        if output.len() > MAX_DECODED_FRAMES {
            return Err(format!(
                "Cannot decode the animation: it has more than {MAX_DECODED_FRAMES} frames. \
                 Shorten the file before loading it."
            ));
        }
    }
    if output.is_empty() {
        return Err("Cannot decode the animation: it contains no frames.".to_string());
    }
    Ok(output)
}
