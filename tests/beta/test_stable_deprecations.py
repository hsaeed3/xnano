"""tests.beta.test_stable_deprecations"""

from __future__ import annotations


def test_stable_fields_hooks_events_and_types_are_deprecated() -> None:
    from xnano import _types, events, fields, hooks

    values = (
        fields.Field,
        fields.GridFieldInfo,
        fields.FieldState,
        hooks.Hooks,
        events.AbstractEventData,
        events.ClipboardEventData,
        events.FocusEventData,
        events.KeyboardEventData,
        events.MouseEventData,
        events.ResizeEventData,
        events.Event,
        events.normalize_keyboard_binding,
        events.parse_binding_tuple,
        events.on,
        events.on_action,
        events.on_click,
        events.on_clipboard,
        events.on_event,
        events.on_field,
        events.on_focus,
        events.on_keyboard,
        events.on_mouse,
        events.on_poll,
        events.on_resize,
        events.on_state,
        events.on_tick,
        _types.Padding,
        _types.Size,
        _types.Area,
        _types.Sizing,
        _types.Frame,
        _types.FieldFocus,
        _types.ScrollHandle,
        _types.resolve_flex_weight,
        _types.field_has_frame_chrome,
        _types.frame_from_field,
        _types.is_component,
        _types.uses_default_component_size,
        _types.is_focusable_component,
        _types.get_focusable_component,
        _types.collect_focusable_fields,
        _types.sync_input_focus_flags,
        _types.focused_component,
        _types.apply_text_keyboard,
        _types.set_field_focus,
        _types.clear_field_focus,
        _types.cycle_field_focus,
        _types.ensure_default_field_focus,
        _types.place_cursor_for_focus,
    )

    for value in values:
        message = getattr(value, "__deprecated__", "")
        assert "v1.2" in message
        assert "xnano.beta" in message
