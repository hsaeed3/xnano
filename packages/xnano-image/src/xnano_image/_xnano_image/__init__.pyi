"""
xnano_image._xnano_image

Type stubs for `xnano_image`'s native rust-extension.

Load, process and convert images and animations (PNG, JPEG, GIF, WebP and the
compact XNI1 container) into terminal cells.

Examples:
    ```python
    image = TerminalImage.open('clip.gif')
    image = image.focal_crop(120, 80, scale=1.5).with_frames_per_second(12).quantize(64)
    animation = image.to_cell_animation(60, 20)  # XCA1 bytes, every frame with its timing
    still = image.to_cell_grid(60, 20)  # XCG1 bytes, one frame
    print(cell_grid_to_ansi(still))
    ```

Conversions return plain ``bytes`` in two formats shared with ``xnano-core``:

- a **cell grid** (``XCG1``) is one terminal frame: the symbol, colors and
  modifiers of every cell;
- a **cell animation** (``XCA1``) is a sequence of cell grids, each with its
  display time in milliseconds.

Use [`cell_grid_to_text`][xnano_image.cell_grid_to_text] and
[`cell_grid_to_ansi`][xnano_image.cell_grid_to_ansi] to inspect or print a
cell grid.

All image operations release the GIL while they work.
"""

import os
from typing import Literal, final

__version__: str
is_optimized_build: bool
"""Whether the extension was built with optimizations. Timing a debug build says nothing."""

# Rust binding
class TerminalImageError(ValueError):
    """
    Raised when image data or an argument is invalid, or an image cannot be processed.

    It is a ``ValueError``, so invalid arguments and undecodable data can be
    handled together. The message names the operation that failed, the value
    that caused it and what is accepted instead.
    """

# Rust binding
class TerminalQueryError(OSError):
    """
    Raised when the terminal cannot be asked for its graphics capabilities.

    [`TerminalGraphics.detect`][xnano_image.TerminalGraphics.detect]
    raises it when standard input or output is not a terminal, or reading the
    terminal's answer fails. Call ``detect`` before starting a full-screen
    session, or build the capabilities without a query using
    [`TerminalGraphics.from_capabilities`][xnano_image.TerminalGraphics.from_capabilities]
    or [`TerminalGraphics.half_blocks`][xnano_image.TerminalGraphics.half_blocks].
    """

# Rust binding
@final
class TerminalGraphics:
    """
    Terminal graphics capabilities: the protocol to draw with and the cell size.

    Pass one as ``graphics=`` to
    [`TerminalImage.to_cell_grid`][xnano_image.TerminalImage.to_cell_grid] or
    [`TerminalImage.to_cell_animation`][xnano_image.TerminalImage.to_cell_animation]
    to draw with the ``sixel``, ``kitty`` or ``iterm2`` protocol instead of
    half-block characters. Instances are immutable and hashable; use
    [`with_protocol`][xnano_image.TerminalGraphics.with_protocol] to
    get a copy with another protocol.

    Maps to [`ratatui_image::picker::Picker`](https://docs.rs/ratatui-image/11.1.0/ratatui_image/picker/struct.Picker.html).

    Attributes:
        protocol: The graphics protocol images are drawn with.
        cell_size_in_pixels: The size of one terminal cell in pixels, ``(width, height)``.
        capabilities: The capabilities the terminal reported when it was detected.

    Examples:
        ```python
        graphics = TerminalGraphics.detect()  # before the full-screen session starts
        grid = TerminalImage.open('photo.png').to_cell_grid(40, 20, graphics=graphics)
        ```
    """
    # Rust binding
    def __repr__(self) -> str: ...
    # Rust binding
    @staticmethod
    def half_blocks() -> TerminalGraphics:
        """
        Capabilities that draw with half-block characters, which work in every terminal.

        The cell size is assumed to be ``(10, 20)`` pixels.
        """
    # Rust binding
    @staticmethod
    def detect() -> TerminalGraphics:
        """
        Ask the terminal which graphics protocol and cell size it supports.

        The query writes escape sequences to the terminal and reads its answer
        from standard input, waiting up to two seconds. Call it once, before
        starting a full-screen session and before reading terminal events. A
        terminal that does not answer is treated as supporting half-blocks
        only.

        Returns:
            The detected capabilities.

        Raises:
            TerminalQueryError: If standard input or output is not a
                terminal, or the query cannot be written or read. Use
                [`from_capabilities`][xnano_image.TerminalGraphics.from_capabilities]
                or [`half_blocks`][xnano_image.TerminalGraphics.half_blocks]
                in that case.
        """
    # Rust binding
    @staticmethod
    def from_capabilities(
        *,
        protocol: Literal['half_blocks', 'sixel', 'kitty', 'iterm2'],
        cell_size_in_pixels: tuple[int, int],
    ) -> TerminalGraphics:
        """
        Capabilities you already know, without querying the terminal.

        Use it when the terminal was queried elsewhere (for example by
        ``xnano.input.detect_terminal_capabilities()``) or when a
        protocol must be forced.

        Args:
            protocol: The graphics protocol to draw with.
            cell_size_in_pixels: The size of one terminal cell, ``(width, height)``,
                each side between 1 and 1000 pixels.

        Raises:
            TerminalImageError: If ``protocol`` is not one of the four protocols or
                a side of ``cell_size_in_pixels`` is out of range.
        """
    # Rust binding
    @property
    def protocol(self) -> Literal['half_blocks', 'sixel', 'kitty', 'iterm2']:
        """The graphics protocol images are drawn with."""
    # Rust binding
    def with_protocol(
        self, protocol: Literal['half_blocks', 'sixel', 'kitty', 'iterm2']
    ) -> TerminalGraphics:
        """
        A copy of these capabilities that draws with ``protocol``.

        Raises:
            TerminalImageError: If ``protocol`` is not one of the four protocols.
        """
    # Rust binding
    @property
    def cell_size_in_pixels(self) -> tuple[int, int]:
        """The size of one terminal cell in pixels, ``(width, height)``."""
    # Rust binding
    @property
    def capabilities(self) -> list[str]:
        """
        The capabilities the terminal reported when it was detected.

        Each is one of ``kitty``, ``sixel``, ``rectangular_operations``,
        ``kitty_compression``, ``cell_size``, ``text_sizing_protocol`` or
        ``background_color``. Empty unless built by
        [`detect`][xnano_image.TerminalGraphics.detect].
        """
    # Rust binding
    def __eq__(self, other: object) -> bool: ...
    # Rust binding
    def __hash__(self) -> int: ...
    # Rust binding
    def __copy__(self) -> TerminalGraphics: ...
    # Rust binding
    def __deepcopy__(self, memo: object) -> TerminalGraphics: ...

# Rust binding
@final
class TerminalImage:
    """
    A decoded, immutable image or animation.

    Every operation returns a new image, so one instance can be shared and
    reused freely, including across threads. Frames are stored as straight
    RGBA. ``len(image)`` is the frame count.

    Attributes:
        width: Width in pixels.
        height: Height in pixels.
        frame_count: Number of frames (1 for a still image).
        duration_milliseconds: Total playback time of every frame, in milliseconds.
        is_animated: Whether there is more than one frame.
        is_opaque: Whether no pixel is transparent.

    Examples:
        ```python
        image = TerminalImage.open('photo.png').resize(80, 60)
        print(image.to_ansi(40))
        ```
    """
    # Rust binding
    def __repr__(self) -> str: ...
    # Rust binding
    @staticmethod
    def open(path: str | os.PathLike[str]) -> TerminalImage:
        """
        Load an image from a file (PNG, JPEG, GIF, WebP or XNI1).

        Raises:
            OSError: If the file cannot be read.
            TerminalImageError: If the data cannot be decoded.
        """
    # Rust binding
    @staticmethod
    def from_bytes(data: bytes) -> TerminalImage:
        """
        Decode PNG, JPEG, GIF, WebP or XNI1 bytes; the format is detected.

        Animated GIF and WebP keep every frame, composited onto the full
        canvas, with their display times. A zero delay means 100 milliseconds
        and no frame is shorter than 10 milliseconds.

        Raises:
            TerminalImageError: If the format is unrecognized or the data is
                corrupt or too large (sides over 16384 pixels, over 1 GiB of
                pixels in total, an animated GIF or WebP canvas over 67
                megapixels, or over 10000 frames).
        """
    # Rust binding
    @staticmethod
    def from_rgba(
        width: int, height: int, pixels: bytes, *, duration_milliseconds: int = 100
    ) -> TerminalImage:
        """
        A single-frame image from ``width * height * 4`` straight RGBA bytes.

        Args:
            width: Width in pixels, 1 to 16384.
            height: Height in pixels, 1 to 16384.
            pixels: Row-major RGBA bytes.
            duration_milliseconds: How long the frame is shown when it becomes
                part of an animation.

        Raises:
            TerminalImageError: If the size is out of range or ``pixels`` has the
                wrong length.
        """
    # Rust binding
    @staticmethod
    def from_frames(frames: list[TerminalImage]) -> TerminalImage:
        """
        An animation from images that all share one size.

        Each image contributes all of its frames, in order, keeping its own
        frame durations (use
        [`with_frames_per_second`][xnano_image.TerminalImage.with_frames_per_second]
        to even them out).

        Raises:
            TerminalImageError: If the list is empty, the sizes differ, or the
                result would hold more than 1 GiB of pixels.
        """
    # Rust binding
    @staticmethod
    def from_xni(data: bytes) -> TerminalImage:
        """
        Decode the compact ``XNI1`` container written by
        [`to_xni`][xnano_image.TerminalImage.to_xni].

        Raises:
            TerminalImageError: If the data is truncated or corrupt.
        """
    # Rust binding
    @property
    def width(self) -> int:
        """Width in pixels."""
    # Rust binding
    @property
    def height(self) -> int:
        """Height in pixels."""
    # Rust binding
    @property
    def frame_count(self) -> int:
        """Number of frames (1 for a still image)."""
    # Rust binding
    @property
    def duration_milliseconds(self) -> int:
        """Total playback time of every frame, in milliseconds."""
    # Rust binding
    @property
    def is_animated(self) -> bool:
        """Whether there is more than one frame."""
    # Rust binding
    @property
    def is_opaque(self) -> bool:
        """Whether no pixel is transparent."""
    # Rust binding
    def frame_durations(self) -> list[int]:
        """Each frame's display time in milliseconds, in playback order."""
    # Rust binding
    def frame_index_at(
        self, elapsed_milliseconds: float, *, should_loop: bool = True
    ) -> int:
        """
        Index of the frame showing ``elapsed_milliseconds`` into playback.

        Negative times show the first frame.

        Args:
            elapsed_milliseconds: Time since playback started.
            should_loop: Start over after the last frame; otherwise hold the
                last frame.

        Raises:
            TerminalImageError: If ``elapsed_milliseconds`` is NaN or infinite.
        """
    # Rust binding
    def to_rgba(self, frame_index: int = 0) -> bytes:
        """
        Raw straight RGBA bytes of one frame, row-major.

        Raises:
            TerminalImageError: If ``frame_index`` is out of range.
        """
    # Rust binding
    def resize(
        self,
        width: int,
        height: int,
        *,
        resampling_filter: Literal[
            'nearest', 'bilinear', 'catmull_rom', 'lanczos3'
        ] = 'lanczos3',
    ) -> TerminalImage:
        """
        Resize to exactly ``width`` x ``height`` pixels.

        Uses SIMD resampling that keeps transparent edges free of dark halos.

        Args:
            width: Width in pixels, 1 to 16384.
            height: Height in pixels, 1 to 16384.
            resampling_filter: ``nearest`` keeps hard pixel edges; ``bilinear``,
                ``catmull_rom`` and ``lanczos3`` are progressively sharper and
                slower.

        Raises:
            TerminalImageError: If a side is out of range or the filter is unknown.
        """
    # Rust binding
    def scale(
        self,
        factor: float,
        *,
        resampling_filter: Literal[
            'nearest', 'bilinear', 'catmull_rom', 'lanczos3'
        ] = 'lanczos3',
    ) -> TerminalImage:
        """
        Scale both sides by ``factor`` (``2.0`` doubles them).

        Raises:
            TerminalImageError: If ``factor`` is not a finite number greater than
                zero, or the result would exceed 16384 pixels per side.
        """
    # Rust binding
    def crop(self, left: int, top: int, width: int, height: int) -> TerminalImage:
        """
        Cut out a rectangle of pixels.

        Raises:
            TerminalImageError: If the rectangle is empty or does not fit inside
                the image.
        """
    # Rust binding
    def fit_to_canvas(
        self,
        width: int,
        height: int,
        *,
        background: tuple[int, int, int] = (0, 0, 0),
        left: int | None = None,
        top: int | None = None,
    ) -> TerminalImage:
        """
        Place the image on a ``width`` x ``height`` canvas without resizing it.

        Smaller images are centered and padded with ``background``; larger
        ones are cropped around the center.

        Args:
            width: Canvas width in pixels, 1 to 16384.
            height: Canvas height in pixels, 1 to 16384.
            background: RGB color of the padding.
            left: Left edge of the kept window within a wider image. Centered
                when ``None``.
            top: Top edge of the kept window within a taller image. Centered
                when ``None``.
        """
    # Rust binding
    def focal_crop(
        self,
        width: int,
        height: int,
        *,
        scale: float = 1.0,
        left: int | None = None,
        top: int | None = None,
        background: tuple[int, int, int] = (0, 0, 0),
        resampling_filter: Literal[
            'nearest', 'bilinear', 'catmull_rom', 'lanczos3'
        ] = 'lanczos3',
    ) -> TerminalImage:
        """
        Scale by ``scale``, then keep an exact window, padding where needed.

        Zooms in on the subject, then keeps a fixed-size rectangle at the
        scaled resolution.

        Args:
            width: Width of the window in pixels.
            height: Height of the window in pixels.
            scale: Scale factor applied before cropping.
            left: Left edge of the window in the scaled image. Centered when
                ``None``.
            top: Top edge of the window in the scaled image. Centered when
                ``None``.
            background: RGB color used to flatten transparency and to pad when
                the window extends past the image.
            resampling_filter: Resampling filter, as in
                [`resize`][xnano_image.TerminalImage.resize].
        """
    # Rust binding
    def flatten(self, background: tuple[int, int, int] = (0, 0, 0)) -> TerminalImage:
        """Composite onto a solid RGB color so no pixel is transparent."""
    # Rust binding
    def quantize(self, colors: int = 64, *, should_dither: bool = False) -> TerminalImage:
        """
        Reduce every frame to an adaptive palette of at most ``colors`` colors.

        Transparency is flattened onto black first.

        Args:
            colors: 2 to 256. Fewer colors compress better (see
                [`to_xni`][xnano_image.TerminalImage.to_xni]) at the cost of
                fidelity.
            should_dither: Apply Floyd-Steinberg dithering.

        Raises:
            TerminalImageError: If ``colors`` is out of range.
        """
    # Rust binding
    def first_frames(self, count: int) -> TerminalImage:
        """
        Keep only the first ``count`` frames.

        Raises:
            TerminalImageError: If ``count`` is 0.
        """
    # Rust binding
    def still_frame(self, frame_index: int) -> TerminalImage:
        """
        Keep one frame as a still image.

        Raises:
            TerminalImageError: If ``frame_index`` is out of range.
        """
    # Rust binding
    def with_frames_per_second(self, frames_per_second: float) -> TerminalImage:
        """
        Give every frame an even cadence of ``frames_per_second``.

        Raises:
            TerminalImageError: If ``frames_per_second`` is not a finite number
                greater than zero.
        """
    # Rust binding
    def with_speed(self, factor: float) -> TerminalImage:
        """
        Play ``factor`` times faster (``2.0`` is twice as fast).

        No frame becomes shorter than 10 milliseconds.

        Raises:
            TerminalImageError: If ``factor`` is not a finite number greater than
                zero.
        """
    # Rust binding
    def to_cell_grid(
        self,
        columns: int | None = None,
        rows: int | None = None,
        *,
        fit: Literal['crop', 'contain', 'cover', 'stretch', 'smart'] = 'contain',
        horizontal_pixels_per_cell: int = 1,
        should_correct_aspect_ratio: bool = False,
        background: tuple[int, int, int] = (0, 0, 0),
        resampling_filter: Literal[
            'nearest', 'bilinear', 'catmull_rom', 'lanczos3'
        ] = 'lanczos3',
        frame_index: int = 0,
        graphics: TerminalGraphics | None = None,
    ) -> bytes:
        """
        Convert one frame to a cell grid (``XCG1`` bytes).

        With neither ``columns`` nor ``rows`` the image keeps its native pixel
        size (two pixel rows per cell). Give one to derive the other from the
        aspect ratio, or both to fit inside that box.

        Args:
            columns: Width in terminal cells, 1 to 1000.
            rows: Height in terminal cells, 1 to 1000.
            fit: How the image is placed in a ``columns`` x ``rows`` box.
                ``crop`` never resizes (center, crop or pad), ``contain``
                fits entirely inside, ``cover`` fills and crops the overflow,
                ``stretch`` fills exactly, and ``smart`` is ``cover`` when
                the aspect ratios nearly match and ``contain`` otherwise.
            horizontal_pixels_per_cell: 1 (lossless width) or 2 (sample two
                pixels across each cell).
            should_correct_aspect_ratio: With 2 pixels per cell the pixels are
                half as wide as tall; this widens the picture so proportions
                stay true.
            background: RGB color behind transparency and padding.
            resampling_filter: Resampling filter, as in
                [`resize`][xnano_image.TerminalImage.resize].
            frame_index: Which frame to convert.
            graphics: Capabilities whose protocol is ``sixel``, ``kitty`` or
                ``iterm2`` draw with that protocol instead of half-blocks.

        Raises:
            TerminalImageError: If an option is invalid, ``frame_index`` is out of
                range, or the grid would hold more than 4000000 cells (an
                unsized conversion of a very large image; pass ``columns`` or
                ``rows``).
        """
    # Rust binding
    def to_cell_grids(
        self,
        columns: int | None = None,
        rows: int | None = None,
        *,
        fit: Literal['crop', 'contain', 'cover', 'stretch', 'smart'] = 'contain',
        horizontal_pixels_per_cell: int = 1,
        should_correct_aspect_ratio: bool = False,
        background: tuple[int, int, int] = (0, 0, 0),
        resampling_filter: Literal[
            'nearest', 'bilinear', 'catmull_rom', 'lanczos3'
        ] = 'lanczos3',
        graphics: TerminalGraphics | None = None,
    ) -> list[bytes]:
        """
        Convert every frame to its own cell grid (``XCG1`` bytes).

        Takes the same arguments as
        [`to_cell_grid`][xnano_image.TerminalImage.to_cell_grid], except
        ``frame_index``. Pair the result with
        [`frame_durations`][xnano_image.TerminalImage.frame_durations], or use
        [`to_cell_animation`][xnano_image.TerminalImage.to_cell_animation] to
        get frames and timing in one value.

        Raises:
            TerminalImageError: If an option is invalid or a grid would hold more
                than 4000000 cells.
        """
    # Rust binding
    def to_cell_animation(
        self,
        columns: int | None = None,
        rows: int | None = None,
        *,
        should_loop: bool = True,
        fit: Literal['crop', 'contain', 'cover', 'stretch', 'smart'] = 'contain',
        horizontal_pixels_per_cell: int = 1,
        should_correct_aspect_ratio: bool = False,
        background: tuple[int, int, int] = (0, 0, 0),
        resampling_filter: Literal[
            'nearest', 'bilinear', 'catmull_rom', 'lanczos3'
        ] = 'lanczos3',
        graphics: TerminalGraphics | None = None,
    ) -> bytes:
        """
        Convert every frame, with its display time, to a cell animation (``XCA1`` bytes).

        Takes the same arguments as
        [`to_cell_grid`][xnano_image.TerminalImage.to_cell_grid], except
        ``frame_index``. A still image becomes a one-frame animation.

        With the ``kitty`` protocol every frame reuses one image id, so the
        terminal replaces the image in place instead of storing a new one per
        frame; each frame still carries its full pixel data. ``sixel`` and
        ``iterm2`` frames carry their full image data every frame.

        Args:
            should_loop: Start over after the last frame; otherwise hold the
                last frame.

        Raises:
            TerminalImageError: If an option is invalid, or the animation would
                hold more than 100000 frames or 64000000 cells in total. Pass
                smaller ``columns`` or ``rows``, or keep fewer frames with
                [`first_frames`][xnano_image.TerminalImage.first_frames].
        """
    # Rust binding
    def to_ansi(
        self,
        columns: int | None = None,
        rows: int | None = None,
        *,
        fit: Literal['crop', 'contain', 'cover', 'stretch', 'smart'] = 'contain',
        horizontal_pixels_per_cell: int = 1,
        should_correct_aspect_ratio: bool = False,
        background: tuple[int, int, int] = (0, 0, 0),
        resampling_filter: Literal[
            'nearest', 'bilinear', 'catmull_rom', 'lanczos3'
        ] = 'lanczos3',
        frame_index: int = 0,
    ) -> str:
        """
        One frame as half-block ANSI text, ready to ``print``.

        Takes the same arguments as
        [`to_cell_grid`][xnano_image.TerminalImage.to_cell_grid], except
        ``graphics``. Every line ends with a style reset.
        """
    # Rust binding
    def encode(self, image_format: Literal['png', 'gif'] = 'png') -> bytes:
        """
        Encode as ``png`` (the first frame) or ``gif`` (every frame, looping).

        Raises:
            TerminalImageError: If ``image_format`` is not ``png`` or ``gif``.
        """
    # Rust binding
    def save(self, path: str | os.PathLike[str]) -> None:
        """
        Write to ``path``; the extension (``.png`` or ``.gif``) picks the format.

        Raises:
            TerminalImageError: If the extension is not ``.png`` or ``.gif``.
            OSError: If the file cannot be written.
        """
    # Rust binding
    def to_xni(self, colors: int = 64) -> bytes:
        """
        Encode as the compact ``XNI1`` container, quantized to ``colors``.

        Raises:
            TerminalImageError: If ``colors`` is not between 2 and 256, or there
                are more than 65535 frames.
        """
    # Rust binding
    def __len__(self) -> int: ...
    # Rust binding
    def __eq__(self, other: object) -> bool: ...
    # Rust binding
    def __hash__(self) -> int: ...
    # Rust binding
    def __copy__(self) -> TerminalImage: ...
    # Rust binding
    def __deepcopy__(self, memo: object) -> TerminalImage: ...

# Rust binding
def cell_grid_size(cell_grid: bytes) -> tuple[int, int]:
    """
    Size ``(columns, rows)`` of a cell grid.

    The whole grid is validated, not only its header.

    Raises:
        TerminalImageError: If ``cell_grid`` is not a valid cell grid.
    """

# Rust binding
def cell_grid_to_text(cell_grid: bytes) -> list[str]:
    """
    The symbols of a cell grid, one string per row, trailing spaces trimmed.

    The text never contains escape sequences: cells drawn by a graphics
    protocol appear as spaces.

    Raises:
        TerminalImageError: If ``cell_grid`` is not a valid cell grid.
    """

# Rust binding
def cell_grid_to_ansi(cell_grid: bytes) -> str:
    """
    A cell grid as ANSI text, one line per row, ready to ``print``.

    Raises:
        TerminalImageError: If ``cell_grid`` is not a valid cell grid.
    """

__all__ = (
    'TerminalGraphics',
    'TerminalImage',
    'TerminalImageError',
    'TerminalQueryError',
    'cell_grid_size',
    'cell_grid_to_ansi',
    'cell_grid_to_text',
)
