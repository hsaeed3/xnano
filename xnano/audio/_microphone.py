"""
xnano.audio._microphone

The microphone: its level and level history.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from xnano._internal import _optional

_optional.require('audio', needed_for='xnano.audio.Microphone')

from xnano_audio import TerminalAudioError, TerminalMicrophone  # noqa: E402

# The hook for values an extension provides.
from xnano_core._xnano_core import _external  # noqa: E402

if TYPE_CHECKING:
    from xnano._schema._axes import NumericExpression
    from xnano.canvas import Canvas

__all__ = ['Microphone']

_LEVEL_NAME: Final = 'audio.level'
"""The name the canvas's runtime knows the microphone level by."""


class Microphone:
    """
    The canvas's microphone: how loud the sound at the default input device is.

    Get it from [`AudioDevice.microphone`][xnano.audio.AudioDevice.microphone], which is
    ``canvas.audio.microphone``. The input device is opened the first time something reads
    the level, the level history, the sample rate or the channel count. On a computer without
    an input device, without permission to record, or on a canvas from ``new()``, which has no
    device, the level is ``0`` and the history is empty.

    The level is an expression, so it drives anything an expression can: a position, a size,
    a color, an effect.

    Maps to [`xnano_audio.TerminalMicrophone`][xnano_audio.TerminalMicrophone].

    Attributes:
        level: The current level from 0.0 to 1.0, as an expression.
        is_open: Whether the input device is open. Reading it never opens the device.
        sample_rate: The input device's sample rate in hertz, or ``None`` when there is no
            input device.
        channels: The input device's channel count, or ``None`` when there is no input device.

    Examples:
        ```python
        import xnano

        with xnano.new(width=20, height=1) as canvas:
            microphone = canvas.audio.microphone
            assert canvas.inspect(microphone.level) == 0.0
            assert not microphone.is_open
            assert microphone.sample_rate is None
        ```
    """

    def __init__(self, canvas: Canvas[object, object]) -> None:
        """
        Create the microphone of a canvas. Use ``canvas.audio.microphone`` instead of calling this.

        Args:
            canvas: The canvas the microphone belongs to.
        """
        self._canvas = canvas
        self._device: TerminalMicrophone | None = None
        self._is_unavailable = False
        self._level = _external(_LEVEL_NAME, True)

    @property
    def level(self) -> NumericExpression:
        """
        The microphone's current level from 0.0 to 1.0, as an expression.

        Reading it opens the default input device the first time a frame evaluates it.
        Without an input device, without permission, or on a canvas without a device, the
        level is ``0``.

        Examples:
            ```python
            import xnano

            with xnano.new(width=20, height=2) as canvas:
                meter = canvas.write('#')
                meter.x = canvas.audio.microphone.level * 19
                assert canvas.inspect(canvas.audio.microphone.level) == 0.0
            ```
        """
        self._canvas._require_open()
        return self._level

    def level_history(self, count: int) -> list[float]:
        """
        Return the last ``count`` microphone levels, oldest first.

        Opens the default input device if it is not open yet. The list is empty without an
        input device, without permission, or on a canvas without a device.

        Args:
            count: How many levels to return.

        Returns:
            The levels, each from 0.0 to 1.0, one for each buffer of sound the device has
            delivered.
        """
        canvas = self._canvas
        canvas._require_open()

        def read() -> list[float]:
            device = self._open()
            return [] if device is None else device.level_history(count)

        return canvas._host.call(read)

    @property
    def is_open(self) -> bool:
        """
        Whether the input device is open and listening.

        This only reports; it never opens the device, so it is ``False`` until the level, the
        level history, the sample rate or the channel count has been read.
        """
        canvas = self._canvas
        canvas._require_open()

        def read() -> bool:
            return self._device is not None and self._device.is_open

        return canvas._host.call(read)

    @property
    def sample_rate(self) -> int | None:
        """
        The input device's sample rate in hertz.

        Opens the default input device if it is not open yet. It is ``None`` without an input
        device, without permission, or on a canvas without a device.
        """
        canvas = self._canvas
        canvas._require_open()

        def read() -> int | None:
            device = self._open()
            return None if device is None else device.sample_rate

        return canvas._host.call(read)

    @property
    def channels(self) -> int | None:
        """
        The input device's channel count.

        Opens the default input device if it is not open yet. It is ``None`` without an input
        device, without permission, or on a canvas without a device.
        """
        canvas = self._canvas
        canvas._require_open()

        def read() -> int | None:
            device = self._open()
            return None if device is None else device.channels

        return canvas._host.call(read)

    def _open(self) -> TerminalMicrophone | None:
        """The input device, opened on first use; ``None`` when there is none. Runs on the loop."""
        if not self._canvas._is_realtime:
            return None
        if self._device is None and not self._is_unavailable:
            try:
                self._device = TerminalMicrophone()
            except TerminalAudioError:
                self._is_unavailable = True
        return self._device

    def _read_level(self) -> float:
        """The level an expression reads. Runs on the loop."""
        device = self._open()
        return 0.0 if device is None else device.level

    def _close(self) -> None:
        """Release the input device. Runs on the loop."""
        device = self._device
        self._device = None
        if device is not None:
            device.close()
