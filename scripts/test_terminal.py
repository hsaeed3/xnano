"""
Run the native terminal suite, supplying a virtual X display on headless Linux.

All Python control code uses the standard library. The terminal application and
Linux virtual display are development tools installed by ``make install-terminal``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


def main() -> int:
    """Run pytest in the project interpreter against an actual Kitty application."""
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_actual_terminal.py",
        "--actual-terminal",
        *sys.argv[1:],
    ]
    environment = os.environ.copy()
    if sys.platform == "linux" and not environment.get("DISPLAY"):
        display_runner = shutil.which("xvfb-run")
        if display_runner is None:
            sys.stderr.write(
                "Cannot run native terminal tests without a display. Install the development tools with make install-terminal, or set DISPLAY to an existing X display.\n"
            )
            return 1
        environment["LIBGL_ALWAYS_SOFTWARE"] = "1"
        command = [
            display_runner,
            "--auto-servernum",
            "--server-args=-screen 0 1280x1024x24",
            *command,
        ]
    if sys.platform not in {"darwin", "linux"}:
        sys.stderr.write(
            "Native Kitty tests require macOS or Linux. Run this target on a supported development machine or the Linux CI job.\n"
        )
        return 1
    return subprocess.run(command, env=environment, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
