# xnano-core

The compiled Rust engine for building terminal interfaces: buffers, widgets, layout, effects, state management, and a live runtime.

## Install

```bash
pip install xnano-core
```

Most people install the top-level `xnano` package instead, which adds the terminal API (`xnano.iter()`, placements, hooks, scenes and sound) on top of this engine:

```bash
pip install xnano
```

For v1 of xnano (a different API), install `xnano>=1.2.3,<2`.

## Example

```python
from xnano_core import Point, Size, Style, Color, Clock

# Basic geometry
point = Point(2, 3) + Point(1, 1)
assert (point.x, point.y) == (3, 4)

# Styles combine colors and text attributes
style = Style('red', 'black', bold=True)
assert 'bold' in style.modifiers

# Clocks can be real or manually advanced for testing
clock = Clock.manual(elapsed_seconds=2.0)
assert clock.elapsed_milliseconds == 2000.0
```

## What it provides

- **Cell buffers**: mutable 2D arrays of terminal cells with styles, colors and text attributes
- **Widgets**: built-in composable pieces like blocks, tables, gauges, charts, calendars and text editors
- **Operations**: animations, effects, transitions, and state mutations on the fly
- **Expression language**: scalar expressions that react to state changes and user input
- **Input**: keyboard and mouse events with key bindings and focus management
- **State management**: declarative state schema with validation, patches, and observations
- **Runtime**: offscreen and live terminal execution with event loops and frame timing

## Links

- **Repository**: https://github.com/hsaeed3/xnano
- **Documentation**: https://xnano.hammad.app
- **API reference**: https://xnano.hammad.app/api-reference/
- **License**: MIT
