//! Terminal graphics protocols (sixel, kitty, iTerm2) through `ratatui-image`.
//!
//! Protocol output is escape-sequence text carried in buffer cells, so it
//! travels through the same cell grid as ordinary half-block frames.

use std::collections::hash_map::RandomState;
use std::hash::BuildHasher;
use std::sync::atomic::{AtomicU32, Ordering};

use image::{DynamicImage, RgbaImage};
use ratatui_core::buffer::Buffer;
use ratatui_core::layout::{Rect, Size};
use ratatui_core::widgets::Widget;
use ratatui_image::picker::{Capability, Picker, ProtocolType};
use ratatui_image::protocol::Protocol;
use ratatui_image::protocol::kitty::Kitty;
use ratatui_image::{Image, Resize};

use crate::animation::{Animation, ResamplingFilter};
use crate::fit::Fit;

pub const PROTOCOL_CHOICES: &str = "'half_blocks', 'sixel', 'kitty' or 'iterm2'";

pub fn parse_protocol(name: &str) -> Result<ProtocolType, String> {
    match name {
        "half_blocks" => Ok(ProtocolType::Halfblocks),
        "sixel" => Ok(ProtocolType::Sixel),
        "kitty" => Ok(ProtocolType::Kitty),
        "iterm2" => Ok(ProtocolType::Iterm2),
        other => Err(format!(
            "Unknown graphics protocol '{other}'. Choose one of {PROTOCOL_CHOICES}."
        )),
    }
}

pub fn protocol_name(protocol: ProtocolType) -> &'static str {
    match protocol {
        ProtocolType::Halfblocks => "half_blocks",
        ProtocolType::Sixel => "sixel",
        ProtocolType::Kitty => "kitty",
        ProtocolType::Iterm2 => "iterm2",
    }
}

pub fn capability_name(capability: &Capability) -> &'static str {
    match capability {
        Capability::Kitty => "kitty",
        Capability::Sixel => "sixel",
        Capability::RectangularOps => "rectangular_operations",
        Capability::KittyCompression => "kitty_compression",
        Capability::CellSize(_) => "cell_size",
        Capability::TextSizingProtocol => "text_sizing_protocol",
        Capability::Background(..) => "background_color",
    }
}

/// A fresh, non-zero kitty image id, so one animation can reuse it for every
/// frame and the terminal replaces the image in place instead of storing a
/// new one per frame.
pub fn new_kitty_image_id() -> u32 {
    static COUNTER: AtomicU32 = AtomicU32::new(0);
    let value = RandomState::new().hash_one(COUNTER.fetch_add(1, Ordering::Relaxed)) as u32;
    value.max(1)
}

/// How one frame is drawn through a graphics protocol.
pub struct ProtocolFrame<'a> {
    pub graphics: &'a Picker,
    pub columns: u32,
    pub rows: u32,
    pub fit: Fit,
    pub resampling_filter: ResamplingFilter,
    /// The kitty image id every frame of one animation shares.
    pub kitty_image_id: Option<u32>,
}

impl ProtocolFrame<'_> {
    /// Render frame `frame_index` of `animation` into a `columns` x `rows` grid.
    pub fn render(&self, animation: &Animation, frame_index: usize) -> Result<Buffer, String> {
        let rgba = RgbaImage::from_raw(
            animation.width,
            animation.height,
            animation.frames[frame_index].rgba.clone(),
        )
        .ok_or("Cannot draw the frame: its pixel data does not match its size.")?;
        let image = DynamicImage::ImageRgba8(rgba);
        let size = Size::new(self.columns as u16, self.rows as u16);
        let filter = Some(self.resampling_filter.image_filter());
        let resize = match self.fit {
            Fit::Crop | Fit::Cover => Resize::Crop(None),
            Fit::Stretch => Resize::Scale(filter),
            Fit::Contain | Fit::Smart => Resize::Fit(filter),
        };
        let protocol = match self.kitty_image_id {
            Some(id) if self.graphics.protocol_type() == ProtocolType::Kitty => {
                self.kitty_protocol(&image, size, &resize, id)?
            }
            _ => self
                .graphics
                .new_protocol(image, size, resize)
                .map_err(|error| {
                    format!("Cannot draw the frame with a graphics protocol: {error}.")
                })?,
        };
        let area = Rect::new(0, 0, size.width, size.height);
        let mut buffer = Buffer::empty(area);
        Image::new(&protocol).render(area, &mut buffer);
        Ok(buffer)
    }

    /// A kitty protocol image with a chosen id, sized the way
    /// [`Picker::new_protocol`] sizes one.
    fn kitty_protocol(
        &self,
        image: &DynamicImage,
        size: Size,
        resize: &Resize,
        id: u32,
    ) -> Result<Protocol, String> {
        let cell_size = self.graphics.font_size();
        let natural = Resize::natural_size(image, cell_size);
        let fits_naturally = !matches!(resize, Resize::Scale(_))
            && natural.width <= size.width
            && natural.height <= size.height
            && (image.width() == u32::from(natural.width) * u32::from(cell_size.width)
                || image.height() == u32::from(natural.height) * u32::from(cell_size.height));
        let (image, area) = if fits_naturally {
            (image.clone(), natural)
        } else {
            let area = resize.size_for(image, cell_size, size);
            (resize.resize(image, cell_size, area, None), area)
        };
        let should_compress = self
            .graphics
            .capabilities()
            .contains(&Capability::KittyCompression);
        Kitty::new(
            image,
            area,
            id,
            self.graphics.tmux_detected(),
            should_compress,
        )
        .map(Protocol::Kitty)
        .map_err(|error| format!("Cannot draw the frame with the kitty protocol: {error}."))
    }
}
