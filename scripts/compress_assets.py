#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "Pillow",
# ]
# ///
"""Compress all PNG and GIF assets in the repository in-place.

PNGs are losslessly re-saved via Pillow (optimize + max deflate).
GIFs are compressed with gifsicle (``brew install gifsicle``).

Usage
-----
::

    uv run scripts/compress_assets.py
    uv run scripts/compress_assets.py --dry-run
    uv run scripts/compress_assets.py --no-gif   # skip GIFs if gifsicle missing
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image  # ty: ignore[unresolved-import]

REPO_ROOT = Path(__file__).resolve().parents[1]


def compress_png(path: Path, dry_run: bool) -> tuple[int, int]:
    original_size = path.stat().st_size
    if dry_run:
        return original_size, original_size

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with Image.open(path) as image:
            image.save(tmp_path, format="PNG", optimize=True, compress_level=9)
        new_size = tmp_path.stat().st_size
        if new_size < original_size:
            shutil.move(str(tmp_path), str(path))
        else:
            tmp_path.unlink(missing_ok=True)
            new_size = original_size
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    return original_size, new_size


def compress_gif(path: Path, dry_run: bool) -> tuple[int, int]:
    original_size = path.stat().st_size
    if dry_run:
        return original_size, original_size

    with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        result = subprocess.run(
            [
                "gifsicle",
                "--optimize=3",
                "--lossy=80",
                "--output",
                str(tmp_path),
                str(path),
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            tmp_path.unlink(missing_ok=True)
            return original_size, original_size

        new_size = tmp_path.stat().st_size
        if new_size < original_size:
            shutil.move(str(tmp_path), str(path))
        else:
            tmp_path.unlink(missing_ok=True)
            new_size = original_size
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    return original_size, new_size


def format_size(bytes_count: int) -> str:
    if bytes_count >= 1_048_576:
        return f"{bytes_count / 1_048_576:.1f} MB"
    if bytes_count >= 1024:
        return f"{bytes_count / 1024:.1f} KB"
    return f"{bytes_count} B"


def format_delta(original: int, compressed: int) -> str:
    if original == 0:
        return "0%"
    saved = original - compressed
    pct = saved / original * 100
    return f"-{pct:.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compress PNG/GIF assets in-place."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="report sizes without writing"
    )
    parser.add_argument(
        "--no-gif", action="store_true", help="skip GIF compression"
    )
    parser.add_argument(
        "--no-png", action="store_true", help="skip PNG compression"
    )
    args = parser.parse_args()

    has_gifsicle = shutil.which("gifsicle") is not None
    if not args.no_gif and not has_gifsicle:
        print(
            "warning: gifsicle not found — skipping GIFs (brew install gifsicle)",
            file=sys.stderr,
        )
        args.no_gif = True

    pngs = sorted(REPO_ROOT.rglob("*.png")) if not args.no_png else []
    gifs = sorted(REPO_ROOT.rglob("*.gif")) if not args.no_gif else []

    total_original = 0
    total_compressed = 0
    errors: list[tuple[Path, str]] = []

    label = "[dry-run] " if args.dry_run else ""

    for path in pngs:
        try:
            original, compressed = compress_png(path, args.dry_run)
            total_original += original
            total_compressed += compressed
            delta = format_delta(original, compressed)
            relative = path.relative_to(REPO_ROOT)
            print(
                f"{label}png  {relative}  {format_size(original)} → {format_size(compressed)}  ({delta})"
            )
        except Exception as exc:
            errors.append((path, str(exc)))
            print(
                f"error  {path.relative_to(REPO_ROOT)}  {exc}", file=sys.stderr
            )

    for path in gifs:
        try:
            original, compressed = compress_gif(path, args.dry_run)
            total_original += original
            total_compressed += compressed
            delta = format_delta(original, compressed)
            relative = path.relative_to(REPO_ROOT)
            print(
                f"{label}gif  {relative}  {format_size(original)} → {format_size(compressed)}  ({delta})"
            )
        except Exception as exc:
            errors.append((path, str(exc)))
            print(
                f"error  {path.relative_to(REPO_ROOT)}  {exc}", file=sys.stderr
            )

    total_saved = total_original - total_compressed
    print()
    print(
        f"total  {format_size(total_original)} → {format_size(total_compressed)}"
        f"  saved {format_size(total_saved)} ({format_delta(total_original, total_compressed)})"
    )

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
