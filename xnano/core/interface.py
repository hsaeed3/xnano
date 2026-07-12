"""xnano.core.interface

---

``AbstractInterface`` base for surfaces with named fields and live
``FieldState``. Layout-specific behavior stays on ``BaseGrid``.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from xnano.fields import FieldState

if TYPE_CHECKING:
    from xnano.fields import FieldInfo


class AbstractInterface:
    """Shared base for surfaces with named fields and live field state.

    ``BaseGrid`` subclasses this so field change notification and
    per-instance ``FieldState`` live beneath layout.
    """

    _field_states: dict[str, FieldState]

    def _init_field_states(self) -> None:
        """Allocate empty ``FieldState`` entries for declared fields."""
        states: dict[str, FieldState] = {}
        for name in getattr(type(self), "_grid_fields", {}):
            states[name] = FieldState(name=name)
        for name in getattr(type(self), "_grid_state_fields", {}):
            states[name] = FieldState(name=name)
        object.__setattr__(self, "_field_states", states)

    def get_field_state(self, name: str) -> FieldState | None:
        """Return live state for ``name``, if tracked.

        Args:
            name: Field attribute name.

        Returns:
            The ``FieldState`` or ``None`` when unknown.
        """
        states = getattr(self, "_field_states", None)
        if not states:
            return None
        return states.get(name)

    def mark_field_dirty(self, name: str) -> None:
        """Mark ``name`` dirty and notify the active host controller.

        Args:
            name: Field attribute name.
        """
        state = self.get_field_state(name)
        if state is not None:
            state.mark_dirty()
            value = getattr(self, name, None)
            state.value = value
        self._notify_field_changed(name, state)

    def _notify_field_changed(
        self, name: str, state: FieldState | None
    ) -> None:
        """Push dirtiness to the active host's controller when present.

        Uses private controller handles (``_session`` / ``controller``)
        so inactive terminals do not raise via the public ``session``
        property.
        """
        try:
            from xnano.core.hosts import get_active_host

            host = get_active_host()
            if host is None:
                return
            controller = getattr(host, "_session", None)
            if controller is None:
                controller = getattr(host, "controller", None)
            if controller is None:
                return
            notify = getattr(controller, "notify_field_changed", None)
            if callable(notify):
                notify(self, name, state)
        except Exception:
            return


__all__ = ("AbstractInterface",)
