"""
File picker: move through the files of a directory, and read the start of the chosen one.

The up and down arrows move the choice. ``enter`` or the right arrow opens a directory, and
``backspace`` or the left arrow goes to the directory above. The right side shows the first
lines of the chosen file, or what a directory holds. ``q`` quits.
"""

import pathlib

import xnano

VISIBLE_ROWS = 18  # the rows of the list, and of the preview
directory = pathlib.Path.cwd()
entries: list[pathlib.Path] = []
chosen = 0  # the place in `entries` of the highlighted one


def read_entries() -> None:
    """List ``directory``, directories first, and choose its first entry."""
    global entries, chosen
    try:
        found = [path for path in directory.iterdir() if not path.name.startswith('.')]
    except OSError:
        found = []
    entries = sorted(found, key=lambda path: (path.is_file(), path.name.lower()))
    chosen = 0


def preview_of(path: pathlib.Path) -> str:
    """The first lines of a file, or the names inside a directory."""
    try:
        if path.is_dir():
            names = sorted(inner.name for inner in path.iterdir())
            return '\n'.join(names[:VISIBLE_ROWS]) or 'an empty directory'
        with path.open(encoding='utf-8') as file:
            lines = [file.readline().rstrip('\n') for _ in range(VISIBLE_ROWS)]
        return '\n'.join(line.expandtabs(4)[:44] for line in lines)
    except UnicodeDecodeError:
        return 'not a text file'
    except OSError as error:
        return f'cannot be read: {error.strerror}'


with xnano.open(title='file picker') as terminal:
    location = terminal.write('', bold=True)
    names = terminal.write('', y=2, width=30, height=VISIBLE_ROWS)
    preview = terminal.write(
        '', x=32, y=1, width=48, height=VISIBLE_ROWS + 2, border='rounded', dim=True
    )
    terminal.write(
        '↑ ↓ choose · enter open · backspace up · q quit', y='bottom', dim=True
    )

    def show() -> None:
        """Draw the directory, the rows around the choice, and the preview of the choice."""
        location.text = str(directory)[-78:]
        first = max(0, min(chosen - VISIBLE_ROWS // 2, len(entries) - VISIBLE_ROWS))
        lines = []
        for index, path in enumerate(entries[first : first + VISIBLE_ROWS], first):
            name = path.name + ('/' if path.is_dir() else '')
            lines.append(('› ' if index == chosen else '  ') + name[:27])
        names.text = '\n'.join(lines) or '  nothing here'
        preview.text = preview_of(entries[chosen]) if entries else ''

    @terminal.hook(on='key', keys=['up', 'down'])
    def move_choice(context: xnano.Context) -> None:
        """Move the highlighted entry up or down, around the ends."""
        global chosen
        if entries:
            step = 1 if context.keyboard.key == 'down' else -1
            chosen = (chosen + step) % len(entries)
            show()

    @terminal.hook(on='key', keys=['enter', 'right'])
    def open_directory(context: xnano.Context) -> None:
        """Go into the highlighted entry when it is a directory."""
        global directory
        if entries and entries[chosen].is_dir():
            directory = entries[chosen]
            read_entries()
            show()

    @terminal.hook(on='key', keys=['backspace', 'left'])
    def go_up(context: xnano.Context) -> None:
        """Go to the directory above, with the one just left highlighted."""
        global directory, chosen
        below, directory = directory, directory.parent
        read_entries()
        if below in entries:
            chosen = entries.index(below)
        show()

    read_entries()
    show()
    terminal.run(stop_on='q')
