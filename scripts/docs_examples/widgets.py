"""
A git client in the terminal: a branch tree, a commit graph and the details of a commit.

Everything is drawn with ``xnano.widgets``: bordered blocks, a table for the commit graph,
lists for the branch tree and the branch menu, and paragraphs of styled text. ``↑`` and
``↓`` move through the commits, a click on a ``▸`` folder opens it, and ``b`` opens the
branch menu over the graph. Run it with ``python widgets.py`` and press ``q`` to quit.
"""

import dataclasses
import textwrap

import xnano
from xnano.styles import Style, StyledText, TextSpan
from xnano.widgets import Block, ItemList, Paragraph, Table, TableCell, TableRow

LANES = ((232, 118, 170), (96, 152, 236), (148, 108, 230), (228, 160, 62))
"""The color of each lane of the graph: pastel pink, pastel blue, purple, light amber."""
LANE_BRANCHES = ("main", "fix/audio-tuning", "docs/learn", "feature/pixel-art")
BRANCHES = ("main", "feature/pixel-art", "fix/audio-tuning", "docs/learn")
INK, PAPER, SELECTION = (21, 23, 28), (245, 246, 250), (74, 80, 112)
SELECTED = Style(PAPER, SELECTION, bold=True)
DIM, BOLD = Style(dim=True), Style(bold=True)
GREEN, RED = (64, 168, 100), (222, 92, 96)
AUTHORS = {"HS": ("hsaeed3", LANES[0]), "DB": ("dependabot", LANES[1])}
# the three panels side by side: the left edge and the width of each, in cells
PANELS = {"branches": (0, 17), "commits": (17, 42), "commit": (59, 21)}
PANEL_HEIGHT = 22  # between the top bar and the status line
TREE_WIDTH = PANELS["branches"][1] - 3  # inside the border, after a column of padding
GRAPH_WIDTH = PANELS["commits"][1] - 2
DETAILS_WIDTH = PANELS["commit"][1] - 2
GRAPH_COLUMNS = 8  # two for each of the four lanes
MESSAGE_WIDTH = GRAPH_WIDTH - GRAPH_COLUMNS - 2 - 3 - 3  # what the other columns leave


# the history, newest first: the graph, the hash, the author, the age, the branches and
# tags on the commit (tags start with ◆) and the message
LOG = """
●       | c1f04e2 | HS | 2h | main ◆v2.1.2      | release: xnano-core 2.1.2
○─╮     | 8e3b7a1 | HS | 3h |                   | Merge branch 'fix/audio-tuning'
│ ●     | 4b28609 | HS | 4h | fix/audio-tuning  | fix(xnano-audio): keep bell chords in tune (#186)
│ │   ● | 9d1c3f7 | HS | 5h | feature/pixel-art | feat(art): pixel art written as text rows
● │   │ | 12da7d9 | HS | 6h |                   | fix(xnano-core): drop the trailing newline from ANSI renders (#185)
│ │ ● │ | a7e2b90 | HS | 8h | docs/learn        | docs: write the getting started guide
│ ● │ │ | 5f60c3a | HS | 9h |                   | fix(xnano-audio): tune the overtones of the bell
●─╯ │ │ | 066523d | HS | 1d |                   | test(xnano-core): make the output capture test reliable (#184)
│   │ ● | e41b8d2 | HS | 1d |                   | feat(art): worlds seen through a camera
●   │ │ | 491985c | HS | 2d |                   | feat!: add xnano.ai and group the API into devices, layout, styles and hooks (#183)
│   ● │ | b38f0c5 | HS | 2d |                   | docs: document hooks and contexts
●───╯ │ | 45e08fa | HS | 3d |                   | feat: show transparent image pixels, type input values and add random choices (#182)
│     ● | 7c2d9a4 | HS | 3d |                   | feat(art): a palette for every sprite
●─────╯ | 3fa61b8 | DB | 4d |                   | build(deps): bump ratatui from 0.29.0 to 0.30.0
●       | d09e5c7 | HS | 5d |                   | ci: build WebAssembly wheels for Pyodide
●       | 6b14f2e | HS | 6d |                   | refactor(core): split the render pipeline into crates
●       | 2e8a7d1 | HS | 1w |                   | perf(grid): cache the width of every cell
●       | f5c3b09 | HS | 1w | ◆v2.0.0           | release: xnano 2.0.0
●       | 90ad4e6 | HS | 2w |                   | docs: the v2 README
"""
FILES = {  # the files each commit changed: the name, the lines added and the lines removed
    "c1f04e2": "Cargo.toml 2 2, pyproject.toml 1 1, HISTORY.md 14 0",
    "8e3b7a1": "bells.rs 24 10",
    "4b28609": "bells.rs 18 6, test_audio.py 24 0",
    "9d1c3f7": "_worlds.py 64 8, test_art.py 31 0",
    "12da7d9": "render.rs 3 5, test_render.py 6 1",
    "a7e2b90": "getting-started.md 142 0",
    "5f60c3a": "bells.rs 6 4",
    "066523d": "test_output.py 12 9",
    "e41b8d2": "_worlds.py 88 12",
    "491985c": "__init__.py 40 22, models.py 610 0, devices.py 18 4",
    "b38f0c5": "hooks.md 96 3",
    "45e08fa": "_images.py 22 7, keyboard.py 31 2",
    "7c2d9a4": "_worlds.py 27 3",
    "3fa61b8": "Cargo.lock 41 38, Cargo.toml 1 1",
    "d09e5c7": "wheels.yml 58 0",
    "6b14f2e": "lib.rs 120 340, Cargo.toml 12 2",
    "2e8a7d1": "cells.rs 44 19",
    "f5c3b09": "pyproject.toml 1 1",
    "90ad4e6": "README.md 212 96",
}
DIFFS = {  # a few changed lines of the first file of some commits
    "c1f04e2": ('-version = "2.1.1"', '+version = "2.1.2"'),
    "8e3b7a1": ("-let ratio = 2.76;", "+let ratio = 2.0;", "+tune(&mut chord);"),
    "4b28609": ("-let ratio = 2.76;", "+let ratio = 2.0;"),
    "9d1c3f7": ("-def from_rows(rows)", "+def pixel_art(", "+    rows, palette"),
    "12da7d9": ("-out.push('\\n');", "+out.trim_end();"),
    "a7e2b90": ("+# Getting started", "+pip install xnano"),
}


@dataclasses.dataclass(frozen=True)
class Commit:
    """One commit: its place in the graph, who made it, what it says and what it changed."""

    graph: str
    hash: str
    author: str
    age: str
    labels: tuple[str, ...]
    message: str
    files: tuple[tuple[str, int, int], ...]
    diff: tuple[str, ...]


def read_log(log: str) -> tuple[Commit, ...]:
    """The commits of ``LOG``, with the files they changed and their diffs."""
    commits = []
    for line in log.strip().splitlines():
        graph, commit_hash, author, age, labels, message = (
            part.strip() for part in line.split("|")
        )
        changes = [change.split() for change in FILES[commit_hash].split(", ")]
        files = tuple(
            (name, int(added), int(removed)) for name, added, removed in changes
        )
        diff = DIFFS.get(commit_hash, ())
        commits.append(
            Commit(
                graph,
                commit_hash,
                author,
                age,
                tuple(labels.split()),
                message,
                files,
                diff,
            )
        )
    return tuple(commits)


COMMITS = read_log(LOG)


@dataclasses.dataclass
class Folder:
    """A node of the branch tree: its name, whether it is open and what it holds."""

    name: str
    is_open: bool
    children: tuple["Folder | str", ...]
    is_section: bool = False


TREE = (
    Folder(
        "LOCAL",
        True,
        (
            "● main",
            Folder("feature", True, ("pixel-art",)),
            Folder("fix", True, ("audio-tuning",)),
            Folder("docs", False, ("learn",)),
        ),
        is_section=True,
    ),
    Folder(
        "REMOTE",
        False,
        ("origin/main", "origin/v1", "origin/v2", "origin/gh-pages"),
        is_section=True,
    ),
    Folder(
        "TAGS",
        True,
        (
            Folder("xnano-core", True, ("v2.1.2", "v2.1.1")),
            Folder("xnano", False, ("v2.0.0",)),
        ),
        is_section=True,
    ),
    Folder("STASHES", False, ("WIP on main",), is_section=True),
)


@dataclasses.dataclass
class App:
    """What is selected, open and checked out."""

    selected: int = 0
    branch: str = "main"
    is_menu_open: bool = False
    menu_index: int = 0


app = App()


def shortened(text: str, width: int) -> str:
    """The text, cut to ``width`` cells with an ellipsis when it is longer."""
    return text if len(text) <= width else text[: width - 1] + "…"


def text_line(spans: list[TextSpan]) -> Paragraph:
    """One line of styled text, exactly as wide as the text."""
    text = StyledText(spans)
    return Paragraph(text, width=len(str(text)), height=1)


def lane_of(commit: Commit) -> int:
    """The lane of the graph that a commit's dot sits on."""
    return (
        next(column for column, glyph in enumerate(commit.graph) if glyph in "●○") // 2
    )


def parents(index: int) -> list[Commit]:
    """
    The commits a commit was made on top of.

    That is the next dot down its own lane and, for a merge, the next dot down the lane it
    merges in.
    """
    graph = COMMITS[index].graph.ljust(GRAPH_COLUMNS)
    lanes = [lane_of(COMMITS[index])] + [graph.find("╮") // 2] * ("╮" in graph)
    found = []
    for lane in lanes:
        for below in COMMITS[index + 1 :]:
            glyph = below.graph.ljust(GRAPH_COLUMNS)[lane * 2]
            if glyph in "●○╯":  # its dot, or the corner where the lane began
                found.append(below)
                break
    return found


def graph_spans(commit: Commit) -> list[TextSpan]:
    """The graph of a row, each character in the color of its lane."""
    graph = commit.graph.ljust(GRAPH_COLUMNS)
    spans = []
    for column, glyph in enumerate(graph):
        lane = column // 2
        if glyph == "─":  # a line toward a lane takes the color of that lane
            corner = next(
                index for index in range(column, len(graph)) if graph[index] in "╮╯"
            )
            lane = corner // 2
        spans.append(TextSpan(glyph, style=Style(LANES[lane])))
    return spans


def message_spans(commit: Commit) -> list[TextSpan]:
    """The branch and tag labels of a commit as chips, then as much of its message as fits."""
    spans, room = [], MESSAGE_WIDTH
    for label in commit.labels:
        if label.startswith("◆"):
            text, style = label + " ", Style(LANES[3], bold=True)
        else:
            lane_color = LANES[lane_of(commit)]
            text, style = f" {shortened(label, 10)} ", Style(INK, lane_color, bold=True)
        spans += [TextSpan(text, style=style), TextSpan(" ")]
        room -= len(text) + 1
    return [*spans, TextSpan(shortened(commit.message, room))]


@xnano.writable
def commit_graph(context: xnano.Context) -> Table:
    """The commit graph, with the selected commit's row highlighted."""
    rows = []
    for index, commit in enumerate(COMMITS):
        is_selected = index == app.selected
        cells = [
            TableCell(StyledText(graph_spans(commit))),
            TableCell(StyledText(message_spans(commit))),
            TableCell(commit.author, style=Style(AUTHORS[commit.author][1], bold=True)),
            TableCell(commit.age.rjust(3), style=Style() if is_selected else DIM),
        ]
        rows.append(TableRow(cells, style=SELECTED if is_selected else None))
    return Table(
        rows,
        header=TableRow(["graph", "message", "by", "age"], style=DIM),
        widths=[GRAPH_COLUMNS, MESSAGE_WIDTH, 2, 3],
        column_spacing=1,
        width=GRAPH_WIDTH,
        height=PANEL_HEIGHT - 2,
    )


def count_spans(label: str, added: int, removed: int) -> list[TextSpan]:
    """A label, then its added lines in green and removed lines in red, on one line."""
    counts = [TextSpan(f"+{added}", style=Style(GREEN))]
    if removed:
        counts.append(TextSpan(f" -{removed}", style=Style(RED)))
    room = DETAILS_WIDTH - len(str(StyledText(counts))) - 1
    return [TextSpan(shortened(label, room).ljust(room + 1)), *counts, TextSpan("\n")]


@xnano.writable
def details(context: xnano.Context) -> Paragraph:
    """The selected commit: hash, author, message, parents, changed files and a diff."""
    commit = COMMITS[app.selected]
    name, color = AUTHORS[commit.author]
    width = DETAILS_WIDTH
    rule = TextSpan("─" * width + "\n", style=DIM)
    spans = [
        TextSpan(commit.hash, style=Style(LANES[3], bold=True)),
        TextSpan(f"  {commit.age} ago\n", style=DIM),
        TextSpan(f" {commit.author} ", style=Style(INK, color, bold=True)),
        TextSpan(f" {name}\n"),
        rule,
        TextSpan("\n".join(textwrap.wrap(commit.message, width)) + "\n\n", style=BOLD),
        TextSpan("parent ", style=DIM),
        TextSpan(
            "\n       ".join(parent.hash for parent in parents(app.selected)) + "\n"
        ),
        TextSpan("branch ", style=DIM),
        TextSpan(shortened(LANE_BRANCHES[lane_of(commit)], width - 7) + "\n"),
        rule,
    ]
    added = sum(added for _, added, _ in commit.files)
    removed = sum(removed for _, _, removed in commit.files)
    file_count = len(commit.files)
    spans += count_spans(f"{file_count} file" + "s" * (file_count > 1), added, removed)
    for file_name, file_added, file_removed in commit.files:
        spans += count_spans(file_name, file_added, file_removed)
    if commit.diff:
        spans.append(TextSpan(f"\n{commit.files[0][0]}\n", style=DIM))
        for line in commit.diff:
            color = GREEN if line.startswith("+") else RED
            spans.append(TextSpan(shortened(line, width) + "\n", style=Style(color)))
    return Paragraph(StyledText(spans), width=DETAILS_WIDTH, height=PANEL_HEIGHT - 2)


def tree_lines() -> list[tuple[StyledText, Folder | None]]:
    """The visible lines of the branch tree, each with the folder it opens or closes."""
    lines: list[tuple[StyledText, Folder | None]] = []

    def add(node: Folder | str, depth: int) -> None:
        indent = "  " * depth
        if isinstance(node, str):
            style = Style(LANES[0], bold=True) if node.startswith("●") else Style()
            text = indent + shortened(node, TREE_WIDTH - len(indent))
            lines.append((StyledText([TextSpan(text, style=style)]), None))
            return
        count = (
            [TextSpan(f"  {len(node.children)}", style=DIM)] if node.is_section else []
        )
        title = StyledText(
            [
                TextSpan(indent + ("▾ " if node.is_open else "▸ "), style=DIM),
                TextSpan(node.name, style=BOLD if node.is_section else Style()),
                *count,
            ]
        )
        lines.append((title, node))
        if node.is_open:
            for child in node.children:
                add(child, depth + 1)

    for section in TREE:
        add(section, 0)
    return lines


@xnano.writable
def branch_tree(context: xnano.Context) -> ItemList:
    """The branches, remotes, tags and stashes, folded as they are now."""
    lines = [line for line, _ in tree_lines()]
    return ItemList(lines, width=TREE_WIDTH, height=PANEL_HEIGHT - 2)


@xnano.writable
def branch_button(context: xnano.Context) -> Paragraph:
    """The checked out branch: a button that opens the branch menu."""
    arrow = "▴" if app.is_menu_open else "▾"
    return text_line([TextSpan(f" ⑂ {app.branch} {arrow} ", style=SELECTED)])


@xnano.writable
def branch_menu(context: xnano.Context) -> ItemList:
    """The branches to switch to, with the one under the cursor highlighted."""
    items = [("● " if branch == app.branch else "  ") + branch for branch in BRANCHES]
    return ItemList(
        items,
        selected=app.menu_index,
        highlight_style=SELECTED,
        block=Block(
            " switch branch ", border_type="rounded", border_style=DIM, title_style=BOLD
        ),
        width=24,
        height=len(BRANCHES) + 2,
    )


with xnano.open(title="xnano · git", mouse=True) as terminal:
    screen = terminal.screen
    # the top bar: the repository, its branch, a toolbar and a search field
    name = [TextSpan("◆ ", style=Style(LANES[0])), TextSpan("xnano", style=BOLD)]
    screen.write(text_line(name), x=1, y=0)
    button = screen.write(branch_button, x=10, y=0)
    tools = (("↓", "Pull"), ("↑", "Push"), ("+", "Branch"), ("≡", "Stash"))
    toolbar = [
        span
        for icon, label in tools
        for span in (
            TextSpan(f"{icon} ", style=Style(LANES[1])),
            TextSpan(f"{label}  "),
        )
    ]
    screen.write(text_line(toolbar), x=23, y=0)
    screen.write("⌕ search commits    ", x=60, y=0, dim=True, underline=True)
    # the three panels, and what is inside them
    for title, (left, width) in PANELS.items():
        frame = Block(
            f" {title} ", border_type="rounded", border_style=DIM, title_style=BOLD
        )
        screen.write(frame, x=left, y=1, width=width, height=PANEL_HEIGHT)
    tree = screen.write(branch_tree, x=PANELS["branches"][0] + 2, y=2)
    graph = screen.write(commit_graph, x=PANELS["commits"][0] + 1, y=2)
    commit_details = screen.write(details, x=PANELS["commit"][0] + 1, y=2)
    menu = screen.write(branch_menu, x=10, y=1, layer=2)
    menu.is_visible = False
    # the status line
    keys = (
        ("↑↓", "move"),
        ("enter", "open"),
        ("b", "branch"),
        ("/", "search"),
        ("q", "quit"),
    )
    hints = [
        span
        for key, action in keys
        for span in (TextSpan(key, style=BOLD), TextSpan(f" {action}  ", style=DIM))
    ]
    screen.write(text_line(hints), x=1, y=23)
    screen.write("✓ working tree clean", x=59, y=23, foreground=GREEN)

    @terminal.hook(on="key")
    def navigate(context: xnano.Context) -> None:
        """Move through the commits, or through the branch menu while it is open."""
        key = context.keyboard.key
        if app.is_menu_open:
            if key in ("up", "down"):
                step = 1 if key == "down" else -1
                app.menu_index = (app.menu_index + step) % len(BRANCHES)
            elif key in ("enter", "escape", "b"):
                if key == "enter":
                    app.branch = BRANCHES[app.menu_index]
                app.is_menu_open = menu.is_visible = False
                button.refresh()
            menu.refresh()
        elif key in ("up", "down", "j", "k"):
            step = 1 if key in ("down", "j") else -1
            app.selected = min(max(app.selected + step, 0), len(COMMITS) - 1)
            graph.refresh()
            commit_details.refresh()
        elif key == "b":
            app.is_menu_open = menu.is_visible = True
            app.menu_index = BRANCHES.index(app.branch)
            menu.refresh()
            button.refresh()

    @tree.hook(on="mouse.kind == 'press'")
    def fold(context: xnano.Context) -> None:
        """Open or close the folder that was clicked."""
        if context.mouse.position is None:
            return
        row = tree.local(context.mouse.position).y
        lines = tree_lines()
        folder = lines[row][1] if 0 <= row < len(lines) else None
        if folder is not None:
            folder.is_open = not folder.is_open
            tree.refresh()

    terminal.run(stop_on="q")
