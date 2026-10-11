"""
Smoke test the ``xnano-core`` WebAssembly wheel inside a Pyodide runtime.

The wasm build has no live terminal, so the test checks that the extension
imports, that a live runtime is refused, and that an offscreen runtime renders
real output into a buffer and runs scheduled calls on its manual clock.
"""

import sys


def main() -> int:
    """Verify core imports, offscreen rendering and clock callbacks in Pyodide."""
    import xnano._xnano_core as core

    sys.stdout.write(f"platform: {sys.platform}\n")
    sys.stdout.write(f"xnano._xnano_core: {core.__version__}\n")
    sys.stdout.write(f"key binding: {core.KeyBinding.parse('ctrl+q')!r}\n")

    if sys.platform == "emscripten":
        try:
            core.Runtime.live()
        except Exception as error:  # noqa: BLE001
            sys.stdout.write(f"Runtime.live is unavailable as expected: {error}\n")
        else:
            sys.stderr.write("✖ Runtime.live should raise on wasm\n")
            return 1

    with core.Runtime.offscreen(width=24, height=6) as runtime:
        buffer = core.Buffer.with_text("hello wasm")
        runtime.mount(buffer, geometry="inherit")
        runtime.step()
        lines = runtime.snapshot().lines()
        if "hello wasm" not in "\n".join(lines):
            sys.stderr.write(f"✖ expected the rendered text, got: {lines!r}\n")
            return 1
        sys.stdout.write(f"offscreen render: {lines[0]!r}\n")

        calls: list[str] = []
        runtime.call_later(0.01, lambda: calls.append("called"))
        runtime.advance_clock(10)
        runtime.step()
        if calls != ["called"]:
            sys.stderr.write(f"✖ expected the scheduled call to run, got: {calls!r}\n")
            return 1

    sys.stdout.write("✓ wasm smoke test passed\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
