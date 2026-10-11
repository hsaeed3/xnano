//! The compact `XNI1` animation container (the format of xnano's `luffy.xni`).
//!
//! ```text
//! "XNI1" | u16 width | u16 height | u16 frame count   (big-endian)
//! frame  = u16 duration in milliseconds | u16 color count | u32 compressed size
//!          | palette (count * RGB) | zlib(one palette index per pixel)
//! ```

use std::collections::HashMap;

use miniz_oxide::deflate::compress_to_vec_zlib;
use miniz_oxide::inflate::decompress_to_vec_zlib;

use crate::animation::{Animation, Frame};

pub const MAGIC: &[u8; 4] = b"XNI1";

const TRUNCATED: &str = "Cannot decode the XNI1 data: it ends before the last frame is complete. \
                         Pass the complete bytes written by TerminalImage.to_xni.";

fn read_u16(data: &[u8], position: usize) -> Result<u16, String> {
    data.get(position..position + 2)
        .map(|bytes| u16::from_be_bytes([bytes[0], bytes[1]]))
        .ok_or_else(|| TRUNCATED.to_string())
}

fn read_u32(data: &[u8], position: usize) -> Result<u32, String> {
    data.get(position..position + 4)
        .map(|bytes| u32::from_be_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]))
        .ok_or_else(|| TRUNCATED.to_string())
}

pub fn decode(data: &[u8]) -> Result<Animation, String> {
    if data.get(..4) != Some(MAGIC.as_slice()) {
        return Err(
            "Cannot decode the data as XNI1: it does not start with the XNI1 header. Pass \
             the bytes written by TerminalImage.to_xni, or use TerminalImage.from_bytes for other \
             formats."
                .into(),
        );
    }
    let width = u32::from(read_u16(data, 4)?);
    let height = u32::from(read_u16(data, 6)?);
    let count = usize::from(read_u16(data, 8)?);
    let pixels = width as usize * height as usize;
    let mut position = 10;
    let mut frames = Vec::with_capacity(count);
    for index in 0..count {
        let duration = u32::from(read_u16(data, position)?);
        let colors = usize::from(read_u16(data, position + 2)?);
        let size = read_u32(data, position + 4)? as usize;
        position += 8;
        let palette = data.get(position..position + colors * 3).ok_or(TRUNCATED)?;
        position += colors * 3;
        let compressed = data.get(position..position + size).ok_or(TRUNCATED)?;
        position += size;
        let indexes = decompress_to_vec_zlib(compressed).map_err(|error| {
            format!("Cannot decode the XNI1 data: frame {index} is corrupt ({error:?}).")
        })?;
        if indexes.len() != pixels {
            return Err(format!(
                "Cannot decode the XNI1 data: frame {index} holds {} pixels, but a \
                 {width}x{height} image needs {pixels}.",
                indexes.len()
            ));
        }
        let mut rgba = Vec::with_capacity(pixels * 4);
        for &palette_index in &indexes {
            let start = usize::from(palette_index) * 3;
            let color = palette.get(start..start + 3).ok_or_else(|| {
                format!(
                    "Cannot decode the XNI1 data: frame {index} uses palette color \
                     {palette_index}, but its palette has {colors} colors."
                )
            })?;
            rgba.extend_from_slice(&[color[0], color[1], color[2], 255]);
        }
        frames.push(Frame {
            rgba,
            duration_milliseconds: duration.max(10),
        });
    }
    if position != data.len() {
        return Err(format!(
            "Cannot decode the XNI1 data: there are {} extra bytes after the last frame. \
             Pass exactly the bytes written by TerminalImage.to_xni.",
            data.len() - position
        ));
    }
    Animation::new(width, height, frames)
}

/// Encode, quantizing each frame to at most `colors` (2..=256) first.
pub fn encode(animation: &Animation, colors: u16) -> Result<Vec<u8>, String> {
    let frame_count = u16::try_from(animation.frames.len()).map_err(|_| {
        format!(
            "Cannot encode {} frames as XNI1: the format holds at most {} frames. Keep fewer \
             frames with TerminalImage.first_frames.",
            animation.frames.len(),
            u16::MAX
        )
    })?;
    let reduced = animation.quantize(colors, false)?;
    let mut output = Vec::new();
    output.extend_from_slice(MAGIC);
    output.extend_from_slice(&(animation.width as u16).to_be_bytes());
    output.extend_from_slice(&(animation.height as u16).to_be_bytes());
    output.extend_from_slice(&frame_count.to_be_bytes());
    for frame in &reduced.frames {
        let mut palette: Vec<[u8; 3]> = Vec::new();
        let mut lookup: HashMap<[u8; 3], u8> = HashMap::new();
        let indexes: Vec<u8> = frame
            .rgba
            .as_chunks::<4>()
            .0
            .iter()
            .map(|pixel| {
                let color = [pixel[0], pixel[1], pixel[2]];
                *lookup.entry(color).or_insert_with(|| {
                    palette.push(color);
                    (palette.len() - 1) as u8
                })
            })
            .collect();
        let compressed = compress_to_vec_zlib(&indexes, 9);
        let duration = frame.duration_milliseconds.min(u32::from(u16::MAX)) as u16;
        output.extend_from_slice(&duration.to_be_bytes());
        output.extend_from_slice(&(palette.len() as u16).to_be_bytes());
        output.extend_from_slice(&(compressed.len() as u32).to_be_bytes());
        output.extend(palette.iter().flatten());
        output.extend_from_slice(&compressed);
    }
    Ok(output)
}
