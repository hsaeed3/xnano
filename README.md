<!-- markdownlint-disable-next-line MD041 -->
> [!NOTE]
> `xnano` has recently gone through a ground up rewrite that offers much more
> flexibility and performance within your terminal applications. However, as
> this is a complete rewrite of the library and it's core extensions, there is
> no backward compatibility with the previous version. You can find
> documentation and other information about `xnano`'s latest stable `v1` release
> in the [`v1` branch](https://github.com/hsaeed3/xnano/tree/v1).

<div align="center">

# **xnano**

**A fun, fast and incredibly flexible terminal UI library for Python, built on
[`ratatui`](https://ratatui.rs).**

![License](https://img.shields.io/github/license/hsaeed3/xnano)
![Python Versions](https://img.shields.io/pypi/pyversions/xnano)
[![CodSpeed](https://img.shields.io/endpoint?url=https://codspeed.io/badge.json)](https://app.codspeed.io/hsaeed3/xnano?utm_source=badge)
[![Built With Ratatui](https://ratatui.rs/built-with-ratatui/badge.svg)](https://ratatui.rs/)

[Documentation](https://xnano.hammad.app) ·
[API Reference](https://xnano.hammad.app/api-reference/) ·
[Contributing](./CONTRIBUTING.md)

</div>

---

`xnano` is a python library that aims to provide a simple, complete and flexible
framework for building terminal applications. With `xnano` you can:

- Render textual, audio and visual content in your applications.
- Add interactive functionality that responds to users at runtime.

## Quick Start

Every example below runs as written, and `q` quits it. The art and sound example
needs the `audio` extra (`pip install "xnano[audio]"`). The feature demo shows
most of what `xnano` can do: run it with `python -m xnano` (or `xnano`).

![The xnano feature demo](https://raw.githubusercontent.com/hsaeed3/xnano/main/docs/assets/readme/demo.png)

### Put content on the screen

Write text, widgets and anything else onto a terminal and position it with
numbers, percentages or words.

```python
import xnano
from xnano.widgets import Gauge

with xnano.open(width=40, height=6) as terminal:
    terminal.screen.write(
        'Hello, world!', x='center', border='rounded', padding={'horizontal': 2}
    )
    terminal.screen.write(Gauge(0.6, label='60%'), y=4, width='100%')
    terminal.run(stop_on='q')
```

### Move things with expressions

A position from `xnano.expressions` is an expression that is evaluated again on
every frame.

```python
import xnano
from xnano.expressions import ParentWidth, TimeElapsed, Width

with xnano.open(width=40, height=3) as terminal:
    ball = terminal.screen.write('●', y=1)
    ball.x = (ParentWidth - Width) * (TimeElapsed % 2 / 2)
    terminal.run(stop_on='q')
```

### React with hooks

A hook runs a function when a key, the mouse, the clock or the state changes.

```python
import xnano

with xnano.open(width=30, height=3) as terminal:
    label = terminal.screen.write('press space', x='center', y=1)

    @terminal.hook(on='key', keys='space')
    def pressed(context: xnano.Context) -> None:
        label.text = f'space at {context.clock.elapsed_seconds:.1f}s'

    terminal.run(stop_on='q')
```

### Add effects

`xnano.effect` builds a tachyonfx effect that animates how content looks.

```python
import xnano

with xnano.open(width=40, height=5) as terminal:
    title = terminal.screen.write('xnano', x='center', y='center', border='rounded')
    title.update(
        xnano.effect('effect.fade_from', foreground='black', duration_milliseconds=1500)
    )
    terminal.run(stop_on='q')
```

### Draw art and play sound

Pixel art is written as text, and notes and melodies play on the canvas. Sound
needs `pip install "xnano[audio]"`.

```python
import xnano

heart = xnano.pixel_art(
    """
    .RR.RR.
    RRRRRRR
    .RRRRR.
    ..RRR..
    ...R...
    """,
    'R=#e03040',
)

with xnano.open(width=20, height=5) as terminal:
    terminal.screen.write(heart, x='center')
    terminal.screen.write('♪ C4 E4 G4', x='center', y=4)
    if terminal.speaker.is_available:
        terminal.speaker.play('C4 E4 G4:2', instrument='bell')
    terminal.run(stop_on='q')
```

## Install

You can install `xnano` with pip using your favorite package manager.

```sh
pip install xnano
```

To run untrusted or model-written Python against a canvas with `xnano.sandbox`,
add the `monty` extra: `pip install "xnano[monty]"`.

`xnano` and its paired `xnano-core` dependency can be installed on Python 3.10+
on any of the following operating systems:

- **Linux**, x86_64 and aarch64: glibc distributions (`manylinux` wheels) and
  musl distributions such as Alpine (`musllinux` wheels). Sound playback in
  `xnano-audio` uses the system ALSA library (`libasound`). The `musllinux`
  audio wheels synthesize sound but cannot play it on a device.
- **macOS**: x86_64 (Intel) and arm64 (Apple silicon).
- **Windows**: x86_64.
- **WebAssembly** ([Pyodide](https://pyodide.org)): continuous integration
  builds and tests only the `xnano-core` wheel in Pyodide. The test imports its
  compiled module `xnano_core._xnano_core` and renders on a runtime without a
  screen. The `xnano` package itself is not built or tested for Pyodide, and
  `xnano-audio` and `xnano-image` are not built for WebAssembly.

On Linux, macOS and Windows every extension is an abi3 wheel, so one wheel per
platform covers Python 3.10 and later.

### Packages

`xnano` itself is built off of an ecosystem of several rust
([Pyo3](https://github.com/pyo3/pyo3)) based packages that provide core and
multi-modal functionality to the library:

- [xnano](./xnano/) - The main `xnano` package.
- [xnano-core](./packages/xnano-core/) - Python bindings for `xnano`s's core
  [ratatui](https://ratatui.rs) based runtime.
- [xnano-audio](./packages/xnano-audio/) - Audio playback & input support for
  `xnano` with the ability to compose audio content directly in python using
  MIDI patch instruments. (Built using [])
- [xnano-image](./packages/xnano-image/) - Image & animation loading/rendering
  support for `xnano` built on
  [ratatui-image](https://github.com/ratatui/ratatui-image). *(Including native
  support for Kitty, iTerm2, Sixel and WebP images.)*

## Documentation

Documentation with browser-runnable examples are available @
[Documentation](https://xnano.hammad.app).

## Contributing

For information on how to contribute to `xnano` or any of its sub-packages
within this repository, please see [Contributing to `xnano`](./CONTRIBUTING.md).

This repository uses a [UV](https://docs.astral.sh/uv/) &
[Cargo](https://rust-lang.org/tools/install/) workspace that can all be managed
through a set of `make` commands.

You can get started contributing to `xnano` by running the following commands:

```sh
git clone https://github.com/hsaeed3/xnano.git
cd xnano
make help

# Optionally install the development workspace.
# This first compiles all rust [crates](./crates/) and builds all python [packages](./packages/)
# for xnano's core extensions (xnano-core, xnano-audio, xnano-image).
# make install
```

## License

`xnano` is released under the [MIT License](./LICENSE).
