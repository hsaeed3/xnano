"""tests.test_vhs_recording"""

import pytest

from xnano_core.rust import native

from xnano.beta.utils import vhs_recording


@pytest.fixture
def clear_vhs_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "XNANO_VHS_MONO",
        "XNANO_VHS_DOCS_BG",
        "XNANO_VHS_THEME",
    ):
        monkeypatch.delenv(key, raising=False)


def test_remap_passthrough_without_env(clear_vhs_env: None) -> None:
    assert vhs_recording.remap_color_for_vhs("violet-500") == "violet-500"
    assert (
        vhs_recording.remap_color_for_vhs(
            "violet-900",
            role="background",
        )
        == "violet-900"
    )


def test_remap_mono_foreground(
    clear_vhs_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XNANO_VHS_MONO", "1")
    monkeypatch.setenv("XNANO_VHS_THEME", "dark")
    assert (
        vhs_recording.remap_color_for_vhs("rose-500")
        == vhs_recording.MONO_FG_DARK
    )
    assert (
        vhs_recording.remap_color_for_vhs(
            "rose-500",
            role="background",
        )
        == vhs_recording.DOC_BG_DARK
    )


def test_remap_mono_light_theme(
    clear_vhs_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XNANO_VHS_MONO", "1")
    monkeypatch.setenv("XNANO_VHS_THEME", "light")
    assert (
        vhs_recording.remap_color_for_vhs("sky-400")
        == vhs_recording.MONO_FG_LIGHT
    )


def test_remap_docs_background_passthrough(
    clear_vhs_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Docs-background mode leaves authored colors untouched: the renderer now
    # paints field backgrounds behind text cells only, so accent backgrounds
    # (e.g. a violet header) should render as designed rather than being
    # flattened to the page color.
    monkeypatch.setenv("XNANO_VHS_DOCS_BG", "1")
    monkeypatch.setenv("XNANO_VHS_THEME", "light")
    assert vhs_recording.remap_color_for_vhs("emerald-400") == "emerald-400"
    assert (
        vhs_recording.remap_color_for_vhs("violet-900", role="background")
        == "violet-900"
    )
    assert vhs_recording.remap_color_for_vhs(None, role="background") is None


def test_native_color_mono_mode(
    clear_vhs_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from xnano.beta.utils.native_types import get_native_color_from_color_like

    monkeypatch.setenv("XNANO_VHS_MONO", "1")
    monkeypatch.setenv("XNANO_VHS_THEME", "dark")
    color = get_native_color_from_color_like("rose-500", role="foreground")
    expected = native.Color.rgb(222, 220, 209)
    assert color == expected
