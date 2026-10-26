"""Tests for the parsers and the README rewriting of ``scripts/readme_assets.py`` (no Kitty needed)."""

from __future__ import annotations

import pathlib
import sys
from typing import cast

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'scripts'))

import readme_assets as assets  # noqa: E402


def options(text: str) -> assets.Options:
    return assets.parse_options(text, 7)


def action(text: str, height: int = 12) -> assets.Action:
    return assets.parse_action(text, 9, assets.Options(name='x', height=height))


def test_options_defaults_and_values() -> None:
    assert options('name="a-b1"') == assets.Options(name='a-b1')
    parsed = options('name="a" type="gif" height=10 duration=2.5')
    assert (parsed.kind, parsed.height, parsed.duration) == ('gif', 10, 2.5)
    assert parsed.filename(assets.DARK_THEME) == 'a-dark.gif'
    assert options('name="a"').filename(assets.LIGHT_THEME) == 'a-light.png'


@pytest.mark.parametrize(
    ('text', 'fragment'),
    [
        ('type="gif"', "'name' is missing"),
        ('name="a" name="b"', "'name' is given twice"),
        ('name="a" color=1', "unknown option 'color'"),
        ('name=a', 'Write it as name='),
        ('name="Bad_Name"', 'lowercase letters'),
        ('name="a" type="video"', 'image" or "gif"'),
        ('name="a" height=ten', 'without quotes'),
        ('name="a" height=2', 'from 3 to 60'),
        ('name="a" height=4.5', 'whole number'),
        ('name="a" duration=3', 'only with type="gif"'),
        ('name="a" type="gif" duration=0', 'above zero'),
        ('name="a" oops', 'cannot read the options'),
    ],
)
def test_option_errors_name_the_line(text: str, fragment: str) -> None:
    with pytest.raises(assets.ReadmeAssetError, match='README.md line 7') as raised:
        options(text)
    assert fragment in str(raised.value)


def test_actions() -> None:
    assert action('wait 0.5') == assets.Wait(0.5)
    assert action('press left ctrl+s') == assets.Press(('left', 'ctrl+s'))
    assert action('type hello  world') == assets.Type('hello  world')
    assert action('paste a b') == assets.Paste('a b')
    assert action('click 30 4') == assets.Click(30, 4, 'left')
    assert action('click 1 2 right') == assets.Click(1, 2, 'right')
    assert action('drag 1 2 3 4') == assets.Drag(1, 2, 3, 4)
    assert action('scroll down 5 6') == assets.Scroll('down', 5, 6, 1)
    assert action('scroll up 5 6 3') == assets.Scroll('up', 5, 6, 3)


@pytest.mark.parametrize(
    ('text', 'fragment'),
    [
        ('jump', "unknown action 'jump'"),
        ('wait', 'wait SECONDS'),
        ('wait soon', 'a number of seconds'),
        ('wait -1', 'zero or more'),
        ('press', 'press KEY'),
        ('type', "'type' has no text"),
        ('paste', "'paste' has no text"),
        ('click 1', 'click COLUMN ROW'),
        ('click a 1', 'a column from 0 to 99'),
        ('click 1 b', 'a row from 0 to 11'),
        ('click 100 1', 'outside the 100 by 12 window'),
        ('click 1 12', 'outside the 100 by 12 window'),
        ('click 1 1 wheel', 'left, right or middle'),
        ('drag 1 2 3', 'drag COLUMN ROW COLUMN ROW'),
        ('scroll sideways 1 1', 'up or down'),
        ('scroll up 1 1 x', 'whole number of ticks'),
        ('scroll up 1 1 0', 'at least 1'),
    ],
)
def test_action_errors_name_the_line(text: str, fragment: str) -> None:
    with pytest.raises(assets.ReadmeAssetError, match='README.md line 9') as raised:
        action(text)
    assert fragment in str(raised.value)


def test_mouse_reports_are_one_based_sgr() -> None:
    assert assets.mouse_reports(assets.Click(30, 4)) == [
        '\x1b[<0;31;5M',
        '\x1b[<0;31;5m',
    ]
    assert assets.mouse_reports(assets.Click(0, 0, 'right')) == [
        '\x1b[<2;1;1M',
        '\x1b[<2;1;1m',
    ]
    assert assets.mouse_reports(assets.Scroll('up', 2, 3, 2)) == ['\x1b[<64;3;4M'] * 2
    assert assets.mouse_reports(assets.Scroll('down', 2, 3)) == ['\x1b[<65;3;4M']
    drag = assets.mouse_reports(assets.Drag(0, 0, 8, 8))
    assert drag[0] == '\x1b[<0;1;1M'
    assert drag[1] == '\x1b[<32;2;2M'
    assert drag[-2] == '\x1b[<32;9;9M'
    assert drag[-1] == '\x1b[<0;9;9m'
    assert len(drag) == 8 + 2  # one motion report per cell crossed


README = """# Title

<!-- @code-block name="one" -->
```python
print(1)
```

Text.

<!-- @code-block name="two" type="gif" height=8 duration=4
wait 1
press q
-->
```python
print(2)
```

<!-- not a code block -->
```python
print(3)
```

End
"""


def test_blocks_are_found_with_their_code_and_actions() -> None:
    blocks = assets.parse_blocks(README)
    assert [block.options.name for block in blocks] == ['one', 'two']
    assert blocks[0].code == 'print(1)\n'
    assert blocks[0].actions == ()
    assert blocks[1].actions == (assets.Wait(1), assets.Press(('q',)))
    assert blocks[1].line == 10  # the 1-based line of the comment
    assert assets.recording_seconds(blocks[1]) == 4
    assert (
        assets.recording_seconds(assets.Block(1, assets.Options('x', 'gif'), (), '', 0))
        == 2
    )


def test_default_recording_seconds_follow_the_waits() -> None:
    block = assets.Block(
        1, assets.Options('x', 'gif'), (assets.Wait(3), assets.Wait(2)), '', 0
    )
    assert assets.recording_seconds(block) == 6


def test_block_errors_name_the_line() -> None:
    with pytest.raises(assets.ReadmeAssetError, match='line 3'):
        assets.parse_blocks('a\nb\n<!-- @code-block name="X" -->\n```python\n```\n')
    short = (
        '<!-- @code-block name="a" type="gif" duration=1\nwait 3\n-->\n```python\n```\n'
    )
    with pytest.raises(assets.ReadmeAssetError, match='line 1.*at least the total wait'):
        assets.parse_blocks(short)
    twice = '<!-- @code-block name="a" -->\n```python\n```\n<!-- @code-block name="a" -->\n```python\n```\n'
    with pytest.raises(assets.ReadmeAssetError, match='already used on line 1'):
        assets.parse_blocks(twice)
    with pytest.raises(assets.ReadmeAssetError, match='never closed'):
        assets.parse_blocks('<!-- @code-block name="a" -->\n```python\nx\n')
    with pytest.raises(assets.ReadmeAssetError, match='own line'):
        assets.parse_blocks(
            '<!-- @code-block name="a" -->\nwait 1\n-->\n```python\n```\n'
        )


def test_every_block_is_rendered_for_the_dark_and_the_light_theme() -> None:
    assert [theme.name for theme in assets.THEMES] == ['dark', 'light']
    assert assets.DARK_THEME.background == '#0d1117'
    assert assets.LIGHT_THEME.background == '#ffffff'
    image, recording = assets.parse_blocks(README)
    assert [image.options.filename(theme) for theme in assets.THEMES] == [
        'one-dark.png',
        'one-light.png',
    ]
    assert [recording.options.filename(theme) for theme in assets.THEMES] == [
        'two-dark.gif',
        'two-light.gif',
    ]


def test_asset_region_lets_the_page_pick_the_theme() -> None:
    region = assets.asset_region(assets.Options(name='demo', kind='gif'))
    assert region == (
        '<!-- @code-block-asset name="demo" -->\n'
        '<picture>\n'
        '  <source media="(prefers-color-scheme: dark)" '
        f'srcset="{assets.ASSET_PATH}/demo-dark.gif">\n'
        f'  <img alt="demo" src="{assets.ASSET_PATH}/demo-light.gif">\n'
        '</picture>\n'
        '<!-- /@code-block-asset -->\n'
    )
    assert assets.REGION_PATTERN.fullmatch('\n' + region)


def test_theme_colors_are_sent_to_kitty_with_the_cursor_hidden() -> None:
    class Window:
        def __init__(self) -> None:
            self.sent: list[tuple[str, dict[str, object]]] = []

        def command(self, name: str, **payload: object) -> None:
            self.sent.append((name, payload))

    window = Window()
    assets.apply_theme(cast(assets.ActualTerminal, window), assets.DARK_THEME)
    assert [name for name, _ in window.sent] == ['set-colors']
    payload = window.sent[0][1]
    assert payload['all'] is True
    colors = cast(dict[str, int], payload['colors'])
    assert colors['background'] == 0x0D1117
    assert colors['foreground'] == 0xE6EDF3
    assert colors['cursor'] == 0x0D1117
    assert colors['cursor_text_color'] == 0x0D1117
    assert colors['color0'] == 0x484F58
    assert colors['color15'] == 0xFFFFFF
    assert [name for name in colors if name.startswith('color')] == [
        f'color{number}' for number in range(16)
    ]
    for theme in assets.THEMES:
        assert len(theme.palette) == 16


def test_regions_are_inserted_replaced_and_removed() -> None:
    once = assets.update_regions(README)
    assert once.count('<!-- @code-block-asset') == 2
    assert (
        '```\n\n<!-- @code-block-asset name="one" -->\n'
        '<picture>\n'
        f'  <source media="(prefers-color-scheme: dark)" srcset="{assets.ASSET_PATH}/one-dark.png">\n'
        f'  <img alt="one" src="{assets.ASSET_PATH}/one-light.png">\n'
        '</picture>\n'
        '<!-- /@code-block-asset -->\n\nText.' in once
    )
    assert f'srcset="{assets.ASSET_PATH}/two-dark.gif"' in once
    assert f'src="{assets.ASSET_PATH}/two-light.gif"' in once
    assert assets.update_regions(once) == once  # idempotent
    stale = once.replace('one-light.png', 'old-light.png')
    assert assets.update_regions(stale) == once  # replaced
    plain = once.replace(
        assets.asset_region(assets.Options(name='one')),
        '<!-- @code-block-asset name="one" -->\n![one](old.png)\n<!-- /@code-block-asset -->\n',
    )
    assert plain != once
    assert assets.update_regions(plain) == once  # a region of plain Markdown is replaced
    unannotated = once.replace('<!-- @code-block name="one" -->\n', '')
    removed = assets.update_regions(unannotated)
    assert 'name="one"' not in removed
    assert removed.count('<!-- @code-block-asset') == 1
    assert removed.startswith('# Title\n\n```python\nprint(1)\n```\n\nText.')


COMMENTED = """# Page

<!-- @code-block name="framed" -->
``` python title="framed.py"
print(1)  # >> [first]
```

<comments>
<tag name="first">
Prints one.
</tag>
</comments>

After.
"""


def page(name: str = 'guide.md') -> assets.Document:
    return assets.Document(
        assets.PAGES / 'learn' / name, assets.PAGE_OUTPUT, assets.PAGE_THEMES
    )


def test_regions_go_after_the_comments_of_their_block() -> None:
    for document in (assets.README_DOCUMENT, page()):
        once = assets.update_regions(COMMENTED, document)
        assert '</comments>\n\n<!-- @code-block-asset name="framed" -->' in once
        assert '```\n\n<comments>' in once  # the comments stay right below their code
        assert assets.update_regions(once, document) == once  # idempotent
        moved = once.replace('<comments>', '<!-- -->\n<comments>', 1)
        assert '<!-- -->\n<comments>' in assets.update_regions(moved, document)


def test_page_regions_show_images_by_the_site_color_scheme() -> None:
    assert assets.asset_region(assets.Options(name='demo'), page()) == (
        '<!-- @code-block-asset name="demo" -->\n\n'
        '![demo](../assets/examples/demo-light.png#only-light)\n'
        '![demo](../assets/examples/demo-dark.png#only-dark)\n\n'
        '<!-- /@code-block-asset -->\n'
    )


def test_page_errors_name_the_page() -> None:
    unclosed = COMMENTED.replace('</comments>\n', '')
    with pytest.raises(
        assets.ReadmeAssetError, match='docs/learn/guide.md line 8: the <comments>'
    ):
        assets.update_regions(unclosed, page())


def test_page_names_are_unique_across_pages() -> None:
    blocks = assets.parse_blocks(COMMENTED)
    with pytest.raises(
        assets.ReadmeAssetError, match='already used in docs/learn/one.md line 3'
    ):
        assets.check_page_names([(page('one.md'), blocks), (page('two.md'), blocks)])
    assets.check_page_names([(assets.README_DOCUMENT, blocks), (page('one.md'), blocks)])


class ChangingWindow:
    """A stand-in window whose screen changes on each read until it has drawn every frame."""

    def __init__(self, frames: int) -> None:
        self.reads = 0
        self.frames = frames

    def text(self, *, ansi: bool = False) -> str:
        self.reads += 1
        return str(min(self.reads, self.frames))


def test_images_wait_for_a_still_window() -> None:
    window = ChangingWindow(frames=4)
    assert assets.wait_until_still(window, still_seconds=0.1, timeout=2)  # pyright: ignore[reportArgumentType]
    assert window.reads > 4  # it kept reading until the drawing stopped


def test_a_window_that_never_stops_is_taken_after_the_timeout() -> None:
    window = ChangingWindow(frames=10**9)
    assert not assets.wait_until_still(window, still_seconds=0.1, timeout=0.3)  # pyright: ignore[reportArgumentType]
