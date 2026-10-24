"""
tests.test_terminal

The terminal package: what the terminal can do, the settings it is asked for and its window.
"""

from __future__ import annotations

import dataclasses
import typing

import pytest

import xnano
import xnano.errors
import xnano.terminal
import xnano_core

COLOR_PROFILES = ('no_terminal', 'no_color', 'ansi16', 'ansi256', 'truecolor')
GRAPHICS_PROTOCOLS = ('half_blocks', 'sixel', 'kitty', 'iterm2')
CAPABILITY_STATUSES = ('supported', 'unsupported', 'unknown')


class TestCapabilities:
    def test_the_terminal_answers_with_xnano_values(self):
        terminal_capabilities = xnano.terminal.capabilities()
        assert isinstance(terminal_capabilities, xnano.terminal.TerminalCapabilities)
        assert isinstance(
            terminal_capabilities.keyboard, xnano.terminal.KeyboardCapabilities
        )
        assert isinstance(
            terminal_capabilities.graphics, xnano.terminal.GraphicsCapabilities
        )
        assert terminal_capabilities.colors in COLOR_PROFILES
        assert terminal_capabilities.keyboard.enhancement in CAPABILITY_STATUSES
        assert terminal_capabilities.graphics.protocol in GRAPHICS_PROTOCOLS

    def test_a_program_that_does_not_run_in_a_terminal_cannot_open_a_canvas(self):
        # Under pytest standard output is captured, so there is no terminal to draw on.
        assert xnano.terminal.capabilities().is_available is False

    def test_every_field_has_the_type_it_documents(self):
        terminal_capabilities = xnano.terminal.capabilities()
        keyboard = terminal_capabilities.keyboard
        assert isinstance(keyboard.can_disambiguate_keys, bool)
        assert isinstance(keyboard.can_report_release_events, bool)
        assert isinstance(keyboard.can_report_modifier_keys, bool)
        assert keyboard.unavailable_reason is None or isinstance(
            keyboard.unavailable_reason, str
        )
        cell_size = terminal_capabilities.graphics.cell_size_in_pixels
        assert cell_size is None or (len(cell_size) == 2 and min(cell_size) > 0)

    def test_the_value_cannot_be_changed(self):
        terminal_capabilities = xnano.terminal.capabilities()
        with pytest.raises(dataclasses.FrozenInstanceError):
            terminal_capabilities.colors = 'truecolor'  # type: ignore[misc]
        with pytest.raises(dataclasses.FrozenInstanceError):
            terminal_capabilities.keyboard.enhancement = 'supported'  # type: ignore[misc]
        with pytest.raises(dataclasses.FrozenInstanceError):
            terminal_capabilities.graphics.protocol = 'kitty'  # type: ignore[misc]

    def test_two_answers_of_one_terminal_are_equal(self):
        assert xnano.terminal.capabilities() == xnano.terminal.capabilities()

    def test_the_fields_come_from_the_answers_of_the_core(self):
        from xnano.terminal._capabilities import capabilities_from_core

        core_terminal = xnano_core.detect_terminal_capabilities()
        core_keyboard = xnano_core.query_keyboard_capabilities()
        built = capabilities_from_core(core_terminal, core_keyboard)
        assert built.colors == core_terminal.color_profile
        assert built.graphics.protocol == core_terminal.graphics_protocol
        assert built.graphics.cell_size_in_pixels == core_terminal.cell_size_in_pixels
        assert built.keyboard.enhancement == core_keyboard.enhancement
        assert built.keyboard.can_disambiguate_keys == core_keyboard.disambiguates_keys
        assert (
            built.keyboard.can_report_release_events == core_keyboard.reports_event_types
        )
        assert built.keyboard.can_report_modifier_keys == core_keyboard.reports_all_keys
        assert built.keyboard.unavailable_reason == core_keyboard.unavailable_reason

    def test_a_canvas_can_only_be_put_on_the_screen_where_there_is_a_terminal(self):
        from xnano.terminal._capabilities import capabilities_from_core

        core_terminal = xnano_core.detect_terminal_capabilities()
        core_keyboard = xnano_core.query_keyboard_capabilities()
        built = capabilities_from_core(core_terminal, core_keyboard)
        assert built.is_available == (
            core_terminal.is_terminal and core_terminal.is_live_terminal_available
        )

    def test_it_refuses_to_ask_while_a_canvas_is_on_the_screen(self, monkeypatch):
        monkeypatch.setattr(xnano.terminal._screen, 'is_screen_claimed', True)
        with pytest.raises(
            xnano.errors.TerminalAlreadyOpenError, match='terminal.capabilities'
        ):
            xnano.terminal.capabilities()

    def test_only_an_open_terminal_has_the_properties_of_a_terminal(self):
        with xnano.new(width=4, height=1) as canvas:
            for name in ('capabilities', 'settings'):
                assert not hasattr(canvas, name), name
            assert canvas.screen.window == canvas.screen.size
        for name in ('capabilities', 'settings'):
            assert isinstance(getattr(xnano.Terminal, name), property), name


class TestNames:
    def test_the_package_exports_what_it_documents(self):
        assert xnano.terminal.__all__ == [
            'CapabilityStatus',
            'ColorProfile',
            'GraphicsCapabilities',
            'GraphicsProtocol',
            'KeyboardCapabilities',
            'OpenSettings',
            'OpeningTerminal',
            'Terminal',
            'TerminalCapabilities',
            'TerminalSettings',
            'capabilities',
            'iter',
            'iter_async',
            'open',
            'open_async',
        ]
        assert all(hasattr(xnano.terminal, name) for name in xnano.terminal.__all__)

    @pytest.mark.parametrize(
        'value_type',
        [
            xnano.terminal.TerminalCapabilities,
            xnano.terminal.KeyboardCapabilities,
            xnano.terminal.GraphicsCapabilities,
        ],
    )
    def test_the_values_are_frozen_dataclasses_with_slots(self, value_type):
        assert dataclasses.is_dataclass(value_type)
        fields = tuple(field.name for field in dataclasses.fields(value_type))
        assert value_type.__slots__ == fields
        assert value_type.__dataclass_params__.frozen

    @pytest.mark.parametrize(
        ('name', 'values'),
        [
            ('ColorProfile', COLOR_PROFILES),
            ('GraphicsProtocol', GRAPHICS_PROTOCOLS),
            ('CapabilityStatus', CAPABILITY_STATUSES),
        ],
    )
    def test_the_names_of_the_answers_are_public_types(self, name, values):
        assert name in xnano.terminal.__all__
        assert typing.get_args(getattr(xnano.terminal, name)) == values
        assert set(typing.get_args(getattr(xnano_core, name))) == set(values)

    @pytest.mark.parametrize(
        'name', ['ColorProfile', 'GraphicsProtocol', 'CapabilityStatus']
    )
    def test_the_names_of_the_answers_are_the_names_of_the_core(self, name):
        assert getattr(xnano.terminal, name) is getattr(xnano_core, name)


class TestTerminalExpressions:
    def test_the_size_of_the_terminal_is_the_size_of_the_device_of_the_core(self):
        import xnano.expressions

        assert xnano.expressions.TerminalWidth is xnano_core.DeviceWidth
        assert xnano.expressions.TerminalHeight is xnano_core.DeviceHeight

    def test_the_names_of_the_core_are_not_expressions_of_xnano(self):
        import xnano.expressions

        for name in ('DeviceWidth', 'DeviceHeight'):
            assert name not in xnano.expressions.__all__
            with pytest.raises(AttributeError):
                getattr(xnano.expressions, name)
        assert 'TerminalWidth' in xnano.expressions.__all__
        assert 'TerminalHeight' in xnano.expressions.__all__

    def test_a_canvas_that_is_not_on_the_screen_has_the_size_it_was_created_with(self):
        from xnano.expressions import TerminalHeight, TerminalWidth

        with xnano.new(width=12, height=3) as canvas:
            assert canvas.evaluate(TerminalWidth) == 12
            assert canvas.evaluate(TerminalHeight) == 3
