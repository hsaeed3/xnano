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

    try:
        CoreSession()
    except RuntimeError as error:
        print(f"CoreSession unavailable as expected: {error}")
    else:
        print("✖ CoreSession should raise RuntimeError on wasm")
        return 1

    print("✓ wasm smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
