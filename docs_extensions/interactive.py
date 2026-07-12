"""docs_extensions.interactive

---

Markdown extension that expands ``<interactive />`` (and a few
equivalent spellings) into the collapsible interactive-code note
from ``docs/includes/interactive.md``.
"""

from __future__ import annotations

import pathlib
import re

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

_TAG_RE = re.compile(
    r"<interactive(?:\s*/>|>\s*</interactive>)",
    re.IGNORECASE,
)

_SNIPPET_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "docs"
    / "includes"
    / "interactive.md"
)


def _load_snippet() -> str:
    return _SNIPPET_PATH.read_text(encoding="utf-8").strip() + "\n\n"


class InteractiveTagPreprocessor(Preprocessor):
    """Replace ``<interactive />`` tags with the shared snippet."""

    def run(self, lines: list[str]) -> list[str]:
        text = "\n".join(lines)
        if not _TAG_RE.search(text):
            return lines
        return _TAG_RE.sub(_load_snippet(), text).split("\n")


class InteractiveTagExtension(Extension):
    """Register the ``<interactive />`` preprocessor."""

    def extendMarkdown(self, md) -> None:
        # Run early so admonition/details see normal markdown syntax.
        md.preprocessors.register(
            InteractiveTagPreprocessor(md),
            "interactive_tag",
            175,
        )


def makeExtension(**kwargs) -> InteractiveTagExtension:
    """Python-Markdown entry point."""
    return InteractiveTagExtension(**kwargs)
