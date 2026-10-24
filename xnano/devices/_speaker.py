"""
xnano.devices._speaker

The speaker of a terminal: what it plays, the effects on everything it plays, and what it
recorded on a canvas without a sound device.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from xnano.audio._audio import Audio

if TYPE_CHECKING:
    from typing_extensions import Unpack

    from xnano._schema._content import PlaySource
    from xnano._schema._media import PlayOptions
    from xnano.audio._notes import PlayHandle
    from xnano.canvas import Canvas
    from xnano.effects._properties import PlayableEffectProperties
    from xnano.hooks._context import Context

__all__ = ['Speaker']


class Speaker:
    """
    The speaker of a terminal: notes, melodies, sounds and playable components.

    Get it from [`Canvas.speaker`][xnano.canvas.Canvas.speaker], or from ``context.speaker``
    inside a hook. On the screen it plays through the computer's sound device. A canvas from
    ``new()`` has no device: what it plays is recorded at the canvas's time, and
    [`render`][xnano.devices.Speaker.render] turns it into [`Audio`][xnano.Audio], the way
    ``screen.render()`` turns the screen into text.

    Attributes:
        fx: The sound effects of everything this speaker plays, one method for each effect.
        is_available: Whether sound can be played: always without a device, otherwise when
            one exists.
        is_offline: Whether this speaker records sound instead of playing it on a device.

    Examples:
        ```python
        import xnano

        with xnano.new(width=8, height=1, bpm=100) as canvas:
            canvas.speaker.play('C4 E4 G4:2 rest C5+E5+G5', instrument='bell')
            canvas.clock.step(delta_seconds=1.0)
            assert canvas.speaker.render().duration_milliseconds == 1000.0
        ```
    """

    __slots__ = ('_canvas', '_context')

    def __init__(
        self,
        canvas: Canvas[object, object],
        context: Context[object, object] | None = None,
    ) -> None:
        """
        Create a view of the speaker. Use ``canvas.speaker`` or ``context.speaker`` instead.

        Args:
            canvas: The root canvas the speaker belongs to.
            context: The hook's context, which notes what a component reads; ``None`` outside
                a hook.
        """
        self._canvas = canvas
        self._context = context

    def __repr__(self) -> str:
        return f'Speaker(is_offline={self.is_offline})'

    def play(self, playable: PlaySource, /, **options: Unpack[PlayOptions]) -> PlayHandle:
        """
        Play a note, audio, a symbol name, a melody or a sequence of those, and return at once.

        ``playable`` is a [`Note`][xnano.Note], a [`Melody`][xnano.audio.Melody], a
        [`Audio`][xnano.Audio], a playable component, the name of a registered symbol, a note
        name such as ``'C#4'``, a MIDI number such as ``60``, a frequency in hertz, melody text,
        or a sequence of those that plays one after another. A ``str`` is a symbol name first;
        if no symbol has that name it is a note name, a frequency such as ``'440hz'`` or melody
        text. Melody text has spaces, ``:2`` holds a note for two beats, ``rest`` is a silence,
        ``+`` joins a chord and ``|`` marks a bar: ``'C4 E4 G4:2 rest C5+E5+G5'``. An option you
        pass here replaces the same value on a ``Note``, so
        ``play(note('C4'), instrument='violin')`` plays the violin.

        Args:
            playable: What to play.
            options: The settings of [`PlayOptions`][xnano.devices.PlayOptions]: ``instrument``,
                ``beats``, ``velocity``, ``effects``, ``volume``, ``pan`` and ``at_beat``.

        Returns:
            A [`PlayHandle`][xnano.audio.PlayHandle] that tells when the sound is over.

        Raises:
            ValueError: A name is not a known sound, note or melody, or an option is out of
                range. The message suggests the closest names.
            TypeError: ``playable`` cannot be played.
        """
        return self._canvas._play(playable, options)

    @property
    def fx(self) -> PlayableEffectProperties:
        """
        The sound effects of everything this speaker plays, one method for each effect.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1) as canvas:
                canvas.speaker.fx.reverb(mix=0.3)
                canvas.speaker.play('C4')
                canvas.clock.step(delta_seconds=0.5)
                assert canvas.speaker.render().duration_milliseconds >= 500.0
            ```
        """
        return self._canvas._audio_device().fx

    @property
    def is_available(self) -> bool:
        """Whether sound can be played: always without a device, otherwise when one exists."""
        return self._canvas._audio_device().is_available

    @property
    def is_offline(self) -> bool:
        """Whether this speaker records sound instead of playing it on a device."""
        return self._canvas._audio_device().is_offline

    def render(self) -> Audio:
        """
        Turn what was played since the previous call into audio, and forget it.

        On a canvas without a sound device everything played is recorded at the canvas's time;
        this mixes it into mono audio that starts at the previous call, so a program or a test
        can listen to it, save it or compare it. A note that rings on past now continues in
        the next call.

        Returns:
            The [`Audio`][xnano.Audio], as long as the time that passed since the previous
            call.

        Raises:
            TerminalError: The speaker plays on a device, so nothing was recorded.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1, fps=10) as canvas:
                canvas.speaker.play('C4', instrument='bell')
                canvas.clock.step()
                audio = canvas.speaker.render()
                assert audio.duration_milliseconds == 100.0
                assert audio.peak > 0.0
            ```
        """
        return Audio(self._canvas._audio_device().render_sound())
