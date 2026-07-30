"""benchmarks.test_markup

---

The text pipelines every rendered document passes through: markdown
tokenization, fenced-code highlighting and ANSI SGR decoding. All three are
``lru_cache``-backed, so each measured callable clears the cache first —
otherwise the benchmark would time a dict lookup instead of the parse.
"""

from __future__ import annotations

from xnano.utils.markup import (
    highlight_lines,
    markdown_blocks,
    markdown_lines,
    parse_ansi_lines,
)

_MARKDOWN = """# xnano report

A **bold** intro with *emphasis*, `inline code` and a [link](https://x.dev).

## Details

- first item with **bold**
- second item with `code`
- third item

> [!NOTE]
> A blockquote admonition with *emphasis*.

```python
def fib(n: int) -> int:
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
```

---

A closing paragraph long enough that the wrapping logic has something real to
lay out instead of a single short span.
"""

_MARKDOWN_WITH_IMAGE = (
    _MARKDOWN + "\n![diagram](assets/diagram.png)\n\nAfter the image.\n"
)

_SOURCE = (
    "import os\n"
    "\n"
    "class Widget:\n"
    '    """A widget."""\n'
    "    def __init__(self, name: str, count: int = 0) -> None:\n"
    "        self.name = name  # comment\n"
    "        self.count = count\n"
    "\n"
    "    def render(self) -> str:\n"
    "        return f'{self.name}: {self.count}'\n"
) * 3

_ANSI_LOG = (
    "\x1b[1;31mERROR\x1b[0m normal \x1b[38;5;208morange\x1b[0m "
    "\x1b[38;2;10;200;30mtruecolor\x1b[0m \x1b[4munderline\x1b[24m done\n"
) * 40


def _markdown_lines() -> object:
    """Tokenize a document into styled runs from a cold cache."""
    markdown_lines.cache_clear()
    return markdown_lines(_MARKDOWN)


def _markdown_blocks() -> object:
    """Split a document into text and inline-image blocks."""
    markdown_blocks.cache_clear()
    return markdown_blocks(_MARKDOWN_WITH_IMAGE)


def _highlight_lines() -> object:
    """Syntax highlight a fenced python block."""
    highlight_lines.cache_clear()
    return highlight_lines(_SOURCE, "python")


def _parse_ansi_lines() -> object:
    """Decode a stream of SGR-styled log lines."""
    parse_ansi_lines.cache_clear()
    return parse_ansi_lines(_ANSI_LOG)


def test_markdown_lines(benchmark) -> None:
    """The dominant cost of any markdown render or ``Text(markdown=True)``."""
    lines = benchmark(_markdown_lines)
    assert len(lines) > 4
    assert any(run.modifiers == ("bold",) for line in lines for run in line)


def test_markdown_blocks(benchmark) -> None:
    """The document model the interactive markdown viewer builds."""
    blocks = benchmark(_markdown_blocks)
    assert any(block[0] == "image" for block in blocks)


def test_highlight_lines(benchmark) -> None:
    """Pygments highlighting — the priciest markup path in the library."""
    lines = benchmark(_highlight_lines)
    assert len(lines) == _SOURCE.count("\n")


def test_parse_ansi_lines(benchmark) -> None:
    """The SGR state machine, including 256-color and truecolor escapes."""
    lines = benchmark(_parse_ansi_lines)
    assert len(lines) == 41
    assert lines[0][0].modifiers == ("bold",)
