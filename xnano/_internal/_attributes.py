"""
xnano._internal._attributes

A base class that refuses to set an attribute the object does not have.
"""

from __future__ import annotations

import difflib
import functools
import inspect
from collections.abc import Callable
from typing import ParamSpec, TypeVar

__all__ = ['_SealedAttributes', 'refuse_unknown_keywords']

_Parameters = ParamSpec('_Parameters')
_Result = TypeVar('_Result')


def _is_settable(owner: type, name: str) -> bool:
    descriptor = inspect.getattr_static(owner, name)
    if isinstance(descriptor, property):
        return descriptor.fset is not None
    return hasattr(descriptor, '__set__')


class _SealedAttributes:
    """
    Refuse an assignment to a public name the object does not declare.

    Without this a typo such as ``canvas.cursor.is_visble = False`` would create a new
    attribute and silently change nothing. The object is sealed at the end of its
    ``__init__`` by calling ``_seal()``.
    """

    def _seal(self) -> None:
        object.__setattr__(self, '_is_sealed', True)

    def __setattr__(self, name: str, value: object) -> None:
        """Set an attribute, or raise ``AttributeError`` for an unknown public name."""
        if (
            name[:1] != '_'
            and self.__dict__.get('_is_sealed')
            and not hasattr(type(self), name)
            and name not in self.__dict__
        ):
            kind = type(self).__name__
            settable = sorted(
                key
                for key in dir(type(self))
                if key[:1] != '_' and _is_settable(type(self), key)
            )
            close = difflib.get_close_matches(name, settable, n=1)
            hint = f' Did you mean {close[0]!r}?' if close else ''
            raise AttributeError(
                f'{kind} has no attribute called {name!r}, so assigning to it would change '
                f'nothing.{hint} The attributes you can assign are: {", ".join(settable)}.'
            )
        object.__setattr__(self, name, value)


def refuse_unknown_keywords(
    function: Callable[_Parameters, _Result],
) -> Callable[_Parameters, _Result]:
    """
    Answer an unknown keyword with the names the function does take.

    Without this Python says only that the function got an unexpected keyword argument.
    """
    names = [
        parameter.name
        for parameter in inspect.signature(function).parameters.values()
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY
    ]
    known = frozenset(names)
    label = function.__qualname__

    @functools.wraps(function)
    def checked(*arguments: _Parameters.args, **keywords: _Parameters.kwargs) -> _Result:
        for name in keywords:
            if name not in known:
                close = difflib.get_close_matches(name, names, n=2)
                hint = (
                    f' Did you mean {" or ".join(repr(item) for item in close)}?'
                    if close
                    else ''
                )
                raise TypeError(
                    f'{label}() has no setting called {name!r}.{hint} The settings are '
                    f'{", ".join(names)}.'
                )
        return function(*arguments, **keywords)

    return checked
