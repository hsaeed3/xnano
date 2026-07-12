"""run_xnano_spec.py — xnano-spec: a focused intent linter for humans & agents.

Usage:
    python scripts/run_xnano_spec.py check [path ...]

Scans Python source files for annotation blocks of the form:

    # [@<tag>]
    # Body line one — what needs to be done, fixed, or decided.
    # Body line two — continues until a non-comment line is hit.

All found blocks surface in an xnano TUI where you can navigate,
read context, and edit body text inline (writing changes back to source).
"""

from __future__ import annotations

import dataclasses
import re
import sys
from pathlib import Path
from typing import Iterator

# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"^\s*#\s*\[@([\w-]+)\]")
_COMMENT_RE = re.compile(r"^\s*#(.*)")


@dataclasses.dataclass
class SpecBlock:
    tag: str
    body: list[str]  # stripped comment text, one item per source line
    file: Path
    line: int  # 1-indexed line number of the [@tag] comment
    body_start: int  # 1-indexed first body line
    body_end: int  # 1-indexed exclusive end (body_start + len(body))

    @property
    def short_path(self) -> str:
        try:
            return str(self.file.relative_to(Path.cwd()))
        except ValueError:
            return str(self.file)

    @property
    def body_text(self) -> str:
        return "\n".join(self.body)


def _scan_file(path: Path) -> Iterator[SpecBlock]:
    try:
        source = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return
    i = 0
    while i < len(source):
        m = _TAG_RE.match(source[i])
        if m:
            tag = m.group(1)
            tag_line = i + 1  # 1-indexed
            j = i + 1
            body: list[str] = []
            while j < len(source):
                cm = _COMMENT_RE.match(source[j])
                if cm:
                    body.append(cm.group(1).strip())
                    j += 1
                else:
                    break
            yield SpecBlock(
                tag=tag,
                body=body,
                file=path,
                line=tag_line,
                body_start=tag_line + 1,
                body_end=tag_line + 1 + len(body),
            )
            i = j
        else:
            i += 1


def scan_paths(paths: list[Path]) -> list[SpecBlock]:
    blocks: list[SpecBlock] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            blocks.extend(_scan_file(path))
        elif path.is_dir():
            for py_file in sorted(path.rglob("*.py")):
                if any(p.startswith(".") for p in py_file.parts):
                    continue
                blocks.extend(_scan_file(py_file))
    return blocks


def save_block(block: SpecBlock, new_body: list[str]) -> None:
    """Overwrite the body comment lines in-place and update the block."""
    raw = block.file.read_text(encoding="utf-8").splitlines(keepends=True)
    tag_line = raw[block.line - 1]
    indent = len(tag_line) - len(tag_line.lstrip())
    prefix = tag_line[:indent]

    new_lines = [
        (f"{prefix}# {ln}\n" if ln.strip() else f"{prefix}#\n")
        for ln in new_body
    ]
    start = block.body_start - 1  # 0-indexed inclusive
    end = block.body_end - 1  # 0-indexed exclusive
    raw[start:end] = new_lines
    block.file.write_text("".join(raw), encoding="utf-8")
    block.body = list(new_body)
    block.body_end = block.body_start + len(new_body)


# ---------------------------------------------------------------------------
# TUI
# ---------------------------------------------------------------------------

from xnano.color import tailwind_color
from xnano.components.text import Text
from xnano.events import on_keyboard
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.tui import Terminal

_V300 = tailwind_color("violet", 300)
_V400 = tailwind_color("violet", 400)
_V500 = tailwind_color("violet", 500)
_V950 = tailwind_color("violet", 950)
_S200 = tailwind_color("slate", 200)
_S400 = tailwind_color("slate", 400)
_S500 = tailwind_color("slate", 500)
_S700 = tailwind_color("slate", 700)
_A300 = tailwind_color("amber", 300)
_A700 = tailwind_color("amber", 700)


def _render_list(blocks: list[SpecBlock], selected: int, height: int) -> Text:
    if not blocks:
        return Text("  no blocks found", color=_S500, modifiers=("italic",))

    half = max(1, height // 3)
    start = max(0, selected - half)
    end = min(len(blocks), start + height)
    start = max(0, end - height)

    parts: list[str | Text] = []
    for i in range(start, end):
        b = blocks[i]
        sel = i == selected
        bg = _V950 if sel else None
        prefix = " ❯ " if sel else "   "
        tag_c = _V300 if sel else _V500
        file_c = _S200 if sel else _S400
        parts.append(
            Text(
                [
                    Text(prefix, color=_V400, background=bg),
                    Text(
                        f"[@{b.tag}]",
                        color=tag_c,
                        modifiers=("bold",) if sel else (),
                        background=bg,
                    ),
                    Text("\n"),
                    Text("    ", background=bg),
                    Text(
                        f"{b.short_path}:{b.line}\n",
                        color=file_c,
                        background=bg,
                    ),
                ]
            )
        )
    return Text(parts)


def _render_detail(
    block: SpecBlock | None,
    edit_mode: bool,
    edit_text: str,
) -> Text:
    if block is None:
        return Text(
            "  select a block to view", color=_S500, modifiers=("italic",)
        )

    parts: list[str | Text] = [
        Text(f"[@{block.tag}]\n", color=_V300, modifiers=("bold",)),
        Text(f"{block.short_path}:{block.line}\n", color=_S400),
        Text("─" * 40 + "\n", color=_S700),
    ]
    if edit_mode:
        parts.append(Text(edit_text + "▋\n", color=_A300))
    elif block.body:
        parts.append(Text(block.body_text + "\n", color=_S200))
    else:
        parts.append(Text("  (empty)\n", color=_S500, modifiers=("italic",)))

    return Text(parts)


class SpecApp(BaseGrid, direction="horizontal", gap=1, background="black"):
    left: Text = Field(
        default=Text(""),
        width="30%",
        border="rounded",
        border_color=_S700,
        title=" xnano-spec  j/k: nav  e: edit  q: quit ",
        background="black",
    )
    right: Text = Field(
        default=Text(""),
        width="1fr",
        border="rounded",
        border_color=_S700,
        title=" Detail ",
        background="black",
    )

    blocks: list = Field(default_factory=list, state=True)
    selected: int = Field(default=0, state=True)
    edit_mode: bool = Field(default=False, state=True)
    edit_text: str = Field(default="", state=True)

    def grid_render(self) -> None:
        n = len(self.blocks)
        sel = self.selected
        current = self.blocks[sel] if self.blocks and 0 <= sel < n else None

        self.left = _render_list(self.blocks, sel, max(1, self.rows - 2))
        self.right = _render_detail(current, self.edit_mode, self.edit_text)

        pos = f"{sel + 1}/{n}" if n else "—"
        if self.edit_mode:
            left_title = f" [{pos}] EDIT MODE "
            right_title = " ctrl+s: save  esc: cancel "
            right_border = _A700
        else:
            left_title = f" [{pos}] j/k: nav  e: edit  q: quit "
            right_title = " Detail "
            right_border = _S700

        self.grid_set_field("left", title=left_title)
        self.grid_set_field(
            "right", title=right_title, border_color=right_border
        )

    @on_keyboard("up")
    def _up(self) -> None:
        if not self.edit_mode and self.blocks:
            self.selected = (self.selected - 1) % len(self.blocks)

    @on_keyboard("down")
    def _down(self) -> None:
        if not self.edit_mode and self.blocks:
            self.selected = (self.selected + 1) % len(self.blocks)

    @on_keyboard("escape")
    def _escape(self) -> None:
        if self.edit_mode:
            self.edit_mode = False
            self.edit_text = ""

    @on_keyboard("backspace")
    def _backspace(self) -> None:
        if self.edit_mode:
            self.edit_text = self.edit_text[:-1]

    @on_keyboard
    def _char(self, ctx) -> None:
        kbd = ctx.keyboard
        if kbd is None:
            return
        char = getattr(kbd, "character", None)
        if not char or len(char) != 1:
            return

        if not self.edit_mode:
            if char == "q":
                from xnano.core.exceptions import Exit

                raise Exit
            elif char == "j" and self.blocks:
                self.selected = (self.selected + 1) % len(self.blocks)
            elif char == "k" and self.blocks:
                self.selected = (self.selected - 1) % len(self.blocks)
            elif char == "e" and self.blocks:
                self.edit_text = self.blocks[self.selected].body_text
                self.edit_mode = True
            return

        if char == "\x13":  # ctrl+s
            self._save()
        elif char in ("\n", "\r"):
            self.edit_text = self.edit_text + "\n"
        elif char not in ("\x7f", "\x08", "\x1b"):
            self.edit_text = self.edit_text + char

    def _save(self) -> None:
        if not self.blocks:
            return
        block = self.blocks[self.selected]
        save_block(block, self.edit_text.splitlines())
        self.edit_mode = False
        self.edit_text = ""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _usage() -> None:
    print(
        "usage: python scripts/run_xnano_spec.py check [path ...]",
        file=sys.stderr,
    )
    sys.exit(1)


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] != "check":
        _usage()

    raw_paths = args[1:] or ["."]
    blocks = scan_paths([Path(p) for p in raw_paths])

    if not blocks:
        print("xnano-spec: no spec blocks found.")
        return

    app = SpecApp()
    app.blocks = blocks
    Terminal(tick_interval=30).run(app)


if __name__ == "__main__":
    main()
