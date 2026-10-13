"""
tests.helpers

Shared test machinery for ``xnano-core``.
"""

from __future__ import annotations

from xnano_core._xnano_core import Buffer, _reference

X = _reference('X', 'numeric_property')
Y = _reference('Y', 'numeric_property')
Width = _reference('Width', 'numeric_property')
Height = _reference('Height', 'numeric_property')
Position = _reference('Position', 'property')
Size = _reference('Size', 'property')
Bounds = _reference('Bounds', 'value')
TimeElapsed = _reference('TimeElapsed', 'numeric')
TimeDelta = _reference('TimeDelta', 'numeric')
TimeElapsedMilliseconds = _reference('TimeElapsedMilliseconds', 'numeric')
TimeDeltaMilliseconds = _reference('TimeDeltaMilliseconds', 'numeric')
Frame = _reference('Frame', 'numeric')
FPS = _reference('FPS', 'numeric')
Focused = _reference('Focused', 'value')
Running = _reference('Running', 'value')
DeviceWidth = _reference('DeviceWidth', 'numeric')
DeviceHeight = _reference('DeviceHeight', 'numeric')


def rows(buffer: Buffer) -> list[str]:
    """The buffer's plain text rows, with trailing blanks trimmed."""
    return buffer.render(format='text').split('\n')
