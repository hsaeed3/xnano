"""tests.benchmarks.test_options_performance

---

Track large dynamic option-list filtering and rendering.
"""

import sys
from typing import Any

from xnano.components.component import ComponentRenderContext
from xnano.components.options import Option, Options
from xnano.core.content import Items
from xnano.core.runtime import Runtime
from xnano.types import Area

_ITEMS = tuple(
    Option(label=f"model-{index:04d}", value=index) for index in range(3_000)
)
# Python 3.10's typing sets __orig_class__ on the instance after __init__,
# which frozen dataclasses reject; skip the subscript there.
if sys.version_info < (3, 11):
    _CONTEXT = ComponentRenderContext(area=Area(x=0, y=0, width=80, height=24))
else:
    _CONTEXT = ComponentRenderContext[Any](
        area=Area(x=0, y=0, width=80, height=24)
    )


def test_bench_options_compose_visible_window(benchmark) -> None:
    """Measure composing a terminal-sized window from 3,000 options."""
    options = Options(items=_ITEMS, selected=1_500)
    content = benchmark(options.compose, _CONTEXT)
    assert isinstance(content, Items)
    assert len(content.items) == 24


def test_bench_options_fuzzy_filter(benchmark) -> None:
    """Measure fuzzy searching the complete 3,000-option data set."""
    options = Options(items=_ITEMS, query="m299")
    visible = benchmark(lambda: options.visible_items)
    assert visible


def test_bench_options_runtime_render(benchmark) -> None:
    """Measure public rendering and frame serialization at SSH dimensions."""
    options = Options(items=_ITEMS, searchable=True, selected=1_500)
    runtime = Runtime.offscreen(width=80, height=24)
    runtime.set_root(options)
    try:
        frame = benchmark(runtime.render)
        assert frame.width == 80
        assert frame.height == 24
    finally:
        runtime.close()


def test_bench_options_dynamic_replacement(benchmark) -> None:
    """Measure a gateway update followed by a complete terminal render."""
    options = Options(items=_ITEMS, selected=1_500)
    updated = tuple(
        Option(label=f"gateway-{index:04d}", value=index)
        for index in range(3_000)
    )
    runtime = Runtime.offscreen(width=80, height=24)
    runtime.set_root(options)
    source = _ITEMS

    def replace_and_render() -> None:
        nonlocal source
        source = updated if source is _ITEMS else _ITEMS
        selected = options.selected_value
        options.items = source
        options.select_value(selected)
        runtime.render()

    try:
        benchmark(replace_and_render)
        assert options.selected_value == 1_500
    finally:
        runtime.close()
