---
title: Installation
icon: lucide/download
---

# Installation

xnano runs on Python 3.10 to 3.14, on Linux, macOS and Windows. To install it
from [PyPI](https://pypi.org/project/xnano/), use pip:

```bash
pip install xnano
```

To add xnano to a project that uses [uv](https://docs.astral.sh/uv/), use this
command:

```bash
uv add xnano
```

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

xnano includes a demo program. The demo shows pictures, so it needs the `image`
extra. Install the extra, then start the demo:

```bash
pip install "xnano[image]"
python -m xnano
```

The demo fills the terminal window. The `xnano` command starts the same demo. To
stop it, press `q`. If you see the demo, xnano works, and you can continue to
[Your First Program](first-program.md).
