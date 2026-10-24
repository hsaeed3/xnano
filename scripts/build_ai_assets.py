"""
scripts.build_ai_assets

Build the libraries of examples that `xnano.ai.assets` installs, from the sources in
`scripts/ai_assets/<name>.jsonl`, after checking every entry.

    uv run python scripts/build_ai_assets.py           # build and print the catalog values
    uv run python scripts/build_ai_assets.py --update  # also write them into xnano/ai/assets.py

The archives land in `dist/ai-assets/`. They are byte-for-byte reproducible, so the checksums in
the catalog stay valid until a source changes. Publish them as the files of the GitHub release
`ai-assets-<version>`, the address the catalog downloads from.

- Art: every row has the declared width, every letter is in the palette, every palette letter
  is used, the roles and colours are valid, and `xnano.draw` builds it.
- Melodies: `xnano.audio.Melody` parses the text, and each bar holds the beats of the meter.
- Components: the program runs as `ComponentModel` runs one, on a canvas of the declared size,
  drawing something and nothing past the edges; what it draws is saved beside it as `output`.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
import sys
import tarfile
from collections.abc import Callable
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parent.parent
SOURCES = REPOSITORY / "scripts" / "ai_assets"
OUTPUT = REPOSITORY / "dist" / "ai-assets"
CATALOG = REPOSITORY / "xnano" / "ai" / "assets" / "__init__.py"

ROLES = {"outline", "base", "shadow", "highlight", "accent", "skin", "detail"}
MOST_COLORS = {8: 5, 12: 7, 16: 10}


class EntryError(ValueError):
    """An entry of a source that breaks a rule, with where it is."""


def check_art(entry: dict[str, object], line: int) -> dict[str, object]:
    """Check a piece of reference art; return it unchanged."""
    import xnano

    width, height = entry["width"], entry["height"]
    rows = entry["rows"]
    palette = entry["palette"]
    assert isinstance(rows, list) and isinstance(palette, dict)
    if len(rows) != height:
        raise EntryError(f"line {line}: {len(rows)} rows, expected {height}")
    for index, row in enumerate(rows):
        if len(row) != width:
            raise EntryError(
                f"line {line}: row {index} has {len(row)} pixels, expected {width}"
            )
        unknown = set(row) - set(palette) - {"."}
        if unknown:
            raise EntryError(
                f"line {line}: row {index} uses {sorted(unknown)}, not in the palette"
            )
    used = set("".join(rows))
    for letter, color in palette.items():
        if len(letter) != 1 or not letter.islower():
            raise EntryError(
                f"line {line}: palette key {letter!r} is not one lowercase letter"
            )
        if letter not in used:
            raise EntryError(f"line {line}: palette letter {letter!r} is never used")
        if color.get("role") not in ROLES:
            raise EntryError(
                f"line {line}: {letter!r} has the role {color.get('role')!r}"
            )
        if not re.fullmatch(r"#[0-9a-f]{6}", str(color.get("color"))):
            raise EntryError(
                f"line {line}: {letter!r} has the colour {color.get('color')!r}"
            )
    most = MOST_COLORS.get(int(width), 10)  # type: ignore[call-overload]
    if len(palette) > most:
        raise EntryError(
            f"line {line}: {len(palette)} colours, at most {most} at this size"
        )
    if sum(1 for color in palette.values() if color["role"] == "outline") > 1:
        raise EntryError(f"line {line}: more than one outline colour")
    xnano.draw(rows, {letter: color["color"] for letter, color in palette.items()})
    return entry


def check_melody(entry: dict[str, object], line: int) -> dict[str, object]:
    """Check a melody's bars and parse; return it unchanged."""
    from xnano.audio import Melody

    text = str(entry["text"])
    meter = str(entry["meter"])
    beats_per_bar = {"4/4": 4.0, "3/4": 3.0, "2/4": 2.0}.get(meter)
    if beats_per_bar is None:
        raise EntryError(f"line {line}: the meter {meter!r} is not 4/4, 3/4 or 2/4")
    bars = [bar.split() for bar in text.split("|")]
    if len(bars) != entry["bars"]:
        raise EntryError(f"line {line}: {len(bars)} bars, expected {entry['bars']}")
    for index, bar in enumerate(bars):
        beats = 0.0
        for token in bar:
            _, _, length = token.rpartition(":") if ":" in token else ("", "", "1")
            beats += float(length)
        if abs(beats - beats_per_bar) > 1e-9:
            raise EntryError(
                f"line {line}: bar {index + 1} holds {beats:g} beats, not {beats_per_bar:g}"
            )
    melody = Melody(text, bpm=float(entry["bpm"]))  # type: ignore[arg-type]
    if melody.length_beats != beats_per_bar * len(bars):
        raise EntryError(f"line {line}: the melody lasts {melody.length_beats:g} beats")
    return entry


def check_component(entry: dict[str, object], line: int) -> dict[str, object]:
    """Run a component's program; return it with what it draws as ``output``."""
    from xnano.ai.models.components import _run_component

    width, height = int(entry["width"]), int(entry["height"])  # type: ignore[call-overload]
    repairs: list[str] = []
    component, problems = _run_component(
        str(entry["request"]), str(entry["program"]), width, height, repairs
    )
    if problems or repairs:
        raise EntryError(f"line {line}: " + "; ".join(problems + repairs))
    return {**entry, "output": component.text}


CHECKS: dict[str, Callable[[dict[str, object], int], dict[str, object]]] = {
    "art-references": check_art,
    "component-examples": check_component,
    "melodies": check_melody,
}


def build(name: str, version: str) -> tuple[Path, int, str]:
    """Check the source of a library and write its archive; return its path, size and checksum."""
    source = SOURCES / f"{name}.jsonl"
    checked = []
    for line, text in enumerate(
        source.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if text.strip():
            checked.append(CHECKS[name](json.loads(text), line))
    entries = "".join(
        json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
        for entry in checked
    )
    description = json.dumps(
        {"name": name, "version": version, "entries": len(checked)}, sort_keys=True
    )
    files = {
        "asset.json": description.encode() + b"\n",
        "entries.jsonl": entries.encode(),
    }
    archive = io.BytesIO()
    # Fixed times, owners and order, so the same sources always give the same bytes.
    with gzip.GzipFile(fileobj=archive, mode="wb", mtime=0) as compressed:
        with tarfile.open(
            fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT
        ) as bundle:
            for file_name in sorted(files):
                data = files[file_name]
                information = tarfile.TarInfo(file_name)
                information.size = len(data)
                information.mtime = 0
                information.mode = 0o644
                bundle.addfile(information, io.BytesIO(data))
    data = archive.getvalue()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / f"{name}-{version}.tar.gz"
    target.write_bytes(data)
    sys.stdout.write(f"{name}: {len(checked)} entries\n")
    return target, len(data), hashlib.sha256(data).hexdigest()


def catalog_versions() -> dict[str, str]:
    """The version of each library in the catalog of xnano/ai/assets.py."""
    source = CATALOG.read_text(encoding="utf-8")
    return dict(
        re.findall(
            r"name='([a-z-]+)',\s+description=\(.*?\),\s+version='([0-9.]+)'",
            source,
            re.S,
        )
    )


def update_catalog(values: dict[str, tuple[int, str]]) -> None:
    """Write the sizes and checksums of the archives into the catalog."""
    source = CATALOG.read_text(encoding="utf-8")
    for name, (size, checksum) in values.items():
        pattern = re.compile(
            rf"(name='{re.escape(name)}',.*?size_bytes=)\d+(,\s+sha256=')[0-9a-f]+(')",
            re.S,
        )
        source, count = pattern.subn(
            rf"\g<1>{size}\g<2>{checksum}\g<3>", source, count=1
        )
        if count != 1:
            raise SystemExit(f"The catalog has no entry for {name}.")
    CATALOG.write_text(source, encoding="utf-8")


def main() -> None:
    """Build every library of the catalog, and update the catalog with ``--update``."""
    values = {}
    for name, version in catalog_versions().items():
        target, size, checksum = build(name, version)
        values[name] = (size, checksum)
        sys.stdout.write(
            f"    {target.relative_to(REPOSITORY)}  size_bytes={size}  sha256={checksum}\n"
        )
    if "--update" in sys.argv[1:]:
        update_catalog(values)
        sys.stdout.write(f"Updated {CATALOG.relative_to(REPOSITORY)}\n")


if __name__ == "__main__":
    main()
