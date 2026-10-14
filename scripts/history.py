#!/usr/bin/env python3
"""
Build ``HISTORY.md`` from the GitHub release notes of every xnano package.

Each release is published by the CI workflow with notes that GitHub generates from the
pull requests and labels described in ``.github/release.yml``. This script reads those
notes with the GitHub command line (``gh``), groups them by package (the part of the tag
before the ``/``), and writes them newest first. Nothing in ``HISTORY.md`` is written by hand.

Run ``make history`` from the repository root after a release is published. It needs ``gh``
to be installed and signed in.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "HISTORY.md"
PACKAGES = ("xnano", "xnano-core", "xnano-audio", "xnano-image")
GENERATED_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
HEADING = re.compile(r"^(#{1,5}) ", re.MULTILINE)
FULL_CHANGELOG = re.compile(r"^\*\*Full Changelog\*\*:.*$", re.MULTILINE)


class HistoryError(RuntimeError):
    """The release notes could not be read or written."""


def read_releases() -> list[dict[str, object]]:
    """Return every published release of the repository, as the GitHub API describes them."""
    command = [
        "gh",
        "api",
        "--paginate",
        "--slurp",
        "repos/{owner}/{repo}/releases?per_page=100",
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, check=True, cwd=ROOT
        )
    except FileNotFoundError:
        raise HistoryError(
            "The GitHub command line (gh) is not installed. Install it from "
            "https://cli.github.com and run `gh auth login`, then run this script again."
        ) from None
    except subprocess.CalledProcessError as error:
        raise HistoryError(
            f"gh could not read the releases: {error.stderr.strip() or error.stdout.strip()}. "
            "Run `gh auth login` and check that this directory is a clone of the repository."
        ) from None
    pages: list[list[dict[str, object]]] = json.loads(completed.stdout)
    return [release for page in pages for release in page if not release["draft"]]


def package_of(tag: str) -> str | None:
    """The package a tag such as ``xnano-core/v2.0.0-beta.2`` belongs to."""
    package, separator, _version = tag.partition("/")
    return package if separator and package in PACKAGES else None


def clean_notes(body: str) -> str:
    """The notes without GitHub's generated comment and changelog link, headings lowered."""
    text = GENERATED_COMMENT.sub("", body.replace("\r\n", "\n"))
    text = FULL_CHANGELOG.sub("", text)
    text = HEADING.sub(lambda match: f"{match.group(1)}### ", text)
    return text.strip()


def render(releases: list[dict[str, object]]) -> str:
    """The text of ``HISTORY.md`` for these releases."""
    by_package: dict[str, list[dict[str, object]]] = {name: [] for name in PACKAGES}
    for release in releases:
        package = package_of(str(release["tag_name"]))
        if package is not None:
            by_package[package].append(release)
    lines = [
        "# History",
        "",
        "Release notes of every xnano package, newest first. This file is generated from the "
        "GitHub releases by `scripts/history.py` (run `make history`); do not edit it by hand.",
        "",
    ]
    for package in PACKAGES:
        entries = sorted(
            by_package[package],
            key=lambda release: str(release["published_at"]),
            reverse=True,
        )
        if not entries:
            continue
        lines += [f"## {package}", ""]
        for release in entries:
            tag = str(release["tag_name"])
            published = datetime.datetime.fromisoformat(
                str(release["published_at"]).replace("Z", "+00:00")
            ).date()
            version = tag.partition("/")[2].removeprefix("v")
            kind = " (pre-release)" if release["prerelease"] else ""
            lines += [
                f"### {version}{kind}",
                "",
                f"Published {published.isoformat()}. [Release page]({release['html_url']}).",
                "",
            ]
            notes = clean_notes(str(release["body"] or ""))
            if notes:
                lines += [notes, ""]
    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    """Write ``HISTORY.md``, or with ``--check`` fail when it is out of date."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit with an error when HISTORY.md differs from the release notes",
    )
    arguments = parser.parse_args()
    try:
        text = render(read_releases())
    except HistoryError as error:
        sys.stderr.write(f"error: {error}\n")
        return 1
    if arguments.check:
        if not HISTORY.is_file() or HISTORY.read_text(encoding="utf-8") != text:
            sys.stderr.write("error: HISTORY.md is out of date; run `make history`.\n")
            return 1
        sys.stdout.write("HISTORY.md matches the release notes.\n")
        return 0
    HISTORY.write_text(text, encoding="utf-8")
    sys.stdout.write(f"Wrote {HISTORY.relative_to(ROOT)}.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
