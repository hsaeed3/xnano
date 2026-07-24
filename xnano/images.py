"""xnano.images

---

Optional Pillow-backed image and animation rendering for terminal cells.
"""

from __future__ import annotations

import dataclasses
import io
import math
import os
import struct
import time
import zlib
from typing import BinaryIO, Literal, TypeAlias

from xnano._types import Size
from xnano.components.abstract import AbstractComponent, ComponentRenderContext
from xnano.core.content import CellCanvas, CellSpan

ImageFit: TypeAlias = Literal[
    "crop",
    "contain",
    "cover",
    "stretch",
    "smart",
]
"""How source pixels are placed inside the available terminal area."""

HorizontalPixelsPerCell: TypeAlias = Literal[1, 2]
"""Number of adjacent source pixels sampled into each terminal cell."""


@dataclasses.dataclass(frozen=True, slots=True)
class _RasterFrame:
    """One decoded full-resolution RGB animation frame."""

    pixels: bytes
    width: int
    height: int
    duration_ms: int


@dataclasses.dataclass(frozen=True, slots=True)
class ImageFrame:
    """One native-resolution RGB frame and its display duration.

    Attributes:
        pixels: Packed row-major RGB bytes.
        duration_ms: Display duration in milliseconds.
    """

    pixels: bytes
    """Packed row-major RGB bytes."""
    duration_ms: int = 100
    """Display duration in milliseconds."""


@dataclasses.dataclass(frozen=True, slots=True)
class ImageData:
    """Decoded image frames independent of Pillow and the render engine.

    Attributes:
        width: Native pixel width shared by every frame.
        height: Native pixel height shared by every frame.
        frames: RGB frames in playback order.
    """

    width: int
    """Native pixel width shared by every frame."""
    height: int
    """Native pixel height shared by every frame."""
    frames: tuple[ImageFrame, ...]
    """RGB frames in playback order."""

    def __post_init__(self) -> None:
        expected_size = self.width * self.height * 3
        if self.width < 1 or self.height < 1 or not self.frames:
            raise ValueError(
                "Image data requires positive dimensions and frames."
            )
        if any(len(frame.pixels) != expected_size for frame in self.frames):
            raise ValueError(
                "Image frame RGB data does not match its dimensions."
            )

    @classmethod
    def from_bytes(cls, data: bytes) -> ImageData:
        """Decode xnano's compact, Pillow-free animation container.

        Args:
            data: Bytes produced by ``scripts/precompute_demo_image.py``.

        Returns:
            Decoded full-resolution RGB image data.
        """
        if data[:4] != b"XNI1":
            raise ValueError("Image data does not have an XNI1 header.")
        try:
            width, height, frame_count = struct.unpack_from(">HHH", data, 4)
            offset = 10
            frames: list[ImageFrame] = []
            pixel_count = width * height
            for _ in range(frame_count):
                duration_ms, color_count, compressed_size = struct.unpack_from(
                    ">HHI", data, offset
                )
                offset += 8
                palette_size = color_count * 3
                palette = data[offset : offset + palette_size]
                offset += palette_size
                compressed = data[offset : offset + compressed_size]
                offset += compressed_size
                indexes = zlib.decompress(compressed)
                if len(indexes) != pixel_count:
                    raise ValueError("Image frame has an invalid pixel count.")
                pixels = bytearray(pixel_count * 3)
                for pixel_index, color_index in enumerate(indexes):
                    palette_offset = color_index * 3
                    pixel_offset = pixel_index * 3
                    pixels[pixel_offset : pixel_offset + 3] = palette[
                        palette_offset : palette_offset + 3
                    ]
                frames.append(ImageFrame(bytes(pixels), max(10, duration_ms)))
        except (struct.error, zlib.error) as error:
            raise ValueError("Image data is truncated or corrupt.") from error
        if offset != len(data):
            raise ValueError("Image data contains unexpected trailing bytes.")
        return cls(width=width, height=height, frames=tuple(frames))


ImageSource: TypeAlias = str | os.PathLike[str] | bytes | BinaryIO | ImageData
"""A filesystem path, encoded image bytes, stream, or decoded image data."""


def _get_pillow_image_module():
    """Import Pillow on demand with an actionable optional-extra error."""
    try:
        from PIL import Image as pillow_image
    except ImportError as error:
        raise ImportError(
            "Image rendering requires Pillow; install xnano[images]."
        ) from error
    return pillow_image


def _open_image_source(source: ImageSource):
    """Open an image source through Pillow without retaining caller streams."""
    pillow_image = _get_pillow_image_module()
    if isinstance(source, bytes):
        return pillow_image.open(io.BytesIO(source))
    return pillow_image.open(source)


def _decode_image_frames(
    source: ImageSource,
    background: tuple[int, int, int],
) -> tuple[_RasterFrame, ...]:
    """Decode and composite every source frame at its native resolution."""
    if isinstance(source, ImageData):
        return tuple(
            _RasterFrame(
                pixels=frame.pixels,
                width=source.width,
                height=source.height,
                duration_ms=max(10, frame.duration_ms),
            )
            for frame in source.frames
        )
    image = _open_image_source(source)
    frames: list[_RasterFrame] = []
    try:
        frame_count = int(getattr(image, "n_frames", 1))
        fallback_duration = max(10, int(image.info.get("duration", 100)))
        for frame_index in range(frame_count):
            image.seek(frame_index)
            duration_ms = max(
                10,
                int(image.info.get("duration", fallback_duration)),
            )
            rgba = image.convert("RGBA")
            if rgba.getextrema()[3] != (255, 255):
                pillow_image = _get_pillow_image_module()
                base = pillow_image.new("RGBA", rgba.size, (*background, 255))
                rgba = pillow_image.alpha_composite(base, rgba)
            rgb = rgba.convert("RGB")
            frames.append(
                _RasterFrame(
                    pixels=rgb.tobytes(),
                    width=rgb.width,
                    height=rgb.height,
                    duration_ms=duration_ms,
                )
            )
    finally:
        image.close()
    if not frames:
        raise ValueError("The image source contains no frames.")
    return tuple(frames)


def _get_resample_filter(pillow_image):
    """Return Pillow's high-quality resampling filter across versions."""
    resampling = getattr(pillow_image, "Resampling", pillow_image)
    return resampling.LANCZOS


def _resize_frame(
    frame: _RasterFrame,
    width: int,
    height: int,
) -> _RasterFrame:
    """Resize one RGB frame to an exact pixel size."""
    if frame.width == width and frame.height == height:
        return frame
    try:
        pillow_image = _get_pillow_image_module()
    except ImportError:
        return _resize_frame_without_pillow(frame, width, height)
    image = pillow_image.frombytes(
        "RGB", (frame.width, frame.height), frame.pixels
    )
    resized = image.resize(
        (max(1, width), max(1, height)),
        _get_resample_filter(pillow_image),
    )
    return _RasterFrame(
        pixels=resized.tobytes(),
        width=resized.width,
        height=resized.height,
        duration_ms=frame.duration_ms,
    )


def _resize_frame_without_pillow(
    frame: _RasterFrame,
    width: int,
    height: int,
) -> _RasterFrame:
    """Resize one RGB frame using dependency-free nearest sampling."""
    target_width = max(1, width)
    target_height = max(1, height)
    source_columns = [
        min(frame.width - 1, column * frame.width // target_width)
        for column in range(target_width)
    ]
    output = bytearray(target_width * target_height * 3)
    for target_row in range(target_height):
        source_row = min(
            frame.height - 1,
            target_row * frame.height // target_height,
        )
        source_row_offset = source_row * frame.width * 3
        output_row_offset = target_row * target_width * 3
        for target_column, source_column in enumerate(source_columns):
            source_offset = source_row_offset + source_column * 3
            output_offset = output_row_offset + target_column * 3
            output[output_offset : output_offset + 3] = frame.pixels[
                source_offset : source_offset + 3
            ]
    return _RasterFrame(
        pixels=bytes(output),
        width=target_width,
        height=target_height,
        duration_ms=frame.duration_ms,
    )


def _fit_frame(
    frame: _RasterFrame,
    width: int,
    pixel_height: int,
    fit: ImageFit,
    background: tuple[int, int, int],
) -> _RasterFrame:
    """Center, crop, or scale a frame into the target pixel rectangle."""
    target_width = max(1, width)
    target_height = max(1, pixel_height)
    source = frame
    resolved_fit = fit
    if fit == "smart":
        source_ratio = frame.width / frame.height
        target_ratio = target_width / target_height
        ratio_mismatch = max(
            source_ratio / target_ratio,
            target_ratio / source_ratio,
        )
        resolved_fit = "cover" if ratio_mismatch <= 1.2 else "contain"
    if resolved_fit != "crop":
        horizontal_ratio = target_width / frame.width
        vertical_ratio = target_height / frame.height
        if resolved_fit == "contain":
            ratio = min(horizontal_ratio, vertical_ratio)
            source = _resize_frame(
                frame,
                max(1, round(frame.width * ratio)),
                max(1, round(frame.height * ratio)),
            )
        elif resolved_fit == "cover":
            ratio = max(horizontal_ratio, vertical_ratio)
            source = _resize_frame(
                frame,
                max(1, round(frame.width * ratio)),
                max(1, round(frame.height * ratio)),
            )
        else:
            source = _resize_frame(frame, target_width, target_height)

    output = bytearray(background * (target_width * target_height))
    source_left = max(0, (source.width - target_width) // 2)
    source_top = max(0, (source.height - target_height) // 2)
    output_left = max(0, (target_width - source.width) // 2)
    output_top = max(0, (target_height - source.height) // 2)
    copy_width = min(source.width, target_width)
    copy_height = min(source.height, target_height)
    source_row_bytes = source.width * 3
    output_row_bytes = target_width * 3
    for row_index in range(copy_height):
        source_start = (
            source_top + row_index
        ) * source_row_bytes + source_left * 3
        output_start = (
            output_top + row_index
        ) * output_row_bytes + output_left * 3
        output[output_start : output_start + copy_width * 3] = source.pixels[
            source_start : source_start + copy_width * 3
        ]
    return _RasterFrame(
        pixels=bytes(output),
        width=target_width,
        height=target_height,
        duration_ms=frame.duration_ms,
    )


def _get_pixel_as_rgb(
    frame: _RasterFrame,
    column: int,
    row: int,
) -> tuple[int, int, int]:
    """Return one frame pixel as an RGB tuple."""
    offset = (row * frame.width + column) * 3
    return (
        frame.pixels[offset],
        frame.pixels[offset + 1],
        frame.pixels[offset + 2],
    )


def _get_pixel_group_as_hex(
    frame: _RasterFrame,
    start_column: int,
    row: int,
    horizontal_pixels_per_cell: HorizontalPixelsPerCell,
) -> str:
    """Average one horizontal source-pixel group as truecolor hex."""
    end_column = min(
        frame.width,
        start_column + horizontal_pixels_per_cell,
    )
    colors = [
        _get_pixel_as_rgb(frame, column, row)
        for column in range(start_column, end_column)
    ]
    color_count = len(colors)
    red = (sum(color[0] for color in colors) + color_count // 2) // color_count
    green = (
        sum(color[1] for color in colors) + color_count // 2
    ) // color_count
    blue = (
        sum(color[2] for color in colors) + color_count // 2
    ) // color_count
    return f"#{red:02x}{green:02x}{blue:02x}"


def _get_frame_as_canvas(
    frame: _RasterFrame,
    horizontal_pixels_per_cell: HorizontalPixelsPerCell,
) -> CellCanvas:
    """Map source pixel groups into half-block terminal cells."""
    rows: list[tuple[CellSpan, ...]] = []
    for upper_row in range(0, frame.height, 2):
        lower_row = min(upper_row + 1, frame.height - 1)
        spans: list[CellSpan] = []
        run_text = ""
        run_color: str | None = None
        run_background: str | None = None
        for column in range(0, frame.width, horizontal_pixels_per_cell):
            color = _get_pixel_group_as_hex(
                frame,
                column,
                upper_row,
                horizontal_pixels_per_cell,
            )
            background = _get_pixel_group_as_hex(
                frame,
                column,
                lower_row,
                horizontal_pixels_per_cell,
            )
            if run_text and (
                color != run_color or background != run_background
            ):
                spans.append(
                    CellSpan(
                        run_text, color=run_color, background=run_background
                    )
                )
                run_text = ""
            run_text += "▀"
            run_color = color
            run_background = background
        if run_text:
            spans.append(
                CellSpan(
                    run_text,
                    color=run_color,
                    background=run_background,
                )
            )
        rows.append(tuple(spans))
    return CellCanvas(
        width=math.ceil(frame.width / horizontal_pixels_per_cell),
        height=math.ceil(frame.height / 2),
        rows=tuple(rows),
    )


@dataclasses.dataclass
class Image(AbstractComponent):
    """A native-resolution terminal image or real-time GIF component.

    Pass an ``Image`` to ``Terminal.render`` for a zero-delay still/first
    frame on live and buffer-backed WASM builds. Pass it to ``Terminal.run``
    to play animated formats according to their source frame timings.

    ``crop`` is intentionally the default fit: source pixels are never
    resized. The source and viewport centers align, with oversized content
    cropped and undersized content padded around the center.

    Attributes:
        source: Encoded image path, bytes, or readable binary stream.
        fit: Native crop, contain, cover, stretch, or adaptive placement.
        loop: Whether an animation restarts after its final frame.
        speed: Playback-rate multiplier.
        background: RGB color behind transparency and centered padding.
        horizontal_pixels_per_cell: One for lossless width or two for 2x2
            source-pixel sampling.
        correct_terminal_aspect: Whether to compensate 2x2 sampling for
            terminal cells that are approximately twice as tall as wide.
    """

    source: ImageSource = ""
    """Encoded image path, bytes, or readable binary stream."""
    fit: ImageFit = "crop"
    """Native crop, contain, cover, stretch, or adaptive placement."""
    loop: bool = True
    """Whether an animation restarts after its final frame."""
    speed: float = 1.0
    """Playback-rate multiplier."""
    background: tuple[int, int, int] = (0, 0, 0)
    """RGB color behind transparency and centered padding."""
    horizontal_pixels_per_cell: HorizontalPixelsPerCell = 1
    """Adjacent source pixels sampled into each terminal cell."""
    correct_terminal_aspect: bool = False
    """Whether 2x2 sampling preserves physical terminal proportions."""

    _frames: tuple[_RasterFrame, ...] = dataclasses.field(
        init=False, repr=False
    )
    _frame_ends_ms: tuple[int, ...] = dataclasses.field(init=False, repr=False)
    _duration_ms: int = dataclasses.field(init=False, repr=False)
    _started_at_ns: int | None = dataclasses.field(
        default=None, init=False, repr=False
    )
    _cached_key: (
        tuple[
            int,
            int,
            int,
            ImageFit,
            HorizontalPixelsPerCell,
            bool,
        ]
        | None
    ) = dataclasses.field(default=None, init=False, repr=False)
    _cached_canvas: CellCanvas | None = dataclasses.field(
        default=None, init=False, repr=False
    )

    def __post_init__(self) -> None:
        if self.fit not in (
            "crop",
            "contain",
            "cover",
            "stretch",
            "smart",
        ):
            raise ValueError(f"Unsupported image fit: {self.fit!r}")
        if self.speed <= 0:
            raise ValueError("Image speed must be greater than zero.")
        if self.horizontal_pixels_per_cell not in (1, 2):
            raise ValueError(
                "Horizontal pixels per cell must be either one or two."
            )
        if len(self.background) != 3 or any(
            channel < 0 or channel > 255 for channel in self.background
        ):
            raise ValueError("Image background must contain three RGB bytes.")
        self.fit_content = False
        self._frames = _decode_image_frames(self.source, self.background)
        elapsed = 0
        frame_ends: list[int] = []
        for frame in self._frames:
            elapsed += frame.duration_ms
            frame_ends.append(elapsed)
        self._frame_ends_ms = tuple(frame_ends)
        self._duration_ms = elapsed

    @property
    def frame_count(self) -> int:
        """Number of decoded still or animation frames."""
        return len(self._frames)

    @property
    def duration_ms(self) -> int:
        """Total duration of one animation cycle in milliseconds."""
        return self._duration_ms

    @property
    def finished(self) -> bool:
        """Whether non-looping playback has reached its source duration."""
        if self.loop or self._started_at_ns is None:
            return False
        elapsed_ns = time.monotonic_ns() - self._started_at_ns
        return elapsed_ns * self.speed >= self._duration_ms * 1_000_000

    def get_frame_index(self, elapsed_ms: float) -> int:
        """Return the source frame active at an elapsed playback time.

        Args:
            elapsed_ms: Playback time in milliseconds.

        Returns:
            The zero-based active frame index.
        """
        if len(self._frames) == 1:
            return 0
        position = max(0, int(elapsed_ms * self.speed))
        if self.loop:
            position %= self._duration_ms
        else:
            position = min(position, self._duration_ms - 1)
        for frame_index, frame_end in enumerate(self._frame_ends_ms):
            if position < frame_end:
                return frame_index
        return len(self._frames) - 1

    def restart(self) -> None:
        """Restart animation timing at the next render."""
        self._started_at_ns = None

    def seek(self, position_ms: float) -> None:
        """Move playback to a source timestamp without delaying a render.

        Args:
            position_ms: Source animation timestamp in milliseconds.
        """
        wall_elapsed_ms = max(0.0, position_ms) / self.speed
        self._started_at_ns = time.monotonic_ns() - round(
            wall_elapsed_ms * 1_000_000
        )

    def get_size(self, ctx: ComponentRenderContext) -> Size:
        """Return the native terminal cell dimensions of the source."""
        frame = self._frames[0]
        if self.correct_terminal_aspect:
            width = frame.width
        else:
            width = math.ceil(frame.width / self.horizontal_pixels_per_cell)
        return Size(
            width=width,
            height=math.ceil(frame.height / 2),
        )

    def compose(self, ctx: ComponentRenderContext) -> CellCanvas:
        """Compose the current timed frame for the target terminal area."""
        now_ns = time.monotonic_ns()
        if self._started_at_ns is None:
            self._started_at_ns = now_ns
        elapsed_ms = (now_ns - self._started_at_ns) / 1_000_000
        frame_index = self.get_frame_index(elapsed_ms)
        source = self._frames[frame_index]
        if self.correct_terminal_aspect:
            native_width = source.width
        else:
            native_width = math.ceil(
                source.width / self.horizontal_pixels_per_cell
            )
        width = max(1, ctx.area.width or native_width)
        height = max(1, ctx.area.height or math.ceil(source.height / 2))
        cache_key = (
            frame_index,
            width,
            height,
            self.fit,
            self.horizontal_pixels_per_cell,
            self.correct_terminal_aspect,
        )
        if cache_key == self._cached_key and self._cached_canvas is not None:
            return self._cached_canvas
        fitted_width = width
        if not self.correct_terminal_aspect:
            fitted_width *= self.horizontal_pixels_per_cell
        fitted = _fit_frame(
            source,
            fitted_width,
            height * 2,
            self.fit,
            self.background,
        )
        if (
            self.correct_terminal_aspect
            and self.horizontal_pixels_per_cell == 2
        ):
            fitted = _resize_frame(
                fitted,
                fitted.width * 2,
                fitted.height,
            )
        canvas = _get_frame_as_canvas(
            fitted,
            self.horizontal_pixels_per_cell,
        )
        self._cached_key = cache_key
        self._cached_canvas = canvas
        return canvas


__all__ = (
    "Image",
    "ImageData",
    "ImageFit",
    "ImageFrame",
    "ImageSource",
    "HorizontalPixelsPerCell",
)
