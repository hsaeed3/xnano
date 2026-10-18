"""
xnano._schema._generics

The type variables for the dependencies and state of a canvas, the ones that follow the type of a
value, a target or a field through a function, the type of the numbers of a region, and the
parameter specification of a component function.
"""

from __future__ import annotations

import sys

if sys.version_info >= (3, 13):
    from typing import Never, ParamSpec, TypeVar
else:
    from typing_extensions import Never, ParamSpec, TypeVar

DepsT = TypeVar('DepsT', default=None)
"""The type of the dependencies a canvas was given with ``new(deps=...)``, or ``None``."""

StateT = TypeVar('StateT', default=None)
"""The type of the dataclass a canvas keeps as its state, or ``None`` without one."""

ValueT = TypeVar('ValueT')
"""The type of a value that a function returns as it received it or looks up by its type."""

WrittenDepsT = TypeVar('WrittenDepsT')
"""The dependencies type of a canvas that is written into another, whatever it is."""

WrittenStateT = TypeVar('WrittenStateT')
"""The state type of a canvas that is written into another, whatever it is."""

DepsT_co = TypeVar('DepsT_co', covariant=True, default=None)

StateT_co = TypeVar('StateT_co', covariant=True, default=None)

NumberT_co = TypeVar('NumberT_co', bound=float, covariant=True, default=float)
"""
The type of the numbers a region measures its start and its length in: ``int`` for a region on
the screen, ``float`` for a region on the timeline. A region left unparameterized is either.
"""

DepsT_contra = TypeVar('DepsT_contra', contravariant=True, default=Never)

StateT_contra = TypeVar('StateT_contra', contravariant=True, default=Never)

TargetT = TypeVar('TargetT')
"""The type of what an operation is piped onto, which comes back as it went in."""

StateFieldT = TypeVar('StateFieldT')
"""The type of one field of a canvas's state dataclass."""

StateRootT = TypeVar('StateRootT')
"""The type of the state dataclass that a field is read from."""

ParametersT = ParamSpec('ParametersT')
"""The parameters a component function takes after its context."""
