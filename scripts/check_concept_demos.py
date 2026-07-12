#!/usr/bin/env python3
"""scripts.check_concept_demos

---

Smoke-test every concept demo script via offscreen terminal where possible.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from generate_concept_demos import DEMOS  # noqa: E402


def _run_demo(name: str, code: str) -> tuple[str, str]:
    with tempfile.NamedTemporaryFile(
        "w", suffix=f"-{name}.py", delete=False
    ) as handle:
        handle.write(code)
        path = Path(handle.name)

    try:
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=8,
        )
        if proc.returncode == 0:
            return "OK", ""
        return f"ERR({proc.returncode})", (proc.stderr or proc.stdout)[:500]
    except subprocess.TimeoutExpired:
        return "TIMEOUT", ""
    finally:
        path.unlink(missing_ok=True)


def main() -> int:
    failed = 0
    for demo in DEMOS:
        status, detail = _run_demo(demo.name, demo.code)
        if status != "OK":
            failed += 1
        line = f"{status:8} {demo.name:22}"
        if detail:
            line += f"\n         {detail.replace(chr(10), ' | ')}"
        print(line)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
