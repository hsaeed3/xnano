#!/usr/bin/env python3
"""scripts.run_vhs_demo

---

Run a named concept demo script for VHS recordings.
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from generate_component_demos import (
    _DEMO_MAP as _COMPONENT_DEMO_MAP,  # noqa: E402
)
from generate_concept_demos import _DEMO_MAP as _CONCEPT_DEMO_MAP  # noqa: E402


_DEMO_MAP = {**_CONCEPT_DEMO_MAP, **_COMPONENT_DEMO_MAP}


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) != 1:
        print("usage: run_vhs_demo.py <demo-name>", file=sys.stderr)
        return 2

    name = args[0]
    if name not in _DEMO_MAP:
        print(f"unknown demo: {name}", file=sys.stderr)
        return 2

    code = _DEMO_MAP[name].code
    exec(compile(code, f"<vhs-demo:{name}>", "exec"), {"__name__": "__main__"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
