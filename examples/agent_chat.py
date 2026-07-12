"""xnano example — agent_chat.py

Interactive agent CLI inspired by Claude Code, Codex, Copilot CLI, and
Cursor — conversational prompt, slash commands, tool-call blocks with live
output, and session status chrome.
"""

from __future__ import annotations

import textwrap
import time
from typing import Iterable, Iterator, Literal, TypeAlias

from xnano._types import CharacterModifier
from xnano.color import tailwind_color
from xnano.components.text import Text
from xnano.events import on_keyboard, on_mouse, on_tick
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.tui import Terminal


ToolKind: TypeAlias = Literal["read", "bash", "edit", "grep"]
"""Supported tool-call kinds shown in the transcript."""

_COMMANDS = [
    ("/help", "Show available commands"),
    ("/clear", "Clear conversation history"),
    ("/compact", "Compact conversation history"),
    ("/model", "Switch active model"),
    ("/status", "Show session status"),
    ("/copy", "Copy last response to clipboard"),
    ("/fork", "Branch session to a peer agent"),
]

_TOOL_LABELS = {
    "read": "◈ Read",
    "bash": "◈ Bash",
    "edit": "◈ Edit",
    "grep": "◈ Grep",
}

_TOOL_ACCENTS = {
    "read": tailwind_color("sky", 400),
    "bash": tailwind_color("emerald", 400),
    "edit": tailwind_color("violet", 400),
    "grep": tailwind_color("amber", 400),
}

_PULSE_COLORS = (
    tailwind_color("sky", 400),
    tailwind_color("violet", 500),
    tailwind_color("fuchsia", 400),
    tailwind_color("emerald", 400),
    tailwind_color("amber", 400),
)

_WELCOME = [
    {
        "type": "system",
        "text": "xnano agent v0.4.2 · session f8a21c · ~/projects/xnano",
    },
    {
        "type": "agent",
        "text": (
            "Ready. I can read files, run shell commands, and edit code. "
            "Type / for commands or describe what to build."
        ),
    },
]


def _color_hex(color) -> str:
    return f"#{color.r:02x}{color.g:02x}{color.b:02x}"


def _pulsing_color(tick: float, offset: int) -> str:
    phase = (tick * 1.4 + offset * 1.1) % len(_PULSE_COLORS)
    index = int(phase) % len(_PULSE_COLORS)
    blend = phase - int(phase)
    current = _PULSE_COLORS[index]
    nxt = _PULSE_COLORS[(index + 1) % len(_PULSE_COLORS)]
    red = int(current.r + (nxt.r - current.r) * blend)
    green = int(current.g + (nxt.g - current.g) * blend)
    blue = int(current.b + (nxt.b - current.b) * blend)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _tool_rail_color(
    status: str,
    tick: float,
    offset: int,
    tool_kind: str,
) -> str:
    if status == "active":
        return _pulsing_color(tick, offset)
    if status == "success":
        accent = _TOOL_ACCENTS.get(tool_kind, tailwind_color("emerald", 500))
        return _color_hex(accent)
    return _color_hex(tailwind_color("slate", 700))


def _stream_chunks(text: str) -> Iterator[str]:
    """Yield ``text`` word-by-word, simulating token-by-token output.

    This is only the default source for the canned demo responses — any
    other iterable of ``str`` chunks (a generator, a real streaming API's
    token iterator, ...) works equally well as input to ``_begin_stream``.
    """
    words = text.split(" ")
    for index, word in enumerate(words):
        yield word if index == len(words) - 1 else word + " "


def _wrap_body(text: str, width: int) -> list[str]:
    """Hard-wrap ``text`` to ``width`` columns, one entry per terminal row.

    Windowing/scrolling slices the rendered ``lines`` list by entry count, so
    each entry must correspond to exactly one rendered row — relying on the
    native widget's own word-wrap would make row count unknowable up front.
    """
    width = max(8, width)
    rows: list[str] = []
    for paragraph in text.split("\n"):
        rows.extend(textwrap.wrap(paragraph, width=width) or [""])
    return rows or [""]


def _wrapped_row(
    rows: list[str],
    index: int,
    *,
    rail: str,
    rail_color,
    lead: str,
    lead_color,
    lead_modifiers: tuple[CharacterModifier, ...],
    text_color,
    text_background=None,
) -> Text:
    """Build one prefixed, wrapped row — blank lead on continuation rows."""
    is_first = index == 0
    return Text(
        [
            Text(rail, color=rail_color),
            Text(
                lead if is_first else " " * len(lead),
                color=lead_color,
                modifiers=lead_modifiers if is_first else (),
            ),
            Text(
                rows[index] + "\n",
                color=text_color,
                background=text_background,
            ),
        ]
    )


def _build_message_lines(
    messages: list[dict], content_width: int
) -> list[str | Text]:
    lines: list[str | Text] = []
    for message in messages:
        kind = message.get("type", "")
        text = message.get("text", "")
        command = message.get("command", "")
        description = message.get("description", "")
        output = message.get("output", "")
        status = message.get("status", "")
        tool_kind = message.get("tool_kind", "bash")
        tick = message.get("_tick", 0.0)

        if kind == "user":
            rows = _wrap_body(text, content_width - 2)
            for index in range(len(rows)):
                lines.append(
                    _wrapped_row(
                        rows,
                        index,
                        rail="",
                        rail_color=None,
                        lead="❯ ",
                        lead_color=tailwind_color("sky", 400),
                        lead_modifiers=("bold",),
                        text_color=tailwind_color("slate", 100),
                    )
                )
            lines.append(Text("\n"))

        elif kind == "agent":
            rows = _wrap_body(text, content_width - 2)
            for index in range(len(rows)):
                lines.append(
                    _wrapped_row(
                        rows,
                        index,
                        rail="",
                        rail_color=None,
                        lead="◆ ",
                        lead_color=tailwind_color("emerald", 400),
                        lead_modifiers=("bold",),
                        text_color=tailwind_color("emerald", 100),
                    )
                )
            lines.append(Text("\n"))

        elif kind == "system":
            rows = _wrap_body(text, content_width - 2)
            for index in range(len(rows)):
                lines.append(
                    _wrapped_row(
                        rows,
                        index,
                        rail="",
                        rail_color=None,
                        lead="ℹ ",
                        lead_color=tailwind_color("slate", 500),
                        lead_modifiers=("italic",),
                        text_color=tailwind_color("slate", 500),
                    )
                )
            lines.append(Text("\n"))

        elif kind == "tool":
            label = _TOOL_LABELS.get(tool_kind, "◈ Tool")
            accent = _TOOL_ACCENTS.get(
                tool_kind, tailwind_color("violet", 400)
            )
            rail_1 = _tool_rail_color(status, tick, 0, tool_kind)
            rail_2 = _tool_rail_color(status, tick, 1, tool_kind)
            rail_3 = _tool_rail_color(status, tick, 2, tool_kind)

            command_rows = _wrap_body(command, content_width - len(label) - 4)
            for index in range(len(command_rows)):
                lines.append(
                    _wrapped_row(
                        command_rows,
                        index,
                        rail="┃ ",
                        rail_color=rail_1,
                        lead=label + "  " if index == 0 else "",
                        lead_color=accent,
                        lead_modifiers=("bold",),
                        text_color=tailwind_color("slate", 100),
                    )
                )

            if description:
                description_rows = _wrap_body(description, content_width - 4)
                for index in range(len(description_rows)):
                    lines.append(
                        _wrapped_row(
                            description_rows,
                            index,
                            rail="┃ ",
                            rail_color=rail_2,
                            lead="  ",
                            lead_color=None,
                            lead_modifiers=(),
                            text_color=tailwind_color("slate", 400),
                        )
                    )

            if output:
                output_bg = _color_hex(tailwind_color("slate", 900))
                output_rows = _wrap_body(output, content_width - 4)
                for index in range(len(output_rows)):
                    lines.append(
                        _wrapped_row(
                            output_rows,
                            index,
                            rail="┃ ",
                            rail_color=rail_3,
                            lead="  ",
                            lead_color=None,
                            lead_modifiers=(),
                            text_color=tailwind_color("slate", 300),
                            text_background=output_bg,
                        )
                    )
            lines.append(Text("\n"))

    return lines


def _windowed_history(
    lines: list[str | Text],
    height: int,
    scroll_offset: int,
) -> tuple[Text, int, bool]:
    """Slice ``lines`` to the visible window for ``scroll_offset``.

    ``scroll_offset`` counts entries up from the bottom (``0`` = pinned to
    the latest message). New messages append at the bottom without moving
    an existing scroll position, matching typical chat/log viewers.

    Returns:
        ``(text, clamped_offset, is_scrolled)`` — the rendered ``Text``, the
            offset clamped to the available history, and whether the view
            is scrolled away from the bottom.
    """
    if not lines:
        return Text(""), 0, False

    window = max(1, height)
    max_offset = max(0, len(lines) - window)
    clamped = max(0, min(scroll_offset, max_offset))
    end = len(lines) - clamped
    start = max(0, end - window)
    return Text(lines[start:end]), clamped, clamped > 0


def _render_autocomplete(
    matches: list[tuple[str, str]],
    selected: int,
) -> Text:
    parts: list[str | Text] = []
    for index, (command, description) in enumerate(matches):
        is_selected = index == selected
        prefix = " ❯ " if is_selected else "   "
        background = tailwind_color("violet", 950) if is_selected else None
        command_color = (
            tailwind_color("violet", 300)
            if is_selected
            else tailwind_color("violet", 400)
        )
        description_color = (
            tailwind_color("slate", 100)
            if is_selected
            else tailwind_color("slate", 400)
        )
        parts.append(
            Text(
                [
                    Text(
                        prefix,
                        color=tailwind_color("violet", 400),
                        background=background,
                    ),
                    Text(
                        f"{command:<12}",
                        color=command_color,
                        modifiers=("bold",) if is_selected else (),
                        background=background,
                    ),
                    Text(
                        f" {description}\n",
                        color=description_color,
                        background=background,
                    ),
                ]
            )
        )
    return Text(parts)


class AgentChat(BaseGrid, direction="vertical", gap=0):
    """Agent CLI with transcript, slash commands, and simulated tool calls."""

    header: str = Field(
        default="  ◆ xnano agent  ·  sonnet-4.6  ·  ~/projects/xnano",
        height=1,
        color=tailwind_color("sky", 400),
        modifiers=["bold"],
    )
    history: Text = Field(
        default=Text(""),
        border="rounded",
        border_color=tailwind_color("slate", 700),
        title=" Conversation ",
        title_position="top",
    )
    autocomplete: Text | None = Field(
        default=None,
        border="rounded",
        border_color=tailwind_color("slate", 700),
        title=" Commands ",
        title_position="top",
    )
    prompt: str = Field(
        default="▋",
        height=3,
        border="rounded",
        border_color=tailwind_color("slate", 700),
        title=" Prompt ",
        title_position="top",
        color=tailwind_color("slate", 100),
    )
    footer: str = Field(
        default=(
            "  [/] commands  [tab] complete  [↑↓/wheel] navigate/scroll  "
            "[enter] send  [q] quit"
        ),
        height=1,
        color=tailwind_color("slate", 600),
    )

    input_text: str = Field(default="", state=True)
    messages: list = Field(default_factory=lambda: list(_WELCOME), state=True)
    autocomplete_index: int = Field(default=0, state=True)
    scroll_offset: int = Field(default=0, state=True)
    sim_steps: list = Field(default_factory=list, state=True)
    sim_index: int = Field(default=0, state=True)
    sim_timer: float = Field(default=0.0, state=True)
    stream_chunks: list = Field(default_factory=list, state=True)
    stream_index: int = Field(default=0, state=True)
    stream_message_index: int = Field(default=-1, state=True)
    tick_time: float = Field(default=0.0, state=True)
    token_count: float = Field(default=12.4, state=True)

    def _matches(self) -> list[tuple[str, str]]:
        if not self.input_text.startswith("/"):
            return []
        return [
            (command, description)
            for command, description in _COMMANDS
            if command.startswith(self.input_text)
        ]

    def _add(self, kind: str, **kwargs: str) -> None:
        self.messages = [*self.messages, {"type": kind, **kwargs}]

    def _begin_stream(self, source: Iterable[str]) -> None:
        """Start revealing a new agent message incrementally from ``source``.

        ``source`` is consumed eagerly into state — a plain list, a
        generator, or a real streaming API's token iterator all work, since
        a ``BaseGrid`` state field must hold a concrete value rather than a
        live iterator.
        """
        self.messages = [*self.messages, {"type": "agent", "text": ""}]
        self.stream_chunks = list(source)
        self.stream_index = 0
        self.stream_message_index = len(self.messages) - 1

    def _advance_stream(self) -> bool:
        """Reveal the next chunk of the in-progress stream, if any.

        Returns:
            ``True`` while a stream is active (whether or not a chunk was
                applied this call), so the tick loop's normal step-advance
                logic is skipped for its entire duration.
        """
        if self.stream_message_index < 0:
            return False
        if self.stream_index >= len(self.stream_chunks):
            self.stream_message_index = -1
            self.stream_chunks = []
            self.stream_index = 0
            return False
        chunk = self.stream_chunks[self.stream_index]
        message = self.messages[self.stream_message_index]
        updated = {**message, "text": message.get("text", "") + chunk}
        self.messages = [
            *self.messages[: self.stream_message_index],
            updated,
            *self.messages[self.stream_message_index + 1 :],
        ]
        self.stream_index += 1
        return True

    def _start_simulation(self, steps: list[dict]) -> None:
        if not steps:
            return
        first = dict(steps[0])
        if first.get("type") == "tool":
            first["status"] = "active"
            first["_tick"] = self.tick_time
            self.messages = [*self.messages, first]
            self.sim_steps = steps
            self.sim_index = 0
            self.sim_timer = time.time()
        elif first.get("type") == "agent":
            self._begin_stream(_stream_chunks(first.get("text", "")))
            self.sim_steps = []
        else:
            self.messages = [*self.messages, first]
            self.sim_steps = []

    def _trigger_response(self, prompt: str) -> None:
        self._add("user", text=prompt)
        self.token_count = round(self.token_count + len(prompt) / 180.0, 1)
        lowered = prompt.lower()

        if any(keyword in lowered for keyword in ("test", "run", "check")):
            steps = [
                {
                    "type": "tool",
                    "tool_kind": "read",
                    "command": "examples/agent_chat.py",
                    "description": "Review current agent chat implementation",
                    "status": "active",
                    "output": "Scanning handlers and render paths...",
                    "duration": 1.0,
                    "next_output": "445 lines · 12 handlers · grid layout",
                },
                {
                    "type": "tool",
                    "tool_kind": "bash",
                    "command": "uv run pytest tests/test_grid_init.py -q",
                    "description": "Run targeted grid tests",
                    "status": "pending",
                    "output": "Running tests...",
                    "duration": 1.4,
                    "next_output": "12 passed in 0.41s",
                },
                {
                    "type": "tool",
                    "tool_kind": "edit",
                    "command": "scripts/generate_showcase_demos.py",
                    "description": "Register agent_chat in showcase pipeline",
                    "status": "pending",
                    "output": '+ ExampleConfig(name="agent_chat", ...)',
                    "duration": 1.2,
                    "next_output": "1 file changed, 18 insertions",
                },
                {
                    "type": "agent",
                    "text": (
                        "Tests passed and the showcase script is wired up. "
                        "Run generate_showcase_demos.py to record the GIFs."
                    ),
                },
            ]
        elif any(
            keyword in lowered for keyword in ("docs", "showcase", "gif")
        ):
            steps = [
                {
                    "type": "tool",
                    "tool_kind": "grep",
                    "command": "docs/index.md",
                    "description": "Find showcase blocks on the homepage",
                    "status": "active",
                    "output": "Searching for xnano-showcase sections...",
                    "duration": 1.0,
                    "next_output": "2 matches · feed + kanban hover blocks",
                },
                {
                    "type": "tool",
                    "tool_kind": "edit",
                    "command": "docs/index.md",
                    "description": "Add agent_chat monotone/color showcase block",
                    "status": "pending",
                    "output": "+ agent_chat showcase hover images",
                    "duration": 1.2,
                    "next_output": "1 file changed, 6 insertions",
                },
                {
                    "type": "agent",
                    "text": (
                        "Docs updated. The homepage will crossfade from "
                        "monotone to color on hover like the other showcases."
                    ),
                },
            ]
        else:
            steps = [
                {
                    "type": "tool",
                    "tool_kind": "grep",
                    "command": f'rg "{prompt[:32]}" xnano/',
                    "description": "Search codebase for relevant context",
                    "status": "active",
                    "output": "Indexing python sources...",
                    "duration": 1.1,
                    "next_output": "Found 8 matches in 3 modules.",
                },
                {
                    "type": "agent",
                    "text": (
                        "I found a few relevant spots. Want a plan, a patch, "
                        "or should I run tests first?"
                    ),
                },
            ]

        self._start_simulation(steps)

    def _last_agent_text(self) -> str | None:
        for message in reversed(self.messages):
            if message.get("type") == "agent":
                return message.get("text")
        return None

    def _execute_command(self, command: str, ctx) -> None:
        command = command.strip()
        base = command.split()[0] if command else ""
        if base == "/help":
            self._add(
                "agent",
                text=(
                    "Commands: /clear /compact /model /status /copy /fork. "
                    "Describe a task in plain language to run tools."
                ),
            )
        elif base == "/clear":
            self.messages = list(_WELCOME)
        elif base == "/compact":
            kept = (
                self.messages[-3:] if len(self.messages) > 3 else self.messages
            )
            self.messages = [
                *kept,
                {"type": "system", "text": "History compacted."},
            ]
        elif base == "/model":
            self._add("system", text="Active model: sonnet-4.6 (fast)")
        elif base == "/status":
            self._add(
                "system",
                text=(
                    f"session f8a21c · {self.token_count:.1f}k tokens · "
                    "3 tools available"
                ),
            )
        elif base == "/copy":
            text = self._last_agent_text()
            if text is None:
                self._add("system", text="No agent response to copy yet.")
            elif ctx.terminal is not None and ctx.terminal.copy_to_clipboard(
                text
            ):
                self._add(
                    "system",
                    text="Copied last agent response to clipboard.",
                )
            else:
                self._add(
                    "system",
                    text="Clipboard copy isn't supported here.",
                )
        elif base == "/fork":
            self._add(
                "system",
                text="Forking session... Created peer agent: 190ddc39",
            )
        else:
            self._add("system", text=f"Unknown command: {base}")

    @on_keyboard("enter")
    def _enter(self, ctx) -> None:
        matches = self._matches()
        if matches and 0 <= self.autocomplete_index < len(matches):
            command, _ = matches[self.autocomplete_index]
            self._execute_command(command, ctx)
            self.input_text = ""
            self.autocomplete_index = 0
        elif self.input_text.strip():
            self._trigger_response(self.input_text)
            self.input_text = ""

    @on_keyboard("backspace")
    def _backspace(self) -> None:
        self.input_text = self.input_text[:-1]
        self.autocomplete_index = 0

    @on_keyboard("tab")
    def _tab(self) -> None:
        matches = self._matches()
        if matches and 0 <= self.autocomplete_index < len(matches):
            command, _ = matches[self.autocomplete_index]
            self.input_text = command + " "
            self.autocomplete_index = 0

    @on_keyboard("up")
    def _up(self) -> None:
        matches = self._matches()
        if matches:
            self.autocomplete_index = (self.autocomplete_index - 1) % len(
                matches
            )
        else:
            self.scroll_offset += 3

    @on_keyboard("down")
    def _down(self) -> None:
        matches = self._matches()
        if matches:
            self.autocomplete_index = (self.autocomplete_index + 1) % len(
                matches
            )
        else:
            self.scroll_offset = max(0, self.scroll_offset - 3)

    @on_mouse(kind="scroll_up")
    def _scroll_up(self) -> None:
        self.scroll_offset += 3

    @on_mouse(kind="scroll_down")
    def _scroll_down(self) -> None:
        self.scroll_offset = max(0, self.scroll_offset - 3)

    @on_keyboard("q")
    def _quit(self, ctx) -> None:
        ctx.terminal.request_exit()

    @on_tick
    def _tick(self) -> None:
        self.tick_time = time.time() * 10.0
        if self._advance_stream():
            return
        if not self.sim_steps:
            return
        step = self.sim_steps[self.sim_index]
        if time.time() - self.sim_timer < step.get("duration", 1.0):
            return

        for message in reversed(self.messages):
            if message.get("type") == "tool" and message.get(
                "command"
            ) == step.get("command"):
                updated = {
                    **message,
                    "status": "success",
                    "output": step.get("next_output", ""),
                }
                index = self.messages.index(message)
                self.messages = [
                    *self.messages[:index],
                    updated,
                    *self.messages[index + 1 :],
                ]
                break

        self.sim_index += 1
        self.token_count = round(self.token_count + 0.3, 1)
        if self.sim_index < len(self.sim_steps):
            next_step = dict(self.sim_steps[self.sim_index])
            if next_step.get("type") == "tool":
                next_step["status"] = "active"
                next_step["_tick"] = self.tick_time
                self.messages = [*self.messages, next_step]
                self.sim_timer = time.time()
            elif next_step.get("type") == "agent":
                self._begin_stream(_stream_chunks(next_step.get("text", "")))
                self.sim_steps = []
            else:
                self.messages = [*self.messages, next_step]
                self.sim_steps = []
        else:
            self.sim_steps = []

    @on_keyboard
    def _character(self, ctx) -> None:
        keyboard = ctx.keyboard
        if keyboard is None:
            return
        character = getattr(keyboard, "character", None)
        if (
            character
            and len(character) == 1
            and character not in ("\n", "\r", "\t", "\x7f", "\x08")
        ):
            self.input_text = self.input_text + character
            self.autocomplete_index = 0

    def grid_render(self) -> None:
        matches = self._matches()
        annotated = [
            {**message, "_tick": self.tick_time}
            if message.get("type") == "tool"
            and message.get("status") == "active"
            else message
            for message in self.messages
        ]
        autocomplete_rows = len(matches) + 2 if matches else 0
        history_rows = max(
            6,
            self.rows - 2 - autocomplete_rows - 5,
        )
        # -2 for the rounded border; a little extra margin for row prefixes.
        content_width = max(20, self.columns - 6)
        history_lines = _build_message_lines(annotated, content_width)
        history_text, clamped_offset, is_scrolled = _windowed_history(
            history_lines, history_rows, self.scroll_offset
        )
        self.history = history_text
        if clamped_offset != self.scroll_offset:
            self.scroll_offset = clamped_offset
        self.grid_set_field(
            "history",
            title=(
                " Conversation · scrolled ↑ · ↓/wheel to catch up "
                if is_scrolled
                else " Conversation "
            ),
        )

        if matches:
            self.grid_set_field("autocomplete", height=autocomplete_rows)
            self.autocomplete = _render_autocomplete(
                matches,
                self.autocomplete_index,
            )
        else:
            self.autocomplete = None

        self.header = (
            f"  ◆ xnano agent  ·  sonnet-4.6  ·  ~/projects/xnano  ·  "
            f"{self.token_count:.1f}k tokens"
        )
        self.prompt = self.input_text + "▋"


if __name__ == "__main__":
    Terminal(tick_interval=15).run(AgentChat())
