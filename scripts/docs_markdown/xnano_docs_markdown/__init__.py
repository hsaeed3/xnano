"""
Code block comments for the xnano documentation.

Lines of a code block are marked with ``# >> [name]``, and a ``<comments>`` element written
right after the block explains them::

    ```python
    picture = xnano.load_image('dusk.png')  # >> [image]
    ```

    <comments>
    <definition term="load_image" kind="function">Reads PNG, JPEG, GIF and WebP files.</definition>

    <tag name="image" color="pink">
    Loads the picture. Any **markdown** works in here.

    <definition term="load_image">Reads `dusk.png` for this example.</definition>
    </tag>
    </comments>

The homepage's examples are written the same way, in ``docs/index.md``. Each ``<feature>``
becomes one example, in the order written, with its markdown as the text beside the
animation; ``figure`` puts the animation on the ``left`` or the ``right``, and ``light`` and
``dark`` name the files shown in each color scheme (``dark`` defaults to ``light``, and
``alt`` to the title)::

    <features>
    <feature title="Sound" figure="left" light="assets/home/sound-light.gif" dark="assets/home/sound-dark.gif">
    Notes are plain values, played by [the speaker](learn/index.md).
    </feature>
    </features>

Python Markdown treats elements it does not know as text inside a paragraph, which breaks
their nesting. This extension reads these elements as blocks whose contents are markdown
instead, so they reach the page whole: the page's script, ``docs/js/code-notes.js``, turns
comments into notes on the code, and the homepage's examples are laid out here. Enable it
next to ``md_in_html``, which it builds on and loads itself when it is missing::

    [project.markdown_extensions]
    md_in_html = {}
    xnano_docs_markdown = {}
"""

from __future__ import annotations

import re
import textwrap
import xml.etree.ElementTree as etree

from markdown import Extension, Markdown
from markdown.preprocessors import Preprocessor
from markdown.treeprocessors import Treeprocessor

ELEMENTS = ("comments", "tag", "definition", "features", "feature")
"""The elements whose contents are read as markdown."""

OPENING_TAG = re.compile(
    rf"^(?P<indent> {{0,3}})<(?P<name>{'|'.join(ELEMENTS)})(?P<attributes>(?:\s[^>]*)?)>"
)
MARKDOWN_ATTRIBUTE = re.compile(r"\smarkdown\s*=")


class MarkdownInComments(Preprocessor):
    """
    Prepare every ``<comments>``, ``<tag>`` and ``<definition>`` for ``md_in_html``.

    Each opening tag gets a markdown attribute, and the lines inside each element lose
    their shared indentation, so content indented for readability is read as text rather
    than as an indented code block.
    """

    def run(self, lines: list[str]) -> list[str]:
        """Return the lines with each element marked and its contents dedented."""
        result: list[str] = []
        index = 0
        while index < len(lines):
            match = OPENING_TAG.match(lines[index])
            if match is None:
                result.append(lines[index])
                index += 1
                continue
            name = match["name"]
            rest = lines[index][match.end() :]
            result.append(self.mark(match) + rest)
            end = None if f"</{name}>" in rest else closing_line(lines, index, name)
            if end is None:
                index += 1
                continue
            inner = lines[index + 1 : end]
            before, closing, after = lines[end].partition(f"</{name}>")
            if before.strip():
                inner.append(before)
            result.extend(self.run(textwrap.dedent("\n".join(inner)).split("\n")))
            result.append(closing + after)
            index = end + 1
        return result

    @staticmethod
    def mark(match: re.Match[str]) -> str:
        """Add ``markdown="1"`` to one opening tag, unless it already has the attribute."""
        attributes = match["attributes"]
        if MARKDOWN_ATTRIBUTE.search(attributes):
            return match[0]
        return f'{match["indent"]}<{match["name"]}{attributes} markdown="1">'


def closing_line(lines: list[str], start: int, name: str) -> int | None:
    """Return the line that closes the element opened on ``start``, or None if none does."""
    depth = 1
    opening = re.compile(rf"^\s*<{name}(?:\s|>)")
    for index in range(start + 1, len(lines)):
        if opening.match(lines[index]) and f"</{name}>" not in lines[index]:
            depth += 1
        elif f"</{name}>" in lines[index]:
            depth -= 1
            if depth == 0:
                return index
    return None


class FeaturesTreeprocessor(Treeprocessor):
    """Lay out each ``<feature>`` of a ``<features>`` element as one of the homepage's examples."""

    def run(self, root: etree.Element) -> None:
        """Rewrite every ``<features>`` element in place."""
        for features in root.iter("features"):
            features.tag = "xn-features"
            features.attrib.clear()
            for feature in features.findall("feature"):
                self.lay_out(feature)

    @staticmethod
    def lay_out(feature: etree.Element) -> None:
        """Turn one ``<feature>`` into a title, its text, and its animation."""
        title = feature.get("title", "")
        light = feature.get("light", "")
        dark = feature.get("dark") or light
        alternative = feature.get("alt") or title
        is_figure_left = feature.get("figure", "right").strip().lower() == "left"
        text = etree.Element("div", {"class": "xn-spread__text"})
        text.text = feature.text
        text.extend(list(feature))
        tail = feature.tail
        feature.clear()
        feature.tag = "div"
        feature.tail = tail
        feature.set(
            "class", "xn-spread xn-spread--reverse" if is_figure_left else "xn-spread"
        )
        heading = etree.SubElement(feature, "h2", {"class": "xn-spread__word"})
        heading.text = title
        feature.append(text)
        figure = etree.SubElement(feature, "figure", {"class": "xn-spread__figure"})
        for scheme, source in (("light", light), ("dark", dark)):
            etree.SubElement(
                figure,
                "img",
                {
                    "class": f"xn-only-{scheme}",
                    "src": source,
                    "alt": alternative,
                    "loading": "lazy",
                },
            )


class CodeCommentsExtension(Extension):
    """Read ``<comments>``, ``<tag>`` and ``<definition>`` as markdown blocks."""

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802 - Python Markdown's name
        """Register the elements as blocks and mark them before raw HTML is read."""
        md.block_level_elements.extend(
            element for element in ELEMENTS if element not in md.block_level_elements
        )
        if not any(
            type(extension).__name__ == "MarkdownInHtmlExtension"
            for extension in md.registeredExtensions
        ):
            md.registerExtensions(["md_in_html"], {})
        # After fenced code is set aside (priority 25), so code is never touched, and
        # before raw HTML is read (priority 20).
        md.preprocessors.register(MarkdownInComments(md), "xnano_code_comments", 22)
        # After the table of contents (priority 5), so the examples' titles stay out of it.
        md.treeprocessors.register(FeaturesTreeprocessor(md), "xnano_features", 4)


def makeExtension(**configuration: object) -> CodeCommentsExtension:  # noqa: N802
    """Return the extension; Python Markdown calls this to load it by module name."""
    return CodeCommentsExtension(**configuration)
