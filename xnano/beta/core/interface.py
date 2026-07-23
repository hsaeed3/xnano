"""xnano.beta.core.interface

---

Track dirty state for named fields shared by beta grids and hosts.
"""

from __future__ import annotations

from xnano.beta.fields import FieldState


class AbstractInterface:
    """Provide per-instance state for declared grid fields.

    Example:
        ``grid.get_field_state("status")``

    Attributes:
        _field_states: Mutable field state keyed by declared field name.
    """

    _field_states: dict[str, FieldState]
    """Mutable field state keyed by declared field name."""

    def _init_field_states(self) -> None:
        """Allocate state for every declared layout and state field."""
        names = (
            *getattr(type(self), "_grid_fields", {}),
            *getattr(type(self), "_grid_state_fields", {}),
        )
        object.__setattr__(
            self,
            "_field_states",
            {name: FieldState(name=name) for name in names},
        )

    def get_field_state(self, name: str) -> FieldState | None:
        """Return tracked state for a field.

        Args:
            name: Field attribute name.

        Returns:
            Its state, or ``None`` for an unknown field.
        """
        return getattr(self, "_field_states", {}).get(name)

    def mark_field_dirty(self, name: str) -> None:
        """Mark a field as changed.

        Args:
            name: Field attribute name.
        """
        state = self.get_field_state(name)
        if state is not None:
            state.mark_dirty()
            state.value = getattr(self, name, None)


__all__ = ("AbstractInterface",)
