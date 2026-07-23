"""tests.beta.test_imports"""

from __future__ import annotations


def test_beta_root_exports() -> None:
    import xnano.beta as xnano

    assert xnano.BaseGrid is not None
    assert xnano.Field is not None
    assert xnano.Terminal is not None
    assert xnano.Context is not None
    assert xnano.Component is not None
    assert xnano.Runtime is not None
    assert xnano.Web is not None
    assert xnano.hooks.on_keyboard is not None
    assert xnano.requests.on_get_request is not None
    assert isinstance(xnano.__version__, str)


def test_beta_drop_in_import_style() -> None:
    import xnano.beta as xnano

    assert hasattr(xnano, "on_keyboard")
    assert hasattr(xnano, "on_action")
    assert hasattr(xnano, "render")
    assert hasattr(xnano, "Action")
    assert hasattr(xnano, "Style")


def test_events_have_no_hook_decorators() -> None:
    from xnano.beta import events

    assert hasattr(events, "Event")
    assert hasattr(events, "KeyboardEventData")
    assert not hasattr(events, "on_keyboard")
    assert hasattr(events, "event_from_core")


def test_hooks_module_namespace() -> None:
    from xnano.beta import hooks

    for name in (
        "on_action",
        "on_click",
        "on_clipboard",
        "on_event",
        "on_field",
        "on_focus",
        "on_keyboard",
        "on_mouse",
        "on_poll",
        "on_resize",
        "on_state",
        "on_tick",
    ):
        assert callable(getattr(hooks, name))
