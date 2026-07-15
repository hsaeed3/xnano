#!/usr/bin/env python3
"""scripts.generate_hook_demos

---

Generate fitted light/dark GIFs for docs/hooks.
"""

from __future__ import annotations

import argparse
import collections.abc
import pathlib
import sys

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "docs" / "assets" / "hooks"
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from vhs_docs import (  # noqa: E402
    THEMES,
    Demo,
    ThemeKey,
    code,
    demo_map,
    record_demo,
    require_vhs,
    run_embedded_code,
)


def build_action_demo(
    *,
    name: str,
    title: str,
    decorator_import: str,
    decorator: str,
    action: str,
    before: str,
    after: str,
) -> Demo:
    """Build a hook demo driven by a synthetic action.

    Args:
        name: Output filename stem.
        title: Border title shown in the recording.
        decorator_import: Hook imported from ``xnano.events``.
        decorator: Decorator expression placed on the handler.
        action: ``Action`` factory expression performed by the terminal.
        before: Message shown before dispatch.
        after: Message assigned by the handler.

    Returns:
        A fitted offscreen demo.
    """
    hook_import = (
        f"from xnano.events import {decorator_import}"
        if decorator_import
        else ""
    )
    return Demo(
        name=name,
        code=code(f"""
            import time
            from xnano import Action, BaseGrid, Field, Terminal, on_action
            {hook_import}

            TRIGGER = {action}

            class Example(
                BaseGrid,
                border="rounded",
                title=" {title} ",
                padding=1,
            ):
                message: str = Field(
                    default="{before}",
                    height=1,
                    align="center",
                    color="slate-400",
                )

                {decorator}
                def handle_trigger(self) -> None:
                    self.message = "{after}"

            example = Example()
            terminal = Terminal.offscreen(cols=52, rows=7)
            try:
                terminal.render(example)
                terminal.perform(TRIGGER)
                terminal.render(example)
                print(terminal.get_output_as_ansi())
                time.sleep(3)
            finally:
                terminal.__exit__(None, None, None)
        """),
        launch_delay="800ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=7,
        content_columns=52,
    )


def build_render_demo(
    *,
    name: str,
    title: str,
    message: str,
    detail: str,
) -> Demo:
    """Build a rendered result demo for a lifecycle or web hook.

    Args:
        name: Output filename stem.
        title: Border title shown in the recording.
        message: Primary result line.
        detail: Secondary explanatory line.

    Returns:
        A fitted offscreen demo.
    """
    return Demo(
        name=name,
        code=code(f"""
            import time
            from xnano import BaseGrid, Field, Terminal

            class Example(
                BaseGrid,
                direction="vertical",
                border="rounded",
                title=" {title} ",
                padding=1,
            ):
                message: str = Field(
                    default="{message}",
                    height=1,
                    align="center",
                    color="violet-400",
                )
                detail: str = Field(
                    default="{detail}",
                    height=1,
                    align="center",
                    color="slate-400",
                )

            Terminal(height=7).render(Example())
            time.sleep(3)
        """),
        launch_delay="800ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=7,
        content_columns=52,
    )


DEMOS: tuple[Demo, ...] = (
    Demo(
        name="overview",
        code=code("""
            import time
            from xnano import Action, BaseGrid, Field, Terminal, on_action

            OPEN = Action.keyboard("enter")

            class Notice(
                BaseGrid,
                border="rounded",
                title=" Hooks & Actions ",
                padding=1,
            ):
                message: str = Field(
                    default="waiting for OPEN",
                    height=1,
                    align="center",
                    color="slate-400",
                )
                detail: str = Field(
                    default="one trigger · one dispatch path",
                    height=1,
                    align="center",
                    color="violet-400",
                )

                @on_action(OPEN)
                def open_notice(self) -> None:
                    self.message = "OPEN performed"

            notice = Notice()
            terminal = Terminal.offscreen(cols=52, rows=8)
            try:
                terminal.render(notice)
                terminal.perform(OPEN)
                terminal.render(notice)
                print(terminal.get_output_as_ansi())
                time.sleep(3)
            finally:
                terminal.__exit__(None, None, None)
        """),
        launch_delay="800ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=8,
        content_columns=52,
    ),
    build_action_demo(
        name="action",
        title="@on_action",
        decorator_import="",
        decorator="@on_action(TRIGGER)",
        action='Action.keyboard("ctrl+s")',
        before="unsaved",
        after="SAVE performed · document saved",
    ),
    build_action_demo(
        name="event",
        title="@on_event",
        decorator_import="on_event",
        decorator="@on_event",
        action='Action.keyboard("enter")',
        before="waiting for any event",
        after="keyboard event observed",
    ),
    build_action_demo(
        name="keyboard",
        title="@on_keyboard",
        decorator_import="on_keyboard",
        decorator='@on_keyboard("enter")',
        action='Action.keyboard("enter")',
        before="press enter",
        after="enter pressed",
    ),
    build_action_demo(
        name="mouse",
        title="@on_mouse",
        decorator_import="on_mouse",
        decorator='@on_mouse("right", kind="press")',
        action='Action.mouse("right", kind="press")',
        before="right click for menu",
        after="context menu opened",
    ),
    build_action_demo(
        name="click",
        title="@on_click",
        decorator_import="on_click",
        decorator='@on_click("message")',
        action='Action.click("message")',
        before="click to confirm",
        after="confirmed",
    ),
    build_action_demo(
        name="tick",
        title="@on_tick",
        decorator_import="on_tick",
        decorator="@on_tick(1000)",
        action="Action.tick(1000)",
        before="waiting for the clock",
        after="one-second tick received",
    ),
    build_action_demo(
        name="resize",
        title="@on_resize",
        decorator_import="on_resize",
        decorator="@on_resize",
        action="Action.resize(width=40, height=12)",
        before="wide layout",
        after="40 × 12 · compact layout",
    ),
    build_action_demo(
        name="clipboard",
        title="@on_clipboard",
        decorator_import="on_clipboard",
        decorator="@on_clipboard",
        action='Action.clipboard("hello")',
        before="paste something",
        after="pasted · hello",
    ),
    build_action_demo(
        name="focus",
        title="@on_focus",
        decorator_import="on_focus",
        decorator='@on_focus(kind="gained")',
        action='Action.focus(kind="gained")',
        before="window unfocused",
        after="window focus gained",
    ),
    build_render_demo(
        name="poll",
        title="@on_poll",
        message="3 frames polled",
        detail="frame hooks run with the host cycle",
    ),
    build_render_demo(
        name="state",
        title="@on_state",
        message="is_loading → Loading…",
        detail="shared state observed across grids",
    ),
    build_render_demo(
        name="field",
        title="@on_field",
        message="total > 0 → Checkout ready",
        detail="grid field condition matched",
    ),
    build_render_demo(
        name="web-requests",
        title="Web Request Hooks · Experimental",
        message="GET reads · POST mutates",
        detail="routes render a page or htmx fragment",
    ),
    build_render_demo(
        name="get-request",
        title="@on_get_request · Experimental",
        message="GET /status → Everything is healthy",
        detail="live session grid rendered",
    ),
    build_render_demo(
        name="post-request",
        title="@on_post_request · Experimental",
        message="POST /increment → Count: 1",
        detail="htmx swaps #xnano-app",
    ),
)

_DEMO_MAP = demo_map(DEMOS)


def generate_demo(
    demo: Demo,
    theme: ThemeKey,
    *,
    vhs: str,
    dry_run: bool,
    quiet: bool,
) -> None:
    """Record one hook demo for a single theme.

    Args:
        demo: Demo to record.
        theme: Documentation theme to apply.
        vhs: Resolved VHS executable.
        dry_run: Print the tape without recording it.
        quiet: Suppress VHS output.
    """
    output = OUTPUT_DIRECTORY / f"{demo.name}-{theme}.gif"
    launch = (
        "uv run python scripts/generate_hook_demos.py "
        f"--run-example {demo.name}"
    )
    record_demo(
        demo,
        output=output,
        theme=theme,
        launch_command=launch,
        vhs=vhs,
        dry_run=dry_run,
        quiet=quiet,
        tape_label="hook",
    )


def parse_arguments(
    arguments: collections.abc.Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        arguments: Optional argument sequence.

    Returns:
        Parsed command-line namespace.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demo",
        choices=list(_DEMO_MAP),
        action="append",
        help="Record only the named demo (repeatable)",
    )
    parser.add_argument(
        "--theme",
        choices=list(THEMES),
        help="Record one theme only (default: both)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print tape files without recording",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Pass --quiet to VHS",
    )
    parser.add_argument(
        "--run-example",
        choices=list(_DEMO_MAP),
        help=argparse.SUPPRESS,
    )
    return parser.parse_args(arguments)


def run_generator(
    arguments: collections.abc.Sequence[str] | None = None,
) -> int:
    """Generate the selected hook demos.

    Args:
        arguments: Optional command-line arguments.

    Returns:
        Process exit code.
    """
    parsed = parse_arguments(arguments)
    if parsed.run_example:
        run_embedded_code(_DEMO_MAP[parsed.run_example], label="hook")
        return 0

    selected = (
        [_DEMO_MAP[name] for name in parsed.demo]
        if parsed.demo
        else list(DEMOS)
    )
    themes: tuple[ThemeKey, ...] = (parsed.theme,) if parsed.theme else THEMES
    vhs = "" if parsed.dry_run else require_vhs()
    for demo in selected:
        for theme in themes:
            generate_demo(
                demo,
                theme,
                vhs=vhs,
                dry_run=parsed.dry_run,
                quiet=parsed.quiet,
            )

    if not parsed.dry_run:
        total = len(selected) * len(themes)
        relative_output = OUTPUT_DIRECTORY.relative_to(REPOSITORY_ROOT)
        print(f"\nDone — {total} GIF(s) in {relative_output}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_generator())
