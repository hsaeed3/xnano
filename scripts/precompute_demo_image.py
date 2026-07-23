"""scripts.precompute_demo_image

---

Build a compact XNI1 animation for the dependency-free ``xnano`` demo.
"""

from __future__ import annotations

import argparse
import pathlib
import struct
import zlib

from PIL import Image as pillow_image
from PIL import (
    ImageSequence as pillow_image_sequence,
)


def _get_native_crop(
    image: pillow_image.Image,
    width: int,
    height: int,
    source_scale: float,
    crop_left: int | None,
    crop_top: int | None,
) -> pillow_image.Image:
    """Return a focal native-resolution crop with black padding.

    Args:
        image: Source RGB image.
        width: Output pixel width.
        height: Output pixel height.
        source_scale: Scale applied before taking the native crop.
        crop_left: Optional source crop left edge; ``None`` centers it.
        crop_top: Optional source crop top edge; ``None`` centers it.

    Returns:
        Centered RGB crop at exactly ``width`` by ``height``.
    """
    if source_scale <= 0:
        raise ValueError("Source scale must be greater than zero.")
    if source_scale != 1.0:
        image = image.resize(
            (
                max(1, round(image.width * source_scale)),
                max(1, round(image.height * source_scale)),
            ),
            pillow_image.Resampling.LANCZOS,
        )
    output = pillow_image.new("RGB", (width, height), (0, 0, 0))
    centered_left = (image.width - width) // 2
    centered_top = (image.height - height) // 2
    source_left = max(
        0,
        min(
            image.width - width,
            centered_left if crop_left is None else crop_left,
        ),
    )
    source_top = max(
        0,
        min(
            image.height - height,
            centered_top if crop_top is None else crop_top,
        ),
    )
    output_left = max(0, (width - image.width) // 2)
    output_top = max(0, (height - image.height) // 2)
    copy_width = min(image.width, width)
    copy_height = min(image.height, height)
    crop = image.crop(
        (
            source_left,
            source_top,
            source_left + copy_width,
            source_top + copy_height,
        )
    )
    output.paste(crop, (output_left, output_top))
    return output


def _encode_frame(
    image: pillow_image.Image,
    duration_ms: int,
    color_count: int,
) -> bytes:
    """Quantize and compress one RGB frame.

    Args:
        image: Source RGB frame.
        duration_ms: Frame display duration.
        color_count: Maximum adaptive palette size.

    Returns:
        Encoded XNI1 frame record.
    """
    quantized = image.quantize(colors=color_count)
    indexes = quantized.tobytes()
    used_color_count = max(indexes) + 1
    palette_values = quantized.getpalette()
    if palette_values is None:
        raise ValueError("Quantized image did not produce a palette.")
    palette = bytes(palette_values[: used_color_count * 3])
    compressed = zlib.compress(indexes, level=9)
    return b"".join(
        (
            struct.pack(
                ">HHI", duration_ms, used_color_count, len(compressed)
            ),
            palette,
            compressed,
        )
    )


def precompute_image(
    source: pathlib.Path,
    destination: pathlib.Path,
    *,
    width: int,
    height: int,
    color_count: int,
    source_scale: float,
    crop_left: int | None,
    crop_top: int | None,
    frame_count: int | None,
    frames_per_second: int | None,
) -> None:
    """Write a centered, palette-compressed XNI1 animation.

    Args:
        source: Input animated image path.
        destination: Output XNI1 path.
        width: Stored native pixel width.
        height: Stored native pixel height.
        color_count: Per-frame adaptive palette limit.
        source_scale: Scale applied before taking the native crop.
        crop_left: Optional source crop left edge.
        crop_top: Optional source crop top edge.
        frame_count: Optional maximum number of source frames.
        frames_per_second: Optional output cadence overriding source timing.
    """
    if frames_per_second is not None and frames_per_second <= 0:
        raise ValueError("Frames per second must be greater than zero.")
    records: list[bytes] = []
    with pillow_image.open(source) as image:
        fallback_duration = max(10, int(image.info.get("duration", 100)))
        for frame_index, source_frame in enumerate(
            pillow_image_sequence.Iterator(image)
        ):
            if frame_count is not None and frame_index >= frame_count:
                break
            if frames_per_second is None:
                duration_ms = max(
                    10,
                    int(
                        source_frame.info.get(
                            "duration",
                            fallback_duration,
                        )
                    ),
                )
            else:
                frame_start_ms = round(frame_index * 1000 / frames_per_second)
                frame_end_ms = round(
                    (frame_index + 1) * 1000 / frames_per_second
                )
                duration_ms = frame_end_ms - frame_start_ms
            frame = _get_native_crop(
                source_frame.convert("RGB"),
                width,
                height,
                source_scale,
                crop_left,
                crop_top,
            )
            records.append(_encode_frame(frame, duration_ms, color_count))

    payload = b"".join(
        (
            b"XNI1",
            struct.pack(">HHH", width, height, len(records)),
            *records,
        )
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    print(
        f"{source}: {len(records)} frames, {width}x{height}, "
        f"{color_count} colors -> {destination} "
        f"({len(payload) / 1024:.1f} KiB)"
    )


def run_precompute() -> None:
    """Parse command-line arguments and generate an XNI1 payload."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("destination", type=pathlib.Path)
    parser.add_argument("--width", type=int, default=120)
    parser.add_argument("--height", type=int, default=80)
    parser.add_argument("--colors", type=int, default=64)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--left", type=int)
    parser.add_argument("--top", type=int)
    parser.add_argument("--frames", type=int)
    parser.add_argument("--fps", type=int)
    arguments = parser.parse_args()
    precompute_image(
        arguments.source,
        arguments.destination,
        width=arguments.width,
        height=arguments.height,
        color_count=arguments.colors,
        source_scale=arguments.scale,
        crop_left=arguments.left,
        crop_top=arguments.top,
        frame_count=arguments.frames,
        frames_per_second=arguments.fps,
    )


if __name__ == "__main__":
    run_precompute()
