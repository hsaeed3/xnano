---
title: Installation
icon: lucide/download
---

# Installation

xnano runs on Python 3.10 and newer, on Linux, macOS and Windows. Install it
from [PyPI](https://pypi.org/project/xnano/):

```bash
pip install xnano
```

Or add it to a project with [uv](https://docs.astral.sh/uv/):

```bash
uv add xnano
```

## Optional extras

Pictures and sound come in their own packages, so the core install stays small.
Add the extra you need:

| Extra | Adds | Install |
| --- | --- | --- |
| `image` | Loading PNG, JPEG, GIF and WebP pictures, animations included | `pip install "xnano[image]"` |
| `audio` | Playing notes, melodies and audio files, and reading the microphone | `pip install "xnano[audio]"` |

Install both at once with `pip install "xnano[image,audio]"`.

Pixel art, widgets, effects and everything else come with the core package. If a
program uses an extra that isn't installed, xnano raises an `ImportError` that
names the extra to install.

Playing sound on Linux uses ALSA, which desktop distributions include. On a
computer with no audio device, `terminal.speaker.is_available` is `False`, so a
program can check it before it plays.

## Check the install

xnano comes with a demo. Run it:

```bash
python -m xnano
```

Press `q` to leave. If the demo draws, you're ready for [Your First
Program](first-program.md).
