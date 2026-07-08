"""xnano example — agent_chat.py

Interactive terminal simulation of an AI developer assistant.
"""

from __future__ import annotations

import math
import time

from xnano.beta import Field, Grid, Terminal, on_keyboard, on_tick
from xnano.beta.components import Text
from xnano.beta.color import tailwind_color


_COMMANDS = [
    ("/quit", "Quit the application"),
    ("/home", "Return to the welcome screen"),
    ("/new", "Start a new session"),
    ("/fork", "Branch current session to peer agent"),
    ("/compact", "Compact conversation history"),
    ("/copy", "Copy last response to clipboard"),
]


def _pulsing_color(t: float, offset: int) -> str:
    phase = (t + offset * 0.8) % (2 * math.pi)
    val = math.sin(phase) * 0.5 + 0.5
    if val < 0.33:
        c = tailwind_color("indigo", 400)
    elif val < 0.66:
        c = tailwind_color("purple", 500)
    else:
        c = tailwind_color("fuchsia", 400)
    return f"#{c.r:02x}{c.g:02x}{c.b:02x}"


def _render_messages(messages: list[dict], height: int) -> Text:
    lines: list[str | Text] = []
    for msg in messages:
        kind = msg.get("type", "")
        text = msg.get("text", "")
        command = msg.get("command", "")
        description = msg.get("description", "")
        output = msg.get("output", "")
        status = msg.get("status", "")
        t = msg.get("_tick", 0.0)

        if kind == "user":
            lines.append(
                Text(
                    [
                        Text(
                            "❯ ",
                            color=tailwind_color("sky", 400),
                            modifiers=("bold",),
                        ),
                        Text(text + "\n", color="white", modifiers=("bold",)),
                    ]
                )
            )
            lines.append(Text("\n"))

        elif kind == "agent":
            lines.append(
                Text(
                    [
                        Text(
                            "◆ Agent: ",
                            color=tailwind_color("emerald", 400),
                            modifiers=("bold",),
                        ),
                        Text(
                            text + "\n", color=tailwind_color("emerald", 100)
                        ),
                    ]
                )
            )
            lines.append(Text("\n"))

        elif kind == "system":
            lines.append(
                Text(
                    [
                        Text(
                            "ℹ ",
                            color=tailwind_color("slate", 400),
                            modifiers=("italic",),
                        ),
                        Text(
                            text + "\n",
                            color=tailwind_color("slate", 400),
                            modifiers=("italic",),
                        ),
                    ]
                )
            )
            lines.append(Text("\n"))

        elif kind == "task":
            if status == "active":
                c1 = _pulsing_color(t, 0)
                c2 = _pulsing_color(t, 1)
                c3 = _pulsing_color(t, 2)
            else:
                c1 = c2 = c3 = (
                    f"#{tailwind_color('violet', 700).r:02x}{tailwind_color('violet', 700).g:02x}{tailwind_color('violet', 700).b:02x}"
                )
            lines.append(
                Text(
                    [
                        Text("┃ ", color=c1),
                        Text(
                            "◆ Run ",
                            color=tailwind_color("purple", 400),
                            modifiers=("bold",),
                        ),
                        Text(
                            command + "\n", color="white", modifiers=("bold",)
                        ),
                    ]
                )
            )
            lines.append(
                Text(
                    [
                        Text("┃ ", color=c2),
                        Text(
                            "  " + description + "\n",
                            color=tailwind_color("slate", 400),
                        ),
                    ]
                )
            )
            if output:
                lines.append(
                    Text(
                        [
                            Text("┃ ", color=c3),
                            Text(
                                "  " + output + "\n",
                                color=tailwind_color("slate", 300),
                                background="#251b30",
                            ),
                        ]
                    )
                )
            lines.append(Text("\n"))

    if not lines:
        return Text("")

    # Only show the last `height` lines worth of content (auto-scroll)
    visible = lines[-max(1, height) :]
    return Text(visible)


def _render_autocomplete(
    matches: list[tuple[str, str]], selected: int
) -> Text:
    parts: list[str | Text] = []
    for idx, (cmd, desc) in enumerate(matches):
        is_sel = idx == selected
        prefix = " ❯ " if is_sel else "   "
        bg = tailwind_color("purple", 950) if is_sel else None
        cmd_color = (
            tailwind_color("purple", 300)
            if is_sel
            else tailwind_color("purple", 400)
        )
        desc_color = (
            tailwind_color("slate", 100)
            if is_sel
            else tailwind_color("slate", 400)
        )
        parts.append(
            Text(
                [
                    Text(
                        prefix,
                        color=tailwind_color("purple", 400),
                        background=bg,
                    ),
                    Text(
                        f"{cmd:<12}",
                        color=cmd_color,
                        modifiers=("bold",) if is_sel else (),
                        background=bg,
                    ),
                    Text(f" {desc}\n", color=desc_color, background=bg),
                ]
            )
        )
    return Text(parts)


class AgentChat(Grid, direction="vertical", background="black"):
    history: Text = Field(
        default=Text(""),
        border="rounded",
        border_color=tailwind_color("slate", 700),
        title=" Developer Agent Terminal ",
        title_position="top",
        background="black",
    )
    autocomplete: Text | None = Field(
        default=None,
        border="rounded",
        border_color=tailwind_color("slate", 700),
        title=" Commands Autocomplete ",
        background="black",
    )
    prompt: str = Field(
        default="▋",
        height=3,
        border="rounded",
        border_color=tailwind_color("slate", 700),
        title=" Prompt Assistant (Type / for commands) ",
        color="white",
        background="black",
    )

    input_text: str = Field(default="", state=True)
    messages: list = Field(
        default_factory=lambda: [{"type": "agent", "text": "Hello! Onwards!"}],
        state=True,
    )
    autocomplete_index: int = Field(default=0, state=True)
    sim_steps: list = Field(default_factory=list, state=True)
    sim_index: int = Field(default=0, state=True)
    sim_timer: float = Field(default=0.0, state=True)
    tick_time: float = Field(default=0.0, state=True)

    def _matches(self) -> list[tuple[str, str]]:
        if not self.input_text.startswith("/"):
            return []
        return [(c, d) for c, d in _COMMANDS if c.startswith(self.input_text)]

    def _add(self, kind: str, **kwargs: str) -> None:
        self.messages = [*self.messages, {"type": kind, **kwargs}]

    def _trigger_response(self, prompt: str) -> None:
        self._add("user", text=prompt)
        low = prompt.lower()
        if any(kw in low for kw in ("test", "run", "check")):
            steps: list[dict] = [
                {
                    "type": "task",
                    "command": "uv run pytest -q 2>&1",
                    "description": "Run pytest suite",
                    "status": "active",
                    "output": "Running tests...",
                    "duration": 1.5,
                    "next_output": "12 passed in 0.11s",
                },
                {
                    "type": "task",
                    "command": "cargo check 2>&1 && uv run mypy python/ 2>&1",
                    "description": "Check Rust compile and mypy",
                    "status": "pending",
                    "output": "Compiling pyo3-build-config v0.23.5...",
                    "duration": 1.5,
                    "next_output": "All checks passed!",
                },
                {
                    "type": "agent",
                    "text": "Tests and static checks passed perfectly!",
                },
            ]
        else:
            steps = [
                {
                    "type": "task",
                    "command": f'xnano-search --query "{prompt}"',
                    "description": "Search codebase for context",
                    "status": "active",
                    "output": "Searching xnano/text.py...",
                    "duration": 1.2,
                    "next_output": "Found 12 matches in 3 files.",
                },
                {
                    "type": "agent",
                    "text": "Searched the codebase. Let me know if you'd like a plan or tests!",
                },
            ]
        first = dict(steps[0])
        first["_tick"] = self.tick_time
        self.messages = [*self.messages, first]
        self.sim_steps = steps
        self.sim_index = 0
        self.sim_timer = time.time()

    def _execute_command(self, cmd: str) -> None:
        cmd = cmd.strip()
        base = cmd.split()[0] if cmd else ""
        if base == "/quit":
            from xnano.beta.exceptions import Exit

            raise Exit
        elif base == "/home":
            self.messages = [
                {"type": "agent", "text": "Hello! How can I help you today?"}
            ]
        elif base == "/new":
            self.messages = [
                {"type": "system", "text": "New session started."}
            ]
        elif base == "/fork":
            self._add(
                "system",
                text="Forking session... Created peer agent: 190ddc39",
            )
        elif base == "/compact":
            kept = (
                self.messages[-2:] if len(self.messages) > 2 else self.messages
            )
            self.messages = [
                *kept,
                {"type": "system", "text": "History compacted."},
            ]
        elif base == "/copy":
            self._add(
                "system", text="Copied last agent response to clipboard."
            )
        else:
            self._add("system", text=f"Unknown command: {base}")

    @on_keyboard("enter")
    def _enter(self) -> None:
        matches = self._matches()
        if matches and 0 <= self.autocomplete_index < len(matches):
            cmd, _ = matches[self.autocomplete_index]
            self._execute_command(cmd)
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
            cmd, _ = matches[self.autocomplete_index]
            self.input_text = cmd + " "
            self.autocomplete_index = 0

    @on_keyboard("up")
    def _up(self) -> None:
        matches = self._matches()
        if matches:
            self.autocomplete_index = (self.autocomplete_index - 1) % len(
                matches
            )

    @on_keyboard("down")
    def _down(self) -> None:
        matches = self._matches()
        if matches:
            self.autocomplete_index = (self.autocomplete_index + 1) % len(
                matches
            )

    @on_tick
    def _tick(self) -> None:
        self.tick_time = time.time() * 6.0
        if not self.sim_steps:
            return
        step = self.sim_steps[self.sim_index]
        if time.time() - self.sim_timer >= step.get("duration", 1.0):
            for msg in reversed(self.messages):
                if msg.get("type") == "task" and msg.get(
                    "command"
                ) == step.get("command"):
                    updated = {
                        **msg,
                        "status": "success",
                        "output": step.get("next_output", ""),
                    }
                    idx = self.messages.index(msg)
                    self.messages = [
                        *self.messages[:idx],
                        updated,
                        *self.messages[idx + 1 :],
                    ]
                    break
            self.sim_index += 1
            if self.sim_index < len(self.sim_steps):
                nxt = dict(self.sim_steps[self.sim_index])
                if nxt.get("type") == "task":
                    nxt["status"] = "active"
                    nxt["_tick"] = self.tick_time
                    self.messages = [*self.messages, nxt]
                    self.sim_timer = time.time()
                else:
                    self.messages = [*self.messages, nxt]
                    self.sim_steps = []
            else:
                self.sim_steps = []

    @on_keyboard
    def _char(self, ctx) -> None:
        kbd = ctx.keyboard
        if kbd is None:
            return
        char = getattr(kbd, "character", None)
        if (
            char
            and len(char) == 1
            and char not in ("\n", "\r", "\t", "\x7f", "\x08")
        ):
            self.input_text = self.input_text + char
            self.autocomplete_index = 0

    def grid_render(self) -> None:
        matches = self._matches()
        annotated = [
            {**m, "_tick": self.tick_time}
            if m.get("type") == "task" and m.get("status") == "active"
            else m
            for m in self.messages
        ]
        history_rows = max(
            4, self.rows - 3 - (len(matches) + 2 if matches else 0) - 2
        )
        self.history = _render_messages(annotated, history_rows)

        if matches:
            self.grid_set_field("autocomplete", height=len(matches) + 2)
            self.autocomplete = _render_autocomplete(
                matches, self.autocomplete_index
            )
        else:
            self.autocomplete = None

        self.prompt = self.input_text + "▋"


if __name__ == "__main__":
    Terminal(tick_interval=15).run(AgentChat())
