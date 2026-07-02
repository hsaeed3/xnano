"""xnano example — agent_chat.py

Interactive, dynamic terminal simulation of an AI developer assistant.
"""

from __future__ import annotations

import math
import sys
import time

from xnano.color import Color
from xnano.events import Event, poll_event
from xnano.layout import Constraint, Layout, Rectangle
from xnano.style import Borders, Style
from xnano.tailwind import tailwind
from xnano.terminal import Frame, Terminal
from xnano.text import Line, Span, Text
from xnano.widgets import Block, ListItem, ListState, ListView, Paragraph

COMMANDS = [
    ("/quit", "Quit the application"),
    ("/home", "Return to the welcome screen"),
    ("/new", "Start a new session"),
    ("/fork", "Branch current session to peer agent"),
    ("/compact", "Compact conversation history"),
    ("/copy", "Copy last response to clipboard"),
]


def get_pulsing_color(t: float, offset: int) -> Color:
    """Compute a pulsing gradient color based on time and vertical offset."""
    phase = (t + offset * 0.8) % (2 * math.pi)
    val = math.sin(phase) * 0.5 + 0.5  # 0.0 to 1.0
    if val < 0.33:
        return tailwind("indigo", 400)
    elif val < 0.66:
        return tailwind("purple", 500)
    else:
        return tailwind("fuchsia", 400)


class AgentChatApp:
    def __init__(self) -> None:
        self.input_text = ""
        # Chat messages: list of dict representing history items
        self.messages: list[dict] = [
            {
                "type": "agent",
                "text": "Hello! Onwards!",
            }
        ]

        # State for scrollable list of messages
        self.list_state = ListState()

        # Autocomplete state
        self.autocomplete_index = 0

        # Step simulation state
        self.simulated_steps: list[dict] = []
        self.simulated_step_index = 0
        self.step_timer = 0.0

        # Pre-compiled styles (Dark themed black/slate)
        self.bg_style = Style(background="black")
        self.user_style = Style(
            foreground=tailwind("sky", 400), modifiers="bold"
        )
        self.agent_style = Style(
            foreground=tailwind("emerald", 400), modifiers="bold"
        )
        self.system_style = Style(
            foreground=tailwind("slate", 400), modifiers="italic"
        )
        self.border_style = Style(foreground=tailwind("slate", 700))
        self.input_style = Style(foreground="white", background="black")

    def add_message(self, sender: str, text: str) -> None:
        self.messages.append({"type": sender.lower(), "text": text})

    def trigger_agent_response(self, prompt: str) -> None:
        self.messages.append({"type": "user", "text": prompt})

        # Simple simulated responses based on keywords
        lowered = prompt.lower()
        if "test" in lowered or "run" in lowered or "check" in lowered:
            self.simulated_steps = [
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
                    "command": "cargo check 2>&1 && uv run mypy python/slash 2>&1",
                    "description": "Check Rust compile and mypy",
                    "status": "pending",
                    "output": "Compiling pyo3-build-config v0.23.5...",
                    "duration": 1.5,
                    "next_output": "All checks passed!",
                },
                {
                    "type": "agent",
                    "text": "I have run the tests and static check suites. Everything compiles, type-checks, and passes tests perfectly!",
                },
            ]
        else:
            self.simulated_steps = [
                {
                    "type": "task",
                    "command": f'xnano-search --query "{prompt}"',
                    "description": "Search codebase for context",
                    "status": "active",
                    "output": "Searching xnano/text.py and xnano/widget.py...",
                    "duration": 1.2,
                    "next_output": "Found 12 matches in 3 files.",
                },
                {
                    "type": "agent",
                    "text": f"I searched the codebase for context on your query. Let me know if you would like me to draft a plan or run tests!",
                },
            ]

        # Append first task
        first_step = self.simulated_steps[0]
        self.messages.append(dict(first_step))
        self.simulated_step_index = 0
        self.step_timer = time.time()

    def get_matching_commands(self) -> list[tuple[str, str]]:
        if not self.input_text.startswith("/"):
            return []
        return [
            (cmd, desc)
            for cmd, desc in COMMANDS
            if cmd.startswith(self.input_text)
        ]

    def autocomplete_text(self) -> None:
        matches = self.get_matching_commands()
        if matches and 0 <= self.autocomplete_index < len(matches):
            cmd, _ = matches[self.autocomplete_index]
            self.input_text = cmd + " "
            self.autocomplete_index = 0

    def navigate_autocomplete(self, direction: int) -> None:
        matches = self.get_matching_commands()
        if not matches:
            return
        self.autocomplete_index = (self.autocomplete_index + direction) % len(
            matches
        )

    def execute_command(self, cmd: str) -> None:
        cmd_clean = cmd.strip()
        self.add_message("User", cmd_clean)

        parts = cmd_clean.split()
        base_cmd = parts[0] if parts else ""

        if base_cmd == "/quit":
            raise SystemExit
        elif base_cmd == "/home":
            self.messages = [
                {
                    "type": "agent",
                    "text": "Hello! I am your Antigravity coding assistant. How can I help you today?",
                }
            ]
            self.list_state.select(0)
        elif base_cmd == "/new":
            self.messages = []
            self.add_message("System", "New session started. History cleared.")
        elif base_cmd == "/fork":
            self.add_message(
                "System",
                "Forking session... Created peer agent with Conversation ID: 190ddc39",
            )
        elif base_cmd == "/compact":
            if len(self.messages) > 2:
                self.messages = self.messages[-2:]
                self.add_message(
                    "System", "History compacted to last 2 messages."
                )
            else:
                self.add_message("System", "History is already compact.")
        elif base_cmd == "/copy":
            self.add_message(
                "System", "Copied last agent response to clipboard."
            )
        else:
            self.add_message("System", f"Unknown command: {base_cmd}")

    def update(self) -> None:
        # Step simulation logic
        if self.simulated_steps:
            elapsed = time.time() - self.step_timer
            current_step = self.simulated_steps[self.simulated_step_index]

            if elapsed >= current_step.get("duration", 1.0):
                # Complete the current active task message
                # Find it in self.messages
                for msg in reversed(self.messages):
                    if msg.get("type") == "task" and msg.get(
                        "command"
                    ) == current_step.get("command"):
                        msg["status"] = "success"
                        msg["output"] = current_step.get("next_output", "")
                        break

                # Advance to next step
                self.simulated_step_index += 1
                if self.simulated_step_index < len(self.simulated_steps):
                    next_step = self.simulated_steps[self.simulated_step_index]
                    if next_step.get("type") == "task":
                        next_step["status"] = "active"
                        self.messages.append(dict(next_step))
                        self.step_timer = time.time()
                    else:
                        # Agent final text response
                        self.messages.append(dict(next_step))
                        self.simulated_steps = []
                        self.simulated_step_index = 0
                else:
                    self.simulated_steps = []
                    self.simulated_step_index = 0

    def draw(self, frame: Frame) -> None:
        area = frame.area()

        # Determine if autocomplete menu is open
        matches = self.get_matching_commands()
        is_menu_open = len(matches) > 0

        # Vertical split: Chat History vs Autocomplete Menu vs Input Box
        if is_menu_open:
            layout = Layout(
                direction="vertical",
                constraints=[
                    Constraint.fill(1),
                    Constraint.length(len(matches) + 2),
                    Constraint.length(3),
                ],
            )
            splits = layout.split(area)
            history_area, menu_area, input_area = (
                splits[0],
                splits[1],
                splits[2],
            )
        else:
            layout = Layout(
                direction="vertical",
                constraints=[Constraint.fill(1), Constraint.length(3)],
            )
            splits = layout.split(area)
            history_area, input_area = splits[0], splits[1]
            menu_area = None

        # 1. Render Autocomplete Menu if open
        if is_menu_open and menu_area is not None:
            menu_lines = []
            for idx, (cmd, desc) in enumerate(matches):
                is_selected = idx == self.autocomplete_index
                prefix = " ❯ " if is_selected else "   "

                cmd_style = (
                    Style(foreground=tailwind("purple", 300), modifiers="bold")
                    if is_selected
                    else Style(foreground=tailwind("purple", 400))
                )
                desc_style = (
                    Style(foreground=tailwind("slate", 100))
                    if is_selected
                    else Style(foreground=tailwind("slate", 400))
                )
                bg = (
                    Style(background=tailwind("purple", 950))
                    if is_selected
                    else Style(background="#1e1e2e")
                )

                line_content = Line(
                    [
                        Span(
                            prefix,
                            style=bg.patch(
                                Style(foreground=tailwind("purple", 400))
                            ),
                        ),
                        Span(f"{cmd:<12}", style=bg.patch(cmd_style)),
                        Span(f" {desc}", style=bg.patch(desc_style)),
                    ]
                )
                menu_lines.append(line_content)

            menu_widget = Paragraph(
                Text(menu_lines),
                block=Block(
                    title=" Commands Autocomplete ",
                    borders="all",
                    border_type="rounded",
                    border_style=self.border_style,
                    style=self.bg_style,
                ),
            )
            frame.render_widget(menu_widget, menu_area)

        # 2. Render Chat History Panel
        history_items = []
        for msg in self.messages:
            msg_type = msg.get("type", "")

            if msg_type == "user":
                history_items.append(
                    ListItem(
                        Line(
                            [
                                Span(
                                    "❯ ",
                                    foreground=tailwind("sky", 400),
                                    modifiers="bold",
                                ),
                                Span(
                                    msg.get("text", ""),
                                    foreground="white",
                                    modifiers="bold",
                                ),
                            ]
                        )
                    )
                )
                history_items.append(ListItem(""))

            elif msg_type == "agent":
                history_items.append(
                    ListItem(
                        Line(
                            [
                                Span("◆ Agent: ", style=self.agent_style),
                                Span(
                                    msg.get("text", ""),
                                    foreground=tailwind("emerald", 100),
                                ),
                            ]
                        )
                    )
                )
                history_items.append(ListItem(""))

            elif msg_type == "system":
                history_items.append(
                    ListItem(
                        Line(
                            [
                                Span("ℹ ", style=self.system_style),
                                Span(
                                    msg.get("text", ""),
                                    style=self.system_style,
                                ),
                            ]
                        )
                    )
                )
                history_items.append(ListItem(""))

            elif msg_type == "task":
                status = msg.get("status", "")
                command = msg.get("command", "")
                description = msg.get("description", "")
                output = msg.get("output", "")

                # Determine pulsing vs static bar colors based on status and time
                if status == "active":
                    t = time.time() * 6.0
                    color1 = get_pulsing_color(t, 0)
                    color2 = get_pulsing_color(t, 1)
                    color3 = get_pulsing_color(t, 2)
                else:
                    color1 = color2 = color3 = tailwind("violet", 700)

                # Line 1: Bar prefix + Command name
                history_items.append(
                    ListItem(
                        Line(
                            [
                                Span("┃ ", foreground=color1),
                                Span(
                                    "◆ Run ",
                                    foreground=tailwind("purple", 400),
                                    modifiers="bold",
                                ),
                                Span(
                                    command,
                                    foreground="white",
                                    modifiers="bold",
                                ),
                            ]
                        )
                    )
                )
                # Line 2: Bar prefix + Description
                history_items.append(
                    ListItem(
                        Line(
                            [
                                Span("┃ ", foreground=color2),
                                Span(
                                    "  " + description,
                                    foreground=tailwind("slate", 400),
                                ),
                            ]
                        )
                    )
                )
                # Line 3 (Optional): Bar prefix + Output logs in a dark highlighted box (matching ss2)
                if output:
                    history_items.append(
                        ListItem(
                            Line(
                                [
                                    Span("┃ ", foreground=color3),
                                    Span(
                                        "  " + output,
                                        foreground=tailwind("slate", 300),
                                        background="#251b30",
                                    ),
                                ]
                            )
                        )
                    )
                # Spacer line following task section
                history_items.append(ListItem(""))

        # Auto-scroll history list state to bottom
        if history_items:
            self.list_state.select(len(history_items) - 1)

        history_list = ListView(
            history_items,
            block=Block(
                title=" Developer Agent Terminal ",
                title_alignment="center",
                borders="all",
                border_type="rounded",
                border_style=self.border_style,
                style=self.bg_style,
            ),
            style=self.bg_style,
        )
        frame.render_stateful_widget(
            history_list, history_area, self.list_state
        )

        # 3. Render Input Field Panel
        display_input = self.input_text + "▋"
        input_widget = Paragraph(
            display_input,
            block=Block(
                title=" Prompt Assistant (Type / for commands) ",
                borders="all",
                border_type="rounded",
                border_style=self.border_style,
                style=self.bg_style,
            ),
            style=self.input_style,
        )
        frame.render_widget(input_widget, input_area)


def main() -> None:
    app = AgentChatApp()

    def handle_enter() -> None:
        matches = app.get_matching_commands()
        if matches:
            if 0 <= app.autocomplete_index < len(matches):
                cmd, _ = matches[app.autocomplete_index]
                app.execute_command(cmd)
                app.input_text = ""
                app.autocomplete_index = 0
        else:
            if app.input_text.strip():
                app.trigger_agent_response(app.input_text)
                app.input_text = ""

    def handle_backspace() -> None:
        app.input_text = app.input_text[:-1]
        app.autocomplete_index = 0

    def handle_up() -> None:
        matches = app.get_matching_commands()
        if matches:
            app.navigate_autocomplete(-1)
        else:
            app.list_state.select_previous()

    def handle_down() -> None:
        matches = app.get_matching_commands()
        if matches:
            app.navigate_autocomplete(1)
        else:
            app.list_state.select_next()

    def handle_tab() -> None:
        app.autocomplete_text()

    def handle_char(character: str) -> None:
        if len(character) == 1:
            app.input_text += character
            app.autocomplete_index = 0

    with Terminal() as term:
        term.clear()

        while True:
            # Low latency event loop for smooth typewriter animation
            event = poll_event(15)
            if event:
                if event.keyboard and event.keyboard.is_press:
                    keyboard_event = event.keyboard
                    if keyboard_event.matches("ctrl+c"):
                        break
                    elif keyboard_event.matches("enter"):
                        handle_enter()
                    elif keyboard_event.matches("backspace"):
                        handle_backspace()
                    elif keyboard_event.matches("up"):
                        handle_up()
                    elif keyboard_event.matches("down"):
                        handle_down()
                    elif keyboard_event.matches("tab"):
                        handle_tab()
                    else:
                        character = keyboard_event.character
                        if character is not None:
                            handle_char(character)

            app.update()
            term.draw(app.draw)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        pass
