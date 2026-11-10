---
title: Installation
icon: lucide/download
---

# Installation

To install xnano from [PyPI](https://pypi.org/project/xnano/), use pip:

```bash
pip install xnano
```

To add xnano to a project that uses [uv](https://docs.astral.sh/uv/), use this
command:

```bash
uv add xnano
```

## Supported platforms

- **Python**: 3.10 to 3.14.
- **Linux**: x86_64 and aarch64, with glibc or musl.
- **macOS**: Intel and Apple silicon.
- **Windows**: x86_64.
- **WebAssembly**: [Pyodide](https://pyodide.org/), in a browser. A browser has
  no terminal, so a canvas from `xnano.new()` draws into memory there, and
  images and sound are not available.

Each platform has a wheel that is already built, so you do not need Rust.

## Optional extras

Images and sound are in separate packages, so the core package stays small. An
**extra** installs one of these packages together with xnano. Install only the
extras that your program uses:

| Extra | What it adds | Command |
| --- | --- | --- |
| `image` | Pictures from PNG, JPEG, GIF and WebP files, also animated pictures | `pip install "xnano[image]"` |
| `audio` | Notes, melodies, audio files and the microphone | `pip install "xnano[audio]"` |

To install the two extras together, use `pip install "xnano[image,audio]"`. In a
uv project, use `uv add "xnano[image,audio]"`.

The core package has everything else, for example pixel art, widgets, effects
and hooks. If a program uses an extra that is not installed, xnano raises an
`ImportError`. The error message gives the command that installs the extra.

On Linux, xnano plays sound through ALSA, which desktop Linux distributions
include. On a computer without a sound device, `terminal.speaker.is_available`
is `False`. If a program plays a sound on such a computer, xnano raises an
error. To prevent this error, check `is_available` before you play a sound.

## Check the installation

xnano includes a demo program. Start it:

```bash
python -m xnano
```

The demo fills the terminal window, and the `xnano` command starts the same
demo. Press a key to leave the opening screen. The left and right arrows change
the page, the up and down arrows move the choice of a page, and `q` stops the
demo. The window must have 80 columns and 24 rows or more.

The demo runs without the extras. With the `image` extra it shows pictures, and
with the `audio` extra it plays sound. If you see the demo, xnano works, and you
can continue to
[Your First Program](first-program.md).
