"""xnano.core.interface

---

Track dirty state for named fields shared by grids and hosts.
"""

from __future__ import annotations

from xnano.fields import FieldState
from xnano.utils.deprecation import warn_renamed_attribute


class AbstractInterface:
    """Provide per-instance state for declared grid fields.

    Example:
        ``grid.grid_get_field_state("status")``

    Attributes:
        _grid_field_states: Mutable field state keyed by declared name.
    """

    _grid_field_states: dict[str, FieldState]
    """Mutable field state keyed by declared field name."""

    def _grid_init_field_states(self) -> None:
        """Allocate state for every declared layout and state field."""
        names = (
            *getattr(type(self), "_grid_fields", {}),
            *getattr(type(self), "_grid_state_fields", {}),
        )
        object.__setattr__(
            self,
            "_grid_field_states",
            {name: FieldState(name=name) for name in names},
        )

    def grid_get_field_state(self, name: str) -> FieldState | None:
        """Return tracked state for a field.

        Args:
            name: Field attribute name.

        Returns:
            Its state, or ``None`` for an unknown field.
        """
        return getattr(self, "_grid_field_states", {}).get(name)

    def grid_mark_field_dirty(self, name: str) -> None:
        """Mark a field as changed.

        Args:
            name: Field attribute name.
        """
        state = self.grid_get_field_state(name)
        if state is not None:
            state.mark_dirty()
            state.value = getattr(self, name, None)

    @warn_renamed_attribute(
        "AbstractInterface.get_field_state",
        "AbstractInterface.grid_get_field_state",
    )
    def get_field_state(self, name: str) -> FieldState | None:
        """Deprecated alias for ``grid_get_field_state``."""
        return self.grid_get_field_state(name)

    @warn_renamed_attribute(
        "AbstractInterface.mark_field_dirty",
        "AbstractInterface.grid_mark_field_dirty",
    )
    def mark_field_dirty(self, name: str) -> None:
        """Deprecated alias for ``grid_mark_field_dirty``."""
        self.grid_mark_field_dirty(name)


__all__ = ("AbstractInterface",)
