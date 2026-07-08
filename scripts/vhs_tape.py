"""scripts.vhs_tape

---

Shared VHS tape helpers for docs demo recordings.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

SHELL_ENV_LINES: tuple[str, ...] = (
    'Env PS1 ""',
    'Env PROMPT_COMMAND ""',
    'Env HISTFILE "/dev/null"',
    'Env BASH_SILENCE_DEPRECATION_WARNING "1"',
    'Env GIT_TERMINAL_PROMPT "0"',
)
"""Suppress shell startup prompts (e.g. ``git_prompt_info``) in recordings."""


def build_run_tape(
    *,
    output: Path,
    settings: str,
    launch_command: str,
    steps: Sequence[str],
    launch_delay: str,
    record_delay: str,
    env_lines: Sequence[str] = (),
    quit_key: str = "q",
) -> str:
    """Build a VHS tape that hides shell noise and exits cleanly.

    Args:
        output: GIF output path (relative to repo root).
        settings: Pre-formatted VHS settings block.
        launch_command: Short command shown only while hidden.
        steps: Interaction steps recorded after launch.
        launch_delay: Wait after starting the app before showing.
        record_delay: Hold on the final frame before quitting.
        env_lines: Extra ``Env`` tape lines.
        quit_key: Key sent while hidden to stop interactive apps.

    Returns:
        Complete tape file contents.
    """
    lines = [
        f"Output {output.as_posix()}",
        settings,
        *SHELL_ENV_LINES,
        *env_lines,
        "Hide",
        'Type "clear"',
        "Enter",
        "Sleep 200ms",
        f'Type "{launch_command}"',
        "Enter",
        f"Sleep {launch_delay}",
        "Show",
        *steps,
        f"Sleep {record_delay}",
        "Hide",
        'Type "clear"',
        "Enter",
        f'Type "{quit_key}"',
        "Sleep 300ms",
    ]
    return "\n".join(lines) + "\n"
