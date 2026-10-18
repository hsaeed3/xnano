"""
xnano._internal._annotation_names

The names that the annotations of the public effect classes use and that those modules cannot
import while they load.
"""

from __future__ import annotations


def bind_annotation_names() -> None:
    """
    Add the names the annotations of the effect modules use to the globals of those modules.

    ``typing.get_type_hints`` reads an annotation in the globals of the module that defines it.
    These names are imported only for type checkers where the annotations are written, because
    the modules import each other in a circle (``xnano.canvas`` reads ``xnano.effects._properties``,
    ``xnano.context`` reads ``xnano.effects._controller``) and the unions of the effect classes
    are built from the classes that ``xnano.effects._properties`` is still defining while it
    loads. This runs once, at the end of ``xnano/__init__.py``, when every module has loaded.
    """
    import xnano._internal._dynamic_operations as dynamic_operations
    import xnano._schema._effects as effects_schema
    import xnano.effects._controller as controller
    import xnano.effects._properties as properties
    from xnano.canvas import Canvas
    from xnano.context import Context
    from xnano.placement import Placement

    dynamic_operations.Canvas = Canvas
    dynamic_operations.Placement = Placement
    properties.RenderableEffect = effects_schema.RenderableEffect
    properties.PlayableEffect = effects_schema.PlayableEffect
    controller.Context = Context
