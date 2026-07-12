#!/usr/bin/env python3
"""Smoke test the xnano-core wasm wheel inside a Pyodide runtime."""

import sys


def main() -> int:
    import xnano_core

    print(f"platform: {sys.platform}")
    print(f"xnano_core: {xnano_core.__version__}")

    from xnano_core.core import (
        CoreEvent,
        CoreKeyBinding,
        CoreRenderContent,
        CoreRenderIR,
        CoreRenderNode,
        CoreSession,
        CoreTerminalEventKind,
        CoreTerminalRef,
        CoreTickEvent,
        IrLine,
    )

    imported = (
        CoreEvent,
        CoreRenderContent,
        CoreRenderIR,
        CoreRenderNode,
        CoreTerminalEventKind,
        CoreTerminalRef,
        CoreTickEvent,
        IrLine,
    )
    print(f"imported {len(imported) + 2} engine classes")

    binding = CoreKeyBinding.parse("ctrl+q")
    print(f"key binding: {binding!r}")

    # Live terminal is unavailable on wasm; buffer-backed sessions work.
    if CoreSession.supports_live_terminal():
        print("✖ supports_live_terminal should be False on wasm")
        return 1
    print("supports_live_terminal: False")

    try:
        CoreSession.init()
    except RuntimeError as error:
        print(f"CoreSession.init unavailable as expected: {error}")
    else:
        print("✖ CoreSession.init should raise RuntimeError on wasm")
        return 1

    # Buffer-backed single-frame render uses the real layout engine.
    session = CoreSession.offscreen(24, 6)
    if not session.is_buffer_backed():
        print("✖ offscreen session should be buffer-backed")
        return 1

    ir = CoreRenderIR.paragraph_raw("hello wasm")
    node = CoreRenderNode.leaf(CoreRenderContent.ir(ir))
    session.render(node)
    lines = session.buffer_snapshot().to_string_lines()
    text = "\n".join(lines)
    if "hello wasm" not in text:
        print(f"✖ expected rendered text, got: {text!r}")
        return 1
    print(f"offscreen render: {lines[0]!r}")

    session.restore()
    print("✓ wasm smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
