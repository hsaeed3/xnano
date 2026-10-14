---
title: Legacy v1
---

# xnano v1

!!! warning "These guides are for xnano v1"

    xnano v1 is no longer part of the current library. The `xnano` package on the `main`
    branch is completely v2: a terminal you put things on, with no grids or fields.
    To follow these guides, install the last v1 release:

    ```bash
    pip install "xnano>=1.2.3,<2"
    ```

    The v1 source, examples and API reference live on the
    [`v1` branch](https://github.com/hsaeed3/xnano/tree/v1), and the latest release is
    [v1.2.3](https://github.com/hsaeed3/xnano/releases/tag/xnano%2Fv1.2.3)
    ([PyPI](https://pypi.org/project/xnano/1.2.3/)).

The guides below describe the original declarative API, with `BaseGrid`, `Field`, hooks and
components. They are kept for existing applications. New applications should use the current
[API reference](../api-reference/index.md).

- [Getting started](getting-started.md)
- [Concept guide](core-concepts/overview.md)
- [Grids and fields](core-concepts/grids.md)
- [Components](core-concepts/components.md)
- [Effects](core-concepts/effects.md)
- [Events and hooks](core-concepts/events.md)
