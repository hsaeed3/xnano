"""tests.test_entrypoint

---

Exercise the installed command and complete lazy public interface.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

import xnano
import xnano.__main__ as entrypoint


def test_public_interface_lazily_resolves_every_documented_export() -> None:
    """Every name advertised by ``from xnano import *`` resolves."""
    exported = {name: getattr(xnano, name) for name in xnano.__all__}
    assert set(dir(xnano)) == set(xnano.__all__)
    assert all(value is not None for value in exported.values())
    with pytest.raises(AttributeError, match="no attribute"):
        xnano.__getattr__("DetroitSmash")


def test_command_without_arguments_launches_showcase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The installed command defaults to the interactive showcase."""
    calls: list[str] = []
    monkeypatch.setattr(sys, "argv", ["xnano"])
    monkeypatch.setattr(
        "xnano.core.demo.run_demo",
        lambda: calls.append("showcase"),
    )
    entrypoint.run_demo()
    assert calls == ["showcase"]


@pytest.mark.parametrize("argument", ("-h", "--help", "help"))
def test_command_help_aliases_print_usage(
    argument: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["xnano", argument])
    entrypoint.run_demo()
    assert "Usage: xnano [PATH.md]" in capsys.readouterr().out


def test_command_opens_markdown_document(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = tmp_path / "guide.md"
    document.write_text("# Guide", encoding="utf-8")
    opened: list[str] = []
    monkeypatch.setattr(sys, "argv", ["xnano", str(document)])
    monkeypatch.setattr(
        "xnano.markdown.run_markdown",
        lambda path: opened.append(path),
    )
    entrypoint.run_demo()
    assert opened == [str(document)]


def test_command_rejects_unknown_input(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["xnano", "missing.txt"])
    with pytest.raises(SystemExit) as exit_error:
        entrypoint.run_demo()
    assert exit_error.value.code == 2
    assert "unknown input" in capsys.readouterr().err
