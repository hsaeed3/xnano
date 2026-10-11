> [!IMPORTANT]
> `xnano` v2 is in beta. The redesigned Rust-backed core is available now, and the previous high-level API remains available as the opt-in `xnano.v1` module.

<div align="center">

# **xnano**

**A fun, fast and incredibly flexible terminal UI library for Python, built on [`ratatui`](https://ratatui.rs).**

![License](https://img.shields.io/github/license/hsaeed3/xnano)
![Python Versions](https://img.shields.io/pypi/pyversions/xnano)
[![CodSpeed](https://img.shields.io/endpoint?url=https://codspeed.io/badge.json)](https://app.codspeed.io/hsaeed3/xnano?utm_source=badge)
[![Built With Ratatui](https://ratatui.rs/built-with-ratatui/badge.svg)](https://ratatui.rs/)

[Documentation](https://xnano.hammad.app) · [API Reference](https://xnano.hammad.app/api-reference/) · [Contributing](./CONTRIBUTING.md)

</div>

---

## Packages

The repository is a uv workspace with three installable backends and a small `xnano` metapackage. The native packages can also be installed and used independently.

| Distribution | Import | Purpose |
| --- | --- | --- |
| [`xnano`](.) | `xnano.v1` (legacy API) | Metapackage; v1 compatibility API is opt-in. |
| [`xnano-core`](./packages/xnano-core) | `xnano._xnano_core` | Rust-backed terminal buffers, widgets, layout, state, input, runtime and effects. |
| [`xnano-audio`](./packages/xnano-audio) | `xnano_audio` | Audio synthesis, playback, capture and beat-based melodies. |
| [`xnano-image`](./packages/xnano-image) | `xnano_image` | Image and animation decoding, processing and terminal-cell conversion. |

## Install

Install the full `xnano` distribution with pip or uv:

```bash
pip install xnano
# or
uv add xnano
```

Install only a backend when you need a smaller dependency set:

```bash
pip install xnano-core
pip install xnano-audio
pip install xnano-image
```

The core package also provides `audio`, `image`, and `all` extras for installing those backends alongside `xnano-core`. On Linux, audio device playback requires ALSA; synthesis and melody scheduling work without an audio device.

## Quick start: draw without a terminal

The core API builds buffers from operations. Rendering a buffer to text is useful for scripts and tests and does not take over the terminal.

```python
from xnano._xnano_core import Border, Buffer, Write

card = Buffer(width=16, height=3)
card.update(Border('rounded'), Write('hello, xnano', x=2, y=1))
print(card.render(format='text'))
```

## Quick start: run a mounted buffer

An offscreen runtime exercises layout and frame rendering without terminal I/O. Use `Runtime.live()` when the application should own a real terminal.

```python
from xnano._xnano_core import Buffer, Runtime, Write

with Runtime.offscreen(width=20, height=3) as runtime:
    buffer = Buffer()
    runtime.mount(buffer, geometry='inherit')
    buffer.update(Write('hello from xnano'))
    runtime.step()
    print(runtime.snapshot().lines()[0])
```

The runtime also routes keyboard and mouse input, manages focus and state, and advances effects against its frame clock. See the [getting started guide](https://xnano.hammad.app/learn/) and [API reference](https://xnano.hammad.app/api-reference/).

## Audio melodies

`xnano-audio` describes notes in beats, converts them to seconds through a tempo map, and schedules notes over clock windows. This makes melody timing independent of the terminal render loop; an application can use the same monotonic clock for UI animation and audio scheduling.

```python
from xnano_audio import TerminalMelody, TerminalTempoMap

melody = (
    TerminalMelody(tempo_map=TerminalTempoMap(120))
    .appended_note('C4', duration_beats=1)
    .appended_note('G4', duration_beats=1)
)
# Query a half-second window on the same monotonic clock used by the UI.
print(melody.scheduled_between(0.0, 0.5))
```

## Images and animations

Decode an image and convert it to terminal cells with `xnano-image`:

```python
from xnano_image import TerminalImage, cell_grid_to_ansi

image = TerminalImage.open('photo.png')
print(cell_grid_to_ansi(image.to_cell_grid(40)))
```

The image package returns a portable cell-grid representation that the core can draw with its cell-grid widgets. It also supports animated formats and conversion to a cell animation.

## The v1 API

The previous declarative API remains available from `xnano.v1`; the main `xnano` package does not import it unless requested. Existing applications can migrate incrementally while new code uses the Rust-backed core.

```python
from xnano.v1 import BaseGrid, Context, Field, Terminal, on_keyboard


class Counter(BaseGrid, direction='vertical', gap=1):
    label: str = Field(default='Count: 0', height=3, border='rounded')
    count: int = Field(default=0, state=True)

    @on_keyboard('up')
    def increment(self) -> None:
        self.count += 1
        self.label = f'Count: {self.count}'

    @on_keyboard('q')
    def quit(self, context: Context) -> None:
        context.terminal.request_exit()


Terminal().run(Counter())
```

The restored legacy documentation is under [`docs/v1`](./docs/v1/). The v1 API is maintained as a compatibility layer; new core capabilities are documented in the current guides and API reference.

## Development

The repository uses a uv workspace and Rust workspace. From the repository root, `uv sync --all-extras` installs the development environment and `make help` lists common build, test, lint, type-check, docs and release commands. Read [CONTRIBUTING.md](./CONTRIBUTING.md) before opening a change.

## License

xnano is released under the [MIT License](./LICENSE).
