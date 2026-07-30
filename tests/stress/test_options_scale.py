"""tests.stress.test_options_scale

---

Exercise large option lists and competing Python work.
"""

import sys
import threading

from typing import Any

from xnano.components.component import ComponentRenderContext
from xnano.components.options import Option, Options
from xnano.core.content import Items, Stack
from xnano.core.runtime import Runtime
from xnano.types import Area


def _large_items(prefix: str = "model") -> tuple[Option, ...]:
    return tuple(
        Option(label=f"{prefix}-{index:04d}", value=index)
        for index in range(3_000)
    )


def test_large_options_compose_only_the_terminal_window() -> None:
    options = Options(
        items=_large_items(),
        searchable=True,
        selected=2_999,
    )
    # Python 3.10's typing sets __orig_class__ on the instance after
    # __init__, which frozen dataclasses reject; skip the subscript there.
    if sys.version_info < (3, 11):
        context = ComponentRenderContext(
            area=Area(x=0, y=0, width=80, height=24)
        )
    else:
        context = ComponentRenderContext[Any](
            area=Area(x=0, y=0, width=80, height=24)
        )

    content = options.compose(context)

    assert isinstance(content, Stack)
    visible = content.children[1]
    assert isinstance(visible, Items)
    assert len(visible.items) == 23
    assert visible.selected == 22
    assert options.selected_value == 2_999


def test_large_options_preserve_selection_across_gateway_update() -> None:
    options = Options(items=_large_items(), selected=1_937)
    runtime = Runtime.offscreen(width=80, height=24)
    runtime.set_root(options)
    try:
        runtime.render()
        selected = options.selected_value
        options.items = _large_items("gateway")
        assert options.select_value(selected)
        frame = runtime.render()
        assert frame.height == 24
        assert options.selected_value == 1_937
    finally:
        runtime.close()


def test_large_options_render_while_python_service_is_busy() -> None:
    options = Options(items=_large_items(), selected=1_500)
    runtime = Runtime.offscreen(width=80, height=24)
    runtime.set_root(options)
    started = threading.Event()
    stopped = threading.Event()

    def run_service() -> None:
        value = 1
        started.set()
        while not stopped.is_set():
            value = (value * 1_103_515_245 + 12_345) & 0x7FFFFFFF

    worker = threading.Thread(target=run_service)
    worker.start()
    started.wait()
    try:
        for selected in (0, 750, 1_500, 2_250, 2_999):
            options.select(selected)
            frame = runtime.render()
            assert frame.height == 24
            assert options.selected_value == selected
    finally:
        stopped.set()
        worker.join()
        runtime.close()
