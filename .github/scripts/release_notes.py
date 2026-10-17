# /// script
# requires-python = ">=3.11"
# dependencies = ["packaging>=24.0"]
# ///
"""
Write the release notes of one release tag, for the ``Release`` jobs of ``.github/workflows/ci.yml``.

Usage: ``release_notes.py <tag> <output file>``, for example
``release_notes.py xnano-core/v2.0.0-beta.4 release-notes.md``. It runs from a full clone
(every commit and tag) and reads pull requests with the GitHub command line (``gh``), which
needs ``GH_TOKEN`` in CI.

The notes of a package are written in the descriptions of the pull requests merged since the
previous release of that package, between two markers::

    <!-- release-notes: xnano-core -->
    # xnano-core 2.0.0-beta.4

    - What changed, for users of the package.
    <!-- /release-notes -->

One pull request may hold a block for each package it changes, and the blocks of every pull
request in the range are joined, oldest first. When no pull request in the range has a block
for the package, the notes are the ones GitHub generates from the pull request titles and the
categories of ``.github/release.yml``. Either way, they end with a link that compares the tag
with the previous release of the same package, not with the newest tag of any package.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from packaging.version import InvalidVersion, Version

PACKAGES = ("xnano", "xnano-core", "xnano-audio", "xnano-image")
TAG_PATTERN = re.compile(r"^(" + "|".join(PACKAGES) + r")/v?(.+)$")
PULL_REQUEST_NUMBER = re.compile(r"\(#(\d+)\)\s*$")
NOTES_BLOCK = re.compile(
    r"<!--\s*release-notes:\s*(?P<package>[a-z-]+)\s*-->(?P<notes>.*?)<!--\s*/release-notes\s*-->",
    re.DOTALL | re.IGNORECASE,
)


class ReleaseNotesError(Exception):
    """A problem the person publishing the release can fix."""


def run(command: list[str]) -> str:
    """Run a command and return its output, explaining a failure."""
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        raise ReleaseNotesError(f"{command[0]} is not installed.") from None
    except subprocess.CalledProcessError as error:
        raise ReleaseNotesError(
            f"{' '.join(command)} failed: {error.stderr.strip() or error.stdout.strip()}"
        ) from None
    return completed.stdout


def parse_tag(tag: str) -> tuple[str, Version]:
    """The package and version of a release tag such as ``xnano-core/v2.0.0-beta.4``."""
    match = TAG_PATTERN.match(tag)
    if match is None:
        raise ReleaseNotesError(
            f'"{tag}" is not a release tag. Release tags look like "<package>/v<version>", '
            f"where <package> is one of: {', '.join(PACKAGES)}."
        )
    package, text = match.groups()
    try:
        return package, Version(text)
    except InvalidVersion:
        raise ReleaseNotesError(
            f'The tag "{tag}" has the version "{text}", which is not a PEP 440 version.'
        ) from None


def previous_tag(tag: str, tags: list[str]) -> str | None:
    """The newest release tag of the same package with a lower version than ``tag``."""
    package, version = parse_tag(tag)
    candidates: list[tuple[Version, str]] = []
    for other in tags:
        match = TAG_PATTERN.match(other)
        if match is None or match.group(1) != package:
            continue
        try:
            other_version = Version(match.group(2))
        except InvalidVersion:
            continue
        if other_version < version:
            candidates.append((other_version, other))
    return max(candidates)[1] if candidates else None


def pull_request_numbers(subjects: list[str]) -> list[int]:
    """The pull requests of squash-merge commit subjects such as ``fix: x (#12)``, in order."""
    numbers: list[int] = []
    for subject in subjects:
        match = PULL_REQUEST_NUMBER.search(subject)
        if match is not None and int(match.group(1)) not in numbers:
            numbers.append(int(match.group(1)))
    return numbers


def notes_blocks(body: str, package: str) -> list[str]:
    """The release-note blocks of ``package`` in one pull request description."""
    text = body.replace("\r\n", "\n")
    return [
        match.group("notes").strip()
        for match in NOTES_BLOCK.finditer(text)
        if match.group("package").lower() == package and match.group("notes").strip()
    ]


def compare_link(repository: str, previous: str | None, tag: str) -> str:
    """The "Full Changelog" line that compares ``tag`` with the package's previous release."""
    if previous is None:
        return f"**Full Changelog**: https://github.com/{repository}/commits/{tag}"
    return f"**Full Changelog**: https://github.com/{repository}/compare/{previous}...{tag}"


def generated_notes(repository: str, tag: str, previous: str | None) -> str:
    """The notes GitHub generates from pull request titles and ``.github/release.yml``."""
    command = [
        "gh",
        "api",
        "--method",
        "POST",
        f"repos/{repository}/releases/generate-notes",
        "-f",
        f"tag_name={tag}",
    ]
    if previous is not None:
        command += ["-f", f"previous_tag_name={previous}"]
    body = json.loads(run(command))["body"]
    # GitHub's own changelog line is replaced by one that compares with the same package.
    return re.sub(r"^\*\*Full Changelog\*\*:.*$", "", body, flags=re.MULTILINE).strip()


def build_notes(tag: str, repository: str) -> str:
    """The release notes of ``tag``."""
    package, _version = parse_tag(tag)
    tags = run(["git", "tag", "--list"]).split()
    previous = previous_tag(tag, tags)
    revision_range = f"{previous}..{tag}" if previous else tag
    subjects = run(
        ["git", "log", "--reverse", "--format=%s", revision_range]
    ).splitlines()
    blocks: list[str] = []
    for number in pull_request_numbers(subjects):
        pull_request = json.loads(
            run(["gh", "api", f"repos/{repository}/pulls/{number}"])
        )
        blocks.extend(notes_blocks(pull_request.get("body") or "", package))
    notes = (
        "\n\n".join(blocks) if blocks else generated_notes(repository, tag, previous)
    )
    return f"{notes}\n\n{compare_link(repository, previous, tag)}\n".lstrip("\n")


def main(argv: list[str] | None = None) -> int:
    """Write the notes of the tag in ``argv`` to the file in ``argv``."""
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 2:
        sys.stderr.write("usage: release_notes.py <tag> <output file>\n")
        return 2
    tag, output = arguments
    try:
        repository = (
            os.environ.get("GITHUB_REPOSITORY")
            or run(
                [
                    "gh",
                    "repo",
                    "view",
                    "--json",
                    "nameWithOwner",
                    "--jq",
                    ".nameWithOwner",
                ]
            ).strip()
        )
        notes = build_notes(tag, repository)
    except ReleaseNotesError as error:
        sys.stderr.write(f"::error::{error}\n")
        return 1
    Path(output).write_text(notes, encoding="utf-8")
    sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
