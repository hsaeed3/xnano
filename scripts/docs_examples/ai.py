"""
A widget written by a language model: a short program, run in xnano's sandbox.

Type what you want and press ``enter``: a ``ComponentModel`` asks its model for a program that
draws it, runs the program in the sandbox of ``xnano.sandbox`` and gives back the widget,
which is written next to the end of the program. A request typed after that changes the
widget, and the lines of the program that the change wrote are shown in pink. ``escape``
clears both.

The answers are the ones Claude Haiku 4.5 gave to the two requests of the recording, through
OpenRouter, replayed with ``xnano.ai.testing.scripted_model``: the example runs offline and
draws the same widget every time, whatever is typed. Give ``ComponentModel`` a model name
such as ``'openrouter:anthropic/claude-haiku-4.5'`` instead to ask a live model. Run it with
``python ai.py`` and press ``ctrl+c`` to quit.
"""

import dataclasses

import xnano
from xnano.ai.models.components import Component, ComponentModel
from xnano.ai.testing import scripted_model
from xnano.styles import Style, StyledText, TextSpan
from xnano.widgets import Block, Paragraph

PINK = (232, 118, 170)
DIM, BOLD = Style(dim=True), Style(bold=True)
WIDGET_WIDTH, WIDGET_HEIGHT = 34, 12
CODE_WIDTH, CODE_HEIGHT = 40, 17  # the end of the program that its panel shows
# what Claude Haiku 4.5 answered, in order: to 'a now playing card with a progress bar', then
# to 'make it pink'; each answer is the layout in a sentence and the program
ANSWERS = (
    # first: request 'a now playing card with a progress bar'
    {
        "layout": "A rounded card showing now playing info with a progress bar, centered on the canvas.",
        "program": """\
# Now playing card with progress bar
# Create a now playing card with song info and a progress bar

current_time = 1.5  # minutes
total_time = 3.8    # minutes
progress_percent = current_time / total_time

# Build the progress bar (10 characters wide)
bar_length = 10
filled = round(progress_percent * bar_length)
progress_bar = '█' * filled + '░' * (bar_length - filled)

# Format the time display
time_text = f'{int(current_time)}:{int((current_time % 1) * 60):02d} / {int(total_time)}:{int((total_time % 1) * 60):02d}'

# Create the content lines
lines = [
    'Now Playing',
    '',
    'Midnight City',
    'M83',
    '',
    progress_bar + f' {progress_percent:.0%}',
    time_text,
]

# Draw the card centered
canvas.screen.write(
    lines,
    x='center',
    y='center',
    border='rounded',
    bold=True,
)
""",
    },
    # second: request 'make it pink'
    {
        "layout": "Now playing card with progress bar, in pink",
        "program": """\
# Now playing card with progress bar, in pink
# Create a now playing card with song info and a progress bar

current_time = 1.5  # minutes
total_time = 3.8    # minutes
progress_percent = current_time / total_time

# Build the progress bar (10 characters wide)
bar_length = 10
filled = round(progress_percent * bar_length)
progress_bar = '█' * filled + '░' * (bar_length - filled)

# Format the time display
time_text = f'{int(current_time)}:{int((current_time % 1) * 60):02d} / {int(total_time)}:{int((total_time % 1) * 60):02d}'

# Create the content lines
lines = [
    'Now Playing',
    '',
    'Midnight City',
    'M83',
    '',
    progress_bar + f' {progress_percent:.0%}',
    time_text,
]

# Draw the card centered with pink colors
canvas.screen.write(
    lines,
    x='center',
    y='center',
    border='rounded',
    bold=True,
    foreground='#ff69b4',
    background='#ffe0f0',
)""",
    },
)


def replaying_model() -> ComponentModel:
    """A component model that gives the recorded answers, one for each request."""
    return ComponentModel(scripted_model(*ANSWERS, repeat_last=True).model)


@dataclasses.dataclass
class Session:
    """What is being typed, the widget so far and the program it was drawn by before."""

    model: ComponentModel = dataclasses.field(default_factory=replaying_model)
    request: str = ""
    widget: Component | None = None
    earlier_program: str = ""

    def clear(self) -> None:
        """Forget the request and the widget, and replay the answers from the first."""
        self.model, self.request = replaying_model(), ""
        self.widget, self.earlier_program = None, ""


session = Session()


@xnano.writable
def request_line(context: xnano.Context) -> Paragraph:
    """The request being typed, or what to type while there is none."""
    typed = TextSpan(session.request + "▏") if session.request else None
    hint = TextSpan("describe a widget, then press enter", style=DIM)
    text = StyledText([TextSpan("› ", style=Style(PINK, bold=True)), typed or hint])
    return Paragraph(text, width=76, height=1)


@xnano.writable
def program(context: xnano.Context) -> Paragraph:
    """The end of the widget's program, numbered, with the lines of the last change in pink."""
    if session.widget is None:
        return Paragraph("the program the model writes", style=DIM, width=CODE_WIDTH)
    lines = session.widget.code.rstrip().splitlines()
    earlier = session.earlier_program.splitlines()
    first = max(len(lines) - CODE_HEIGHT, 0)
    spans = []
    for number, line in enumerate(lines[first:], start=first + 1):
        is_changed = bool(earlier) and line not in earlier
        room = CODE_WIDTH - 4  # after the line number
        shown = line if len(line) <= room else line[: room - 1] + "…"
        style = Style(PINK, bold=True) if is_changed else Style()
        spans.append(TextSpan(f"{number:>2}  ", style=DIM))
        spans.append(TextSpan(shown + "\n", style=style))
    return Paragraph(StyledText(spans), width=CODE_WIDTH, height=CODE_HEIGHT)


@xnano.writable
def widget(context: xnano.Context) -> Component | Paragraph:
    """The widget the program draws."""
    if session.widget is None:
        hint = "the widget it draws"
        return Paragraph(hint, style=DIM, alignment="center", width=WIDGET_WIDTH)
    return session.widget


with xnano.open(title="xnano.ai") as terminal:
    screen = terminal.screen
    title = [TextSpan("◆ ", style=Style(PINK)), TextSpan("xnano.ai", style=BOLD)]
    title.append(TextSpan("  ComponentModel", style=DIM))
    screen.write(Paragraph(StyledText(title), width=27, height=1), x=1, y=0)
    panels = ((" request ", 0, 1, 80, 3), (" program · xnano.sandbox ", 0, 4, 44, 19))
    for name, x, y, width, height in (*panels, (" widget ", 44, 4, 36, 19)):
        frame = Block(name, border_type="rounded", border_style=DIM, title_style=BOLD)
        screen.write(frame, x=x, y=y, width=width, height=height)
    prompt = screen.write(request_line, x=2, y=2)
    code = screen.write(program, x=2, y=5)
    drawn = screen.write(widget, x=45, y=7)
    keys = "enter  ask the model  ·  esc  clear  ·  ctrl+c  quit"
    screen.write(keys, x="center", y="bottom", dim=True)

    @terminal.hook(on="key")
    def type_request(context: xnano.Context) -> None:
        """Type the request, or clear everything with escape."""
        key, text = context.keyboard.key, context.keyboard.text
        if key == "escape":
            session.clear()
            code.refresh()
            drawn.refresh()
        elif key == "backspace":
            session.request = session.request[:-1]
        elif text and key != "enter":
            session.request += text
        prompt.refresh()

    @terminal.hook(on="key", keys="enter")
    async def ask(context: xnano.Context) -> None:
        """Ask for the widget, or for a change to the one there is, and show its program."""
        request = session.request.strip()
        if not request:
            return
        if session.widget is None:
            answer = session.model.generate_async(
                request, width=WIDGET_WIDTH, height=WIDGET_HEIGHT
            )
        else:
            answer = session.model.edit_async(session.widget, request)
        session.earlier_program = session.widget.code if session.widget else ""
        session.widget, session.request = await answer, ""
        for placement in (prompt, code, drawn):
            placement.refresh()

    terminal.run()
