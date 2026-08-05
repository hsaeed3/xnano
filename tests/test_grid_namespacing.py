"""tests.test_grid_namespacing

---

Covers the ``grid_*`` / ``__xnano_*__`` naming convention on ``BaseGrid``
and ``AbstractInterface``: every public member follows it, the previous
names still work as deprecated aliases, and ``__xnano_grid__`` identifies
a grid without importing ``BaseGrid``.
"""

from __future__ import annotations

import warnings

import pytest

from xnano.components.text import Text
from xnano.fields import Field
from xnano.grids import BaseGrid
from xnano.types import is_grid

_EXEMPT = frozenset({"z", "rows", "columns", "visible"})


class _App(BaseGrid):
    body: str = Field(default="hi")


def _is_deprecated(member: object) -> bool:
    """Whether a class member carries PEP 702 deprecation metadata."""
    if isinstance(member, property):
        member = member.fget
    return hasattr(member, "__deprecated__")


def test_every_public_grid_member_follows_the_convention() -> None:
    offenders = [
        name
        for name in dir(BaseGrid)
        if not name.startswith("_")
        and name not in _EXEMPT
        and not name.startswith("grid_")
        # Deprecated aliases are kept deliberately; they carry PEP 702
        # metadata so type checkers strike them through.
        and not _is_deprecated(getattr(BaseGrid, name, None))
    ]
    assert offenders == []


def test_dunder_members_are_xnano_namespaced_or_python_protocol() -> None:
    xnano_dunders = [
        name
        for name in vars(BaseGrid)
        if name.startswith("__") and name.endswith("__") and "xnano" in name
    ]
    assert "__xnano_grid__" in xnano_dunders


def test_is_grid_identifies_grids_without_importing_basegrid() -> None:
    assert is_grid(_App())
    assert not is_grid(Text("x"))
    assert not is_grid("plain")
    assert not is_grid(None)


def test_grid_focused_and_grid_state_are_the_canonical_names() -> None:
    grid = _App()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert grid.grid_focused is False
        assert grid.grid_state is None


@pytest.mark.parametrize(
    ("old", "new"),
    (
        ("focused", "grid_focused"),
        ("state", "grid_state"),
    ),
)
def test_deprecated_properties_still_read_through(old: str, new: str) -> None:
    grid = _App()
    with pytest.warns(DeprecationWarning):
        value = getattr(grid, old)
    assert value == getattr(grid, new)


def test_deprecated_methods_delegate_to_their_new_names() -> None:
    grid = _App()
    with pytest.warns(DeprecationWarning):
        grid.set_background("black")
    assert grid._grid_frame is not None
    assert grid._grid_frame.background == "black"

    calls: list[str] = []
    with pytest.warns(DeprecationWarning):
        grid.schedule_update(lambda: calls.append("ran"))
    assert calls == ["ran"]


def test_interface_state_helpers_are_renamed_with_aliases() -> None:
    grid = _App()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        state = grid.grid_get_field_state("body")
        assert state is not None
        grid.grid_mark_field_dirty("body")

    with pytest.warns(DeprecationWarning):
        assert grid.get_field_state("body") is state
    with pytest.warns(DeprecationWarning):
        grid.mark_field_dirty("body")


def test_field_state_storage_is_grid_namespaced() -> None:
    grid = _App()
    assert isinstance(grid._grid_field_states, dict)
    assert "body" in grid._grid_field_states
