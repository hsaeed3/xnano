---
title: "Getting Started"
---

# Getting Started

!!! note "Interactive Examples"

    Thanks to the [Pyodide](https://pyodide.org) and [markdown-exec](https://pawamoy.github.io/markdown-exec/) projects, many of the code examples within the xnano
    documentation are interactive and can be run directly in your browser.

    Try hitting the <kbd>Run</kbd> button on any code block that provides one!

## Installation

You can install xnano on Python 3.10+ using your favorite package manager.

??? abstract "WASM & MicroPython Support"

    [xnano]{data-preview} and [xnano-core]{data-preview} can both be installed on [WASM](https://webassembly.org/) and [MicroPython](https://micropython.org/) platforms, but some features <small>(such as keyboard/mouse event handling)</small> may not be available due to platform limitations.

=== "pip"

    ```bash
    pip install "xnano>=1.0.7"
    ```

=== "uv"

    ```bash
    uv pip install "xnano>=1.0.7"

    # or add to your project's dependencies
    # uv add xnano
    ```

=== "poetry"

    ```bash
    poetry install "xnano>=1.0.7"

    # or add to your project's dependencies
    # poetry add xnano
    ```

=== "conda"

    ```bash
    conda install "xnano>=1.0.7"
    ```

## What is xnano?

xnano is a very pythonic framework for building interactive user interfaces on the terminal & web browser. The library itself is
built of two rust-based dependencies:

- [xnano-core]{data-preview} - Low level terminal rendering engine built on top of [ratatui](https://ratatui.rs) and [tachyonfx](https://github.com/ratatui/tachyonfx) specifically for xnano.
- [pydantic-core](https://github.com/pydantic/pydantic-core) - The core of the [Pydantic](https://pydantic.dev/docs/validation/latest/get-started) library used for runtime type validation.

## Supported Interfaces

The core idea of xnano is to provide a unified language that can be re-used across multiple user interfaces with no extra effort. Currently, xnano supports
the following interfaces.

### Terminal

The main featureset of the library revolves around it's rust-based terminal rendering engine, [xnano-core]{data-preview}.

!!! example "Interactive Example"

    The following example is interactive and can be run directly in the browser by hitting the <kbd>Run</kbd> button.

```pyodide install="xnano>=1.0.7"
import xnano

xnano.render("hello, terminal!", color="blue")
```

### Web

Rendered content is __orthogonal__ to the host interface it is displayed on, which means everything you build and render onto the terminal within xnano can also be rendered onto a webpage with no extra effort.

!!! abstract "Web Dependencies"

    The entire layout and component system for the WebUI engine is built on top of raw [HTMX](https://htmx.org/) and [TailwindCSS](https://tailwindcss.com/), and requires no additional dependencies aside from [starlette](https://www.starlette.io/) and [uvicorn](https://www.uvicorn.org/) to serve the application.

    You can use WebUI based components by installing the following extra:

    ```bash
    pip install "xnano[web]"
    ```

```python
from xnano import Field, BaseGrid
from xnano.webui import Web

class App(BaseGrid):
    body: str = Field(default="hello, web!")

Web().run(App())
```

## Next Steps

Currently this site is still a work in progress. Complete walkthroughs and documentation for both <code>xnano</code> and <code>xnano-core</code> are coming soon.

[xnano]: ./getting-started.md
[xnano-core]: ../xnano-core/overview.md
*[pydantic-core]: Data validation library written in rust.
