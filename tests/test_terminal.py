import pytest
from unittest import mock
from xnano.terminal import Terminal, Frame, restore_terminal
from xnano.layout import Rectangle, Position, Size
from xnano import _core
from xnano.widgets import Block


def test_frame_cannot_be_instantiated_directly():
    with pytest.raises(
        TypeError, match="Frame instances are created internally"
    ):
        Frame()


def test_frame_from_and_to_core():
    mock_core_frame = mock.Mock(spec=_core.Frame)
    frame = Frame._from_core(mock_core_frame)
    assert frame._to_core() is mock_core_frame


def test_frame_methods():
    mock_core_frame = mock.Mock(spec=_core.Frame)
    # Mock area returning native core.Rect
    mock_rect = _core.Rect(0, 0, 80, 24)
    mock_core_frame.area.return_value = mock_rect

    frame = Frame._from_core(mock_core_frame)

    # Area
    area = frame.area()
    assert isinstance(area, Rectangle)
    assert area.x == 0
    assert area.y == 0
    assert area.width == 80
    assert area.height == 24

    # render_widget
    mock_widget = mock.Mock()
    mock_widget._to_core.return_value = "native_widget"
    frame.render_widget(mock_widget, area)
    assert mock_core_frame.render_widget.call_count == 1
    w_arg, r_arg = mock_core_frame.render_widget.call_args[0]
    assert w_arg == "native_widget"
    assert r_arg.x == area.x and r_arg.width == area.width

    # render_stateful_widget
    mock_state = mock.Mock()
    mock_state._to_core.return_value = "native_state"
    frame.render_stateful_widget(mock_widget, area, mock_state)
    assert mock_core_frame.render_stateful_widget.call_count == 1
    w_arg, r_arg, s_arg = mock_core_frame.render_stateful_widget.call_args[0]
    assert w_arg == "native_widget"
    assert r_arg.x == area.x and r_arg.width == area.width
    assert s_arg == "native_state"

    # set_cursor_position
    pos = Position(5, 5)
    frame.set_cursor_position(pos)
    assert mock_core_frame.set_cursor_position.call_count == 1
    p_arg = mock_core_frame.set_cursor_position.call_args[0][0]
    assert p_arg.x == 5 and p_arg.y == 5

    # hide_cursor
    frame.hide_cursor()
    mock_core_frame.hide_cursor.assert_called_once()

    # process_effects
    mock_effect_mgr = mock.Mock()
    mock_effect_mgr._to_core.return_value = "native_mgr"
    frame.process_effects(mock_effect_mgr, 500, area)
    assert mock_core_frame.process_effects.call_count == 1
    m_arg, d_arg, r_arg = mock_core_frame.process_effects.call_args[0]
    assert m_arg == "native_mgr"
    assert d_arg == 500
    assert r_arg.x == area.x and r_arg.width == area.width

    # count
    mock_core_frame.count.return_value = 42
    assert frame.count() == 42


def test_terminal_management():
    # Mock the native Terminal.init classmethod
    mock_core_term = mock.Mock(spec=_core.Terminal)
    mock_core_term.size.return_value = _core.Size(120, 40)
    mock_core_term.__enter__ = mock.Mock(return_value=mock_core_term)
    mock_core_term.__exit__ = mock.Mock(return_value=None)

    with mock.patch(
        "xnano._core.Terminal.init", return_value=mock_core_term
    ) as mock_init:
        term = Terminal()
        assert term._to_core() is mock_core_term
        mock_init.assert_called_once()

        # repr
        assert repr(term) == "Terminal()"

        # size
        size = term.size()
        assert isinstance(size, Size)
        assert size.width == 120
        assert size.height == 40

        # clear
        term.clear()
        mock_core_term.clear.assert_called_once()

        # draw
        draw_calls = []

        def my_draw_cb(frame):
            draw_calls.append(frame)

        term.draw(my_draw_cb)

        # The native draw will call the bridge callback
        mock_core_term.draw.assert_called_once()
        bridge_cb = mock_core_term.draw.call_args[0][0]

        # Call the bridge callback with a mock native frame
        mock_native_frame = mock.Mock(spec=_core.Frame)
        bridge_cb(mock_native_frame)

        assert len(draw_calls) == 1
        assert isinstance(draw_calls[0], Frame)
        assert draw_calls[0]._to_core() is mock_native_frame

        # Test sequence draw
        mock_widget = mock.Mock()
        mock_widget._to_core.return_value = "native_widget"
        mock_state = mock.Mock()
        mock_state._to_core.return_value = "native_state"
        mock_area = Rectangle(0, 0, 10, 10)

        mock_native_frame.area.return_value = _core.Rect(0, 0, 80, 24)
        mock_native_frame.render_widget.reset_mock()
        mock_native_frame.render_stateful_widget.reset_mock()

        term.draw(
            [
                mock_widget,
                (mock_widget, mock_area),
                (mock_widget, mock_area, mock_state),
            ]
        )

        bridge_cb_seq = mock_core_term.draw.call_args[0][0]
        bridge_cb_seq(mock_native_frame)

        assert mock_native_frame.render_widget.call_count == 2
        assert mock_native_frame.render_stateful_widget.call_count == 1

        # Test sequence draw invalid tuple length
        term.draw([(mock_widget, mock_area, mock_state, "extra")])
        bridge_cb_err = mock_core_term.draw.call_args[0][0]
        with pytest.raises(ValueError, match="Invalid draw tuple"):
            bridge_cb_err(mock_native_frame)

        # Test single widget draw
        real_widget = Block()
        mock_native_frame.render_widget.reset_mock()
        term.draw(real_widget)
        bridge_cb_single = mock_core_term.draw.call_args[0][0]
        bridge_cb_single(mock_native_frame)
        assert mock_native_frame.render_widget.call_count == 1

        # Test single string draw
        mock_native_frame.render_widget.reset_mock()
        term.draw("Hello")
        bridge_cb_str = mock_core_term.draw.call_args[0][0]
        bridge_cb_str(mock_native_frame)
        assert mock_native_frame.render_widget.call_count == 1

        # Test callback returning sequence of layout tuples
        mock_native_frame.render_widget.reset_mock()
        mock_native_frame.render_stateful_widget.reset_mock()
        term.draw(
            lambda frame: [
                mock_widget,
                (mock_widget, mock_area),
                (mock_widget, mock_area, mock_state),
            ]
        )
        bridge_cb_cbseq = mock_core_term.draw.call_args[0][0]
        bridge_cb_cbseq(mock_native_frame)
        assert mock_native_frame.render_widget.call_count == 2
        assert mock_native_frame.render_stateful_widget.call_count == 1

        # Test callback returning single widget
        mock_native_frame.render_widget.reset_mock()
        term.draw(lambda frame: mock_widget)
        bridge_cb_cbsingle = mock_core_term.draw.call_args[0][0]
        bridge_cb_cbsingle(mock_native_frame)
        assert mock_native_frame.render_widget.call_count == 1

        # Test callback returning sequence invalid tuple length
        term.draw(
            lambda frame: [(mock_widget, mock_area, mock_state, "extra")]
        )
        bridge_cb_cberr = mock_core_term.draw.call_args[0][0]
        with pytest.raises(ValueError, match="Invalid draw tuple"):
            bridge_cb_cberr(mock_native_frame)

        # Test Frame.render sequence/widget rendering
        # 1. Sequence rendering
        mock_native_frame.render_widget.reset_mock()
        mock_native_frame.render_stateful_widget.reset_mock()
        frame = Frame._from_core(mock_native_frame)
        frame.render(
            [
                mock_widget,
                (mock_widget, mock_area),
                (mock_widget, mock_area, mock_state),
            ]
        )
        assert mock_native_frame.render_widget.call_count == 2
        assert mock_native_frame.render_stateful_widget.call_count == 1

        # 2. Single widget rendering
        mock_native_frame.render_widget.reset_mock()
        frame.render(mock_widget)
        assert mock_native_frame.render_widget.call_count == 1

        # 3. Invalid tuple length in Frame.render
        with pytest.raises(ValueError, match="Invalid draw tuple"):
            frame.render([(mock_widget, mock_area, mock_state, "extra")])

        # Context manager
        with term as t:
            assert t is term
            mock_core_term.__enter__.assert_called_once()

        mock_core_term.__exit__.assert_called_once()


def test_restore_terminal():
    with mock.patch("xnano._core.restore_terminal") as mock_restore:
        restore_terminal()
        mock_restore.assert_called_once()
