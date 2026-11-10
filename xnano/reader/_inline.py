"""
xnano.reader._inline

The text inside a line of Markdown: emphasis, code, links and images, as runs.
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Callable

from xnano.reader._lines import Run

__all__ = ['image_as_text', 'inline_runs']

INLINE = re.compile(
    r"""
      (?P<escape>\\[\\`*_{}\[\]()#+\-.!|~<>])
    | (?P<code>(?P<ticks>`+)(?P<code_text>.+?)(?<!`)(?P=ticks)(?!`))
    | (?P<image>!\[(?P<alt>[^\]]*)\]
        \((?P<source><[^>]*>|(?:[^()\s]|\([^()\s]*\))*)(?:\s+"[^"]*")?\))
    | (?P<link>\[(?P<label>(?:[^\[\]]|!?\[[^\]]*\](?:\([^)]*\))?)*)\]
        \((?P<target><[^>]*>|(?:[^()\s]|\([^()\s]*\))*)(?:\s+"[^"]*")?\))
    | (?P<reference>\[(?P<reference_label>[^\[\]]+)\]\[(?P<reference_name>[^\]]*)\])
    | (?P<autolink><(?P<address>https?://[^>\s]+)>)
    | (?P<break><br\s*/?>)
    | (?P<html></?[A-Za-z][^>]*>)
    | (?P<strong>\*\*(?=\S)(?P<strong_star>.+?)(?<=\S)\*\*
        |(?<![A-Za-z0-9])__(?=\S)(?P<strong_under>.+?)(?<=\S)__(?![A-Za-z0-9]))
    | (?P<strike>~~(?=\S)(?P<strike_text>.+?)(?<=\S)~~)
    | (?P<emphasis>(?:\*(?=[^\s*])(?P<star_text>.+?)(?<=[^\s*])\*(?!\*))
        |(?:(?<![A-Za-z0-9_])_(?=[^\s_])(?P<under_text>.+?)(?<=[^\s_])_(?![A-Za-z0-9_])))
    """,
    re.VERBOSE | re.DOTALL,
)
KINDS = (
    'escape',
    'code',
    'image',
    'link',
    'reference',
    'autolink',
    'break',
    'html',
    'strong',
    'strike',
    'emphasis',
)


def inline_runs(text: str, references: dict[str, str]) -> list[Run]:
    """
    The runs of a piece of inline Markdown.

    Args:
        text: The Markdown source of one paragraph, heading or cell.
        references: The targets of the reference links of the document, by their names in
            lower case.

    Returns:
        The runs. An image is a run that keeps its source in ``image_source``.
    """
    runs: list[Run] = []
    position = 0
    for match in INLINE.finditer(text):
        if match.start() > position:
            runs.append(Run(text[position : match.start()]))
        position = match.end()
        kind = next(kind for kind in KINDS if match[kind] is not None)
        runs.extend(RUNS_OF[kind](match, references))
    if position < len(text):
        runs.append(Run(text[position:]))
    return [run for run in runs if run.text or run.image_source is not None]


def image_as_text(run: Run) -> Run:
    """An image inside a sentence, as its description in brackets."""
    if run.image_source is None:
        return run
    label = run.text or run.image_source
    if run.target is not None:
        return dataclasses.replace(run, text=label, image_source=None)
    return dataclasses.replace(run, text=f'[image: {label}]', dim=True, image_source=None)


def _linked(label: str, target: str, references: dict[str, str]) -> list[Run]:
    """The runs of a link: its label, underlined, with the place that it leads to."""
    return [
        image_as_text(dataclasses.replace(run, target=target))
        for run in inline_runs(label, references)
    ] or [Run(target, target=target)]


def _code(match: re.Match[str], references: dict[str, str]) -> list[Run]:
    text = match['code_text'].replace('\n', ' ')
    if text.startswith(' ') and text.endswith(' ') and text.strip():
        text = text[1:-1]  # one space at each end separates the code from its marks
    return [Run(text, code=True)]


def _image(match: re.Match[str], references: dict[str, str]) -> list[Run]:
    return [Run(match['alt'], image_source=match['source'].strip('<>'))]


def _link(match: re.Match[str], references: dict[str, str]) -> list[Run]:
    return _linked(match['label'], match['target'].strip('<>'), references)


def _reference(match: re.Match[str], references: dict[str, str]) -> list[Run]:
    name = (match['reference_name'] or match['reference_label']).lower()
    target = references.get(name)
    if target is None:
        return [Run(match['reference'])]
    return _linked(match['reference_label'], target, references)


def _strong(match: re.Match[str], references: dict[str, str]) -> list[Run]:
    inner = match['strong_star'] or match['strong_under']
    return [dataclasses.replace(run, bold=True) for run in inline_runs(inner, references)]


def _strike(match: re.Match[str], references: dict[str, str]) -> list[Run]:
    return [
        dataclasses.replace(run, strike=True)
        for run in inline_runs(match['strike_text'], references)
    ]


def _emphasis(match: re.Match[str], references: dict[str, str]) -> list[Run]:
    inner = match['star_text'] or match['under_text']
    return [
        dataclasses.replace(run, italic=True) for run in inline_runs(inner, references)
    ]


RUNS_OF: dict[str, Callable[[re.Match[str], dict[str, str]], list[Run]]] = {
    'escape': lambda match, references: [Run(match['escape'][1])],
    'code': _code,
    'image': _image,
    'link': _link,
    'reference': _reference,
    'autolink': lambda match, references: [
        Run(match['address'], target=match['address'])
    ],
    'break': lambda match, references: [Run('\n')],
    'html': lambda match, references: [],  # a tag inside a sentence is left out
    'strong': _strong,
    'strike': _strike,
    'emphasis': _emphasis,
}
"""The runs that each kind of inline text gives, by the kind."""
