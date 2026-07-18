---
title: " "
icon: "lucide/smile"
---

<span class="page-index"></span>

<img src="./assets/xnano-light.png" alt="ZYX Hero" class="hero-light" align="center" style="background: transparent;" />
<img src="./assets/xnano-dark.png" alt="ZYX Hero" class="hero-dark" align="center" style="background: transparent;" />

<p align="center">
  <a href="https://pypi.org/project/xnano" target="_blank"><img src="https://img.shields.io/pypi/v/xnano.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/xnano" target="_blank"><img src="https://img.shields.io/pypi/pyversions/xnano.svg?cacheSeconds=3600" alt="Python version"></a>
  <a href="https://github.com/hsaeed3/xnano/blob/main/LICENSE" target="_blank"><img src="https://img.shields.io/github/license/hsaeed3/xnano.svg" alt="License"></a>
</p>

---

xnano is a modern TUI framework for python designed to simplify the process of putting and interacting with stuff on your terminal, built on rust.

Fast and flexible, xnano gives you a simple [Pydantic](https://github.com/pydantic/pydantic) like API for rendering to the terminal and interacting with its components in a way that plays nicely with your brain.

---

*[Pydantic]: Data validation library using Python type hints.
*[TUI]: A text-based user interface (your terminal applications).

---

<div class="xnano-showcase" markdown>
![feed monotone dark](./assets/examples/feed-dark-mono.gif){.showcase-mono .demo-dark}
![feed color dark](./assets/examples/feed-dark.gif){.showcase-color .demo-dark}
![feed monotone light](./assets/examples/feed-light-mono.gif){.showcase-mono .demo-light}
![feed color light](./assets/examples/feed-light.gif){.showcase-color .demo-light}
</div>

<div class="xnano-showcase" markdown>
![agent chat monotone dark](./assets/examples/agent_chat-dark-mono.gif){.showcase-mono .demo-dark}
![agent chat color dark](./assets/examples/agent_chat-dark.gif){.showcase-color .demo-dark}
![agent chat monotone light](./assets/examples/agent_chat-light-mono.gif){.showcase-mono .demo-light}
![agent chat color light](./assets/examples/agent_chat-light.gif){.showcase-color .demo-light}
</div>

---

## Installation

You can install xnano with your favorite package manager on python 3.10+.

=== "pip"

    ```bash title="Install with pip"
    pip install "xnano"
    ```

=== "uv"

    ```bash title="Install with uv"
    uv pip install "xnano"

    # or add to your project's dependencies
    # uv add xnano
    ```

=== "poetry"

    ```bash title="Install with poetry"
    poetry install "xnano"

    # or add to your project's dependencies
    # poetry add xnano
    ```

=== "conda"

    ```bash title="Install with conda"
    conda install "xnano"
    ```

---

## Hello World

A [grid](api/xnano/grid.md#xnano.grid.BaseGrid), a couple of [fields](../api/xnano/fields#xnano.fields.Field), some [hooks](api/xnano/events.md#xnano.events.on_event), and a [`Terminal`](api/xnano/tui/terminal.md#xnano.tui.terminal.Terminal) to run it — that's the whole shape of an xnano app.

??? example "Interactive Example"

    The following code block is interactive and can be run directly in the browser.

    ```pyodide install="xnano>=1.0.9" hl_lines="4 5"
    from xnano import BaseGrid, Field, Terminal

    class Hello(BaseGrid, direction="vertical"):
        message: str = Field(default="Hello, xnano!", color="violet", modifiers=["bold"], height=1)
        hint: str = Field(default="press q to quit", height=1, color="slate-500")

    Terminal(height=2).render(Hello())
    ```

```python title="Hello, xnano" hl_lines="5 6 9 10 13"
from xnano import BaseGrid, Field, Terminal
from xnano.context import Context
from xnano.events import on_keyboard

class Hello(BaseGrid, direction="vertical"):
    message: str = Field(default="Hello, xnano!", color="violet", modifiers=["bold"], height=1) # (1)!
    hint: str = Field(default="press q to quit", height=1, color="slate-500")

    @on_keyboard("q") # (2)!
    def quit(self, ctx: Context) -> None:
        ctx.terminal.request_exit()

Terminal().run(Hello()) # (3)!
```

1. A grid is a class; a field is a typed, styled attribute on it — this one's violet and bold.
2. A method wrapped in [`@on_keyboard`](api/xnano/events.md#xnano.events.on_keyboard) becomes a hook, fired whenever that key is pressed.
3. [`Terminal().run(...)`](api/xnano/tui/terminal.md#xnano.tui.terminal.Terminal) keeps the app alive, reading input and repainting until it exits.

<div class="xnano-demo" markdown>
![hello dark](./assets/concepts/hello_render-dark.gif){.demo-dark}
![hello light](./assets/concepts/hello_render-light.gif){.demo-light}
</div>


## Next Steps

Once you're ready to get started, try clicking on one of the following cards to explore the documentation & examples.

<br/>

<div class="grid cards" markdown>

-   :material-view-grid:{ .lg .middle } **Core Concepts**

    ---

    Start with the core concepts and components that make up the xnano, along with interactive examples to get you off the ground running.

    [Core Concepts | Grids]{.xnano-card-link}

-   :material-puzzle:{ .lg .middle } **Components**

    ---

    Explore xnano's component API, along with built-in components and how to easily define your own.

    [Components | Components]{.xnano-card-link}

-   :material-school:{ .lg .middle } **Tutorials**

    ---

    Simple step-by-step tutorials for a variety of common use cases and patterns that can be implemented with xnano.

    [Tutorials | Overview]{.xnano-card-link}

-   :material-chip:{ .lg .middle } **Core Architecture**

    ---

    For _advanced_ developers, who want a deeper undertanding of the underlying rust-based <code>xnano-core</code> library along with xnano's core architecture and event/rendering lifecycle.

    [Core Architecture | xnano-core]{.xnano-card-link}

-   :material-book-open-page-variant:{ .lg .middle } **API Reference**

    ---

    Complete API reference for the public classes, methods and other objects within the <code>xnano</code> and <code>xnano-core</code> packages.

    [API Reference | xnano]{.xnano-card-link}

</div>

[Core Concepts]: core-concepts/grids.md
[Core Concepts | Grids]: core-concepts/grids.md
[Components | Components]: components/index.md
[Tutorials | Overview]: tutorials/index.md
[Core Architecture | xnano-core]: architecture/xnano-core.md
[API Reference | xnano]: api/xnano/xnano.md
