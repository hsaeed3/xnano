"""xnano.grids

---

Build declarative layouts from named ``Field`` values. Grids can nest,
share state, react to hooks, and use the same layout on terminal and web.
"""

from __future__ import annotations

import abc
import dataclasses
import inspect
import itertools
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Sequence,
    TypedDict,
    get_args,
    overload,
)

if sys.version_info < (3, 11):
    from typing_extensions import (
        NotRequired,
        Unpack,
        dataclass_transform,
    )
else:
    from typing import NotRequired, Unpack, dataclass_transform

from xnano.area import (
    Alignment,
    Area,
    Padding,
    PaddingLike,
    VerticalAlignment,
    align_area,
)
from xnano.colors import ColorLike
from xnano.core.interface import AbstractInterface
from xnano.core.layout import LayoutConstraint
from xnano.fields import (
    UNSET,
    ClassNameLike,
    Field,
    GridFieldInfo,
    _normalize_slide_axes,
)
from xnano.types import (
    Axis,
    Border,
    CharacterModifier,
    Direction,
    Frame,
    FrameTitlePosition,
    Side,
    SizingLike,
    frame_from_field,
)
from xnano.utils.deprecation import (
    resolve_color_alias,
    resolve_renamed_alias,
    warn_color_alias,
    warn_renamed_attribute,
)
from xnano.utils.responsive import (
    breakpoint_for_width,
    collect_responsive_overrides,
    responsive_noop,
)

if TYPE_CHECKING:
    from xnano.effects import (
        AbstractEffect,
        EffectHandle,
        EffectInterpolation,
        EffectMotion,
        KnownEffectKind,
    )
    from xnano.types import Sizing

_GRID_RESERVED: frozenset[str] = frozenset(
    {
        "grid_settings",
        "visible",
        "z",
        "columns",
        "rows",
    }
)


_FIELD_MOUSE_KINDS: frozenset[str] = frozenset({"press", "drag", "release"})


_GRID_MODIFIER_FLAG_KEYS: tuple[str, ...] = (
    "bold",
    "dim",
    "italic",
    "underline",
    "slow_blink",
    "rapid_blink",
    "reversed",
)
"""Boolean ``grid_set_field`` keys that toggle character modifiers.

``GridFieldInfo`` stores modifiers as a single ``modifiers`` sequence,
so these flags are translated into it before ``dataclasses.replace``.
"""


_GRID_FIELD_CONFIG_KEYS: frozenset[str] = frozenset(
    {
        "strict",
        "slide",
        "visible",
        "z",
        "wireframe",
        "foreground",
        "background",
        "fill",
        "width",
        "height",
        "gap",
        "direction",
        "horizontal_align",
        "vertical_align",
        "border",
        "border_sides",
        "border_color",
        "title",
        "title_position",
        "padding",
        "margin",
        "modifiers",
        "class_name",
        "bold",
        "dim",
        "italic",
        "underline",
        "slow_blink",
        "rapid_blink",
        "reversed",
    }
)


_GRID_FIELD_IMMUTABLE_KEYS: frozenset[str] = frozenset(
    {
        "default",
        "default_factory",
        "init",
        "state",
    }
)


_GridLayoutConstraint = LayoutConstraint
"""Local name for the shared layout constraint type used while sizing grids."""


@dataclasses.dataclass(frozen=True, slots=True)
class _GridFieldHit:
    grid: "BaseGrid"
    field_name: str
    area: Area
    slot_area: Area
    parent_area: Area
    slide_axes: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True, slots=True)
class _GridSlideCapture:
    grid: "BaseGrid"
    field_name: str
    parent_area: Area
    slot_area: Area
    grab_x: int
    grab_y: int
    slide_axes: list[str]


class GridSettings(TypedDict, total=False):
    """Rendering, layout, and frame settings for a ``BaseGrid`` subclass.

    Attributes:
        foreground: Foreground color of rendered content.
        background: Background color of the grid frame.
        direction: Direction used to lay out fields.
        gap: Cells between fields.
        border: Border style around the grid.
        border_sides: Border sides to display.
        border_color: Color of the border.
        title: Text displayed in the grid frame.
        title_position: Alignment of the frame title.
        padding: Space between the frame and its content.
        bold: Whether content is bold.
        dim: Whether content is dimmed.
        italic: Whether content is italic.
        underline: Whether content is underlined.
        slow_blink: Whether content blinks slowly.
        rapid_blink: Whether content blinks rapidly.
        reversed: Whether foreground and background are reversed.
        strict: Whether field assignments are validated.
    """

    foreground: NotRequired[ColorLike]
    """The foreground color of the grid's content."""
    background: NotRequired[ColorLike]
    """The background color of the grid's frame area."""
    direction: NotRequired[Direction]
    """The direction in which content within this grid should be laid out."""
    gap: NotRequired[int]
    """The gap between fields in this grid."""
    border: NotRequired[Border]
    """The border style to be applied onto the outer frame of the grid."""
    border_sides: NotRequired[list[Side]]
    """The sides of the border to be applied onto the outer frame of the grid."""
    border_color: NotRequired[ColorLike]
    """The color of the border."""
    title: NotRequired[str]
    """The title to be displayed around the outer frame of the grid."""
    title_position: NotRequired[FrameTitlePosition]
    """The position of the title within the outer frame of the grid."""
    padding: NotRequired[PaddingLike]
    """The padding to be applied around the content area of the grid."""
    bold: NotRequired[bool]
    """Whether the grid should be rendered in bold."""
    dim: NotRequired[bool]
    """Whether the grid should be rendered in dim."""
    italic: NotRequired[bool]
    """Whether the grid should be rendered in italic."""
    underline: NotRequired[bool]
    """Whether the grid should be rendered in underline."""
    slow_blink: NotRequired[bool]
    """Whether the grid should be rendered in slow blink."""
    rapid_blink: NotRequired[bool]
    """Whether the grid should be rendered in rapid blink."""
    reversed: NotRequired[bool]
    """Whether the grid should be rendered in reversed color."""
    strict: NotRequired[bool]
    """When ``True`` (the default), all field values are validated against their
    type annotations during grid construction."""


def _resolve_settings_color_alias(
    settings: GridSettings | None,
) -> Any:
    """Map a deprecated ``color`` grid setting onto ``foreground``.

    ``foreground`` wins when both are given, matching every other
    ``color`` alias in the library.
    """
    if not settings or "color" not in settings:
        return settings
    resolved = dict(settings)
    color = resolved.pop("color")
    warn_color_alias(stacklevel=4)
    resolved.setdefault("foreground", color)
    return resolved


def _merge_grid_settings(
    bases: tuple[type, ...],
    class_kwargs: GridSettings,
    declared: GridSettings | None = None,
) -> GridSettings:
    """Merge grid settings from bases, class-header kwargs, and body dict."""
    class_kwargs = _resolve_settings_color_alias(class_kwargs)
    declared = _resolve_settings_color_alias(declared)
    merged: GridSettings = {}
    for base in bases:
        if base is object:
            continue
        parent = getattr(base, "grid_settings", None)
        if parent:
            merged = {**merged, **parent}
    if class_kwargs:
        merged = {**merged, **class_kwargs}
    if declared:
        merged = {**merged, **declared}
    return merged


def _frame_axis_size(frame: Frame | None, direction: Direction) -> int:
    """Return the chrome thickness a grid frame consumes along an axis."""
    if frame is None:
        return 0
    size = 0
    if frame.border is not None:
        sides = frame.border_sides
        if direction == "vertical":
            edges = ("top", "bottom")
        else:
            edges = ("left", "right")
        size += 2 if sides is None else sum(edge in sides for edge in edges)
    if frame.padding is not None:
        padding = Padding.parse(frame.padding)
        size += (
            padding.vertical if direction == "vertical" else padding.horizontal
        )
    return size


def _grid_inner_width(area: Area, frame: Frame | None) -> int:
    """Return the content width inside a grid's own frame."""
    return max(0, area.width - _frame_axis_size(frame, "horizontal"))


def _grid_frame_size_for_field(
    field: GridFieldInfo,
    direction: Direction,
) -> int:
    size = 0
    if field.border is not None:
        sides = field.border_sides
        if direction == "vertical":
            if sides is None:
                size += 2
            else:
                if "top" in sides:
                    size += 1
                if "bottom" in sides:
                    size += 1
        else:
            if sides is None:
                size += 2
            else:
                if "left" in sides:
                    size += 1
                if "right" in sides:
                    size += 1

    if field.padding is not None:
        padding = Padding.parse(field.padding)
        if direction == "vertical":
            size += padding.vertical
        else:
            size += padding.horizontal

    if field.margin is not None:
        margin = Padding.parse(field.margin)
        if direction == "vertical":
            size += margin.vertical
        else:
            size += margin.horizontal

    return size


def _apply_field_modifier_flags(
    field_config: dict[str, Any],
    current_modifiers: Sequence[str] | None,
) -> dict[str, Any]:
    """Translate boolean modifier flags into a ``modifiers`` sequence.

    ``grid_set_field(bold=True)`` toggles the ``"bold"`` modifier on
    top of the config's ``modifiers`` (when given) or the field's
    current modifiers; ``bold=False`` removes it. The flag keys are
    consumed so ``dataclasses.replace`` only sees real
    ``GridFieldInfo`` attributes.
    """
    translated = dict(field_config)
    base = translated.get("modifiers")
    if base is None:
        base = current_modifiers or ()
    modifiers = list(base)
    for key in _GRID_MODIFIER_FLAG_KEYS:
        if key not in translated:
            continue
        enabled = bool(translated.pop(key))
        if enabled and key not in modifiers:
            modifiers.append(key)
        elif not enabled and key in modifiers:
            modifiers.remove(key)
    translated["modifiers"] = tuple(modifiers)
    return translated


def _expand_field_class_name_config(
    field_config: dict[str, Any],
) -> dict[str, Any]:
    """Expand a ``class_name`` config entry into derived field attributes.

    Resolves Tailwind classes lazily and fills in every
    derived attribute the caller did not pass explicitly — explicit
    keys always win, matching ``xnano.fields.Field``.
    """
    from xnano.tailwind import (
        normalize_tailwind_classes,
        resolve_tailwind_classes,
    )

    tokens = normalize_tailwind_classes(field_config["class_name"])
    resolved = resolve_tailwind_classes(tokens)
    expanded = dict(field_config)
    expanded["class_name"] = tokens
    derived_keys = (
        "foreground",
        "background",
        "border",
        "border_color",
        "border_sides",
        "padding",
        "margin",
        "gap",
        "width",
        "height",
        "horizontal_align",
        "direction",
    )
    for key in derived_keys:
        value = getattr(resolved, key)
        if value is not None and key not in field_config:
            expanded[key] = value
    if resolved.modifiers and "modifiers" not in field_config:
        expanded["modifiers"] = resolved.modifiers
    return expanded


def _grid_inset_area_for_margin(
    area: Area,
    margin: Padding,
) -> Area:
    """Shrink ``area`` by ``margin`` on each side, clamped to >= 0 size."""
    width = max(0, area.width - margin.horizontal)
    height = max(0, area.height - margin.vertical)
    return Area(
        x=area.x + min(margin.left, area.width),
        y=area.y + min(margin.top, area.height),
        width=width,
        height=height,
    )


def _grid_min_size_for_field(
    field: GridFieldInfo,
    direction: Direction,
) -> int:
    frame_size = _grid_frame_size_for_field(field, direction)
    if frame_size > 0:
        return frame_size + 1
    return 0


def _field_axis_sizing(
    field: GridFieldInfo,
    direction: Direction,
) -> "Sizing | None":
    """Return the ``Sizing`` that drives ``field``'s layout-axis split.

    The split runs along the parent's layout ``direction`` — the field's
    ``height`` for vertical layouts, ``width`` for horizontal.
    """
    return field.height if direction == "vertical" else field.width


def _field_cross_sizing(
    field: GridFieldInfo,
    direction: Direction,
) -> "Sizing | None":
    """Return the ``Sizing`` for ``field``'s cross axis (opposite the layout).

    The cross axis is the one the split does not size — the field's ``width``
    in a vertical grid, ``height`` in a horizontal one.
    """
    return field.width if direction == "vertical" else field.height


def _field_needs_content_measure(
    field: GridFieldInfo,
    direction: Direction,
) -> bool:
    """Return whether ``field`` must measure its content to lay out."""
    axis_sizing = _field_axis_sizing(field, direction)
    return axis_sizing is not None and axis_sizing.is_fit


def _sizing_to_constraint(
    sizing: "Sizing",
    min_size: int,
    frame_size: int,
    content_length: int | None,
) -> _GridLayoutConstraint:
    """Lower a unified ``Sizing`` to a grid layout constraint."""
    if sizing.kind == "cells":
        length = sizing.value
        if sizing.minimum is not None:
            length = max(length, sizing.minimum)
        if sizing.maximum is not None:
            length = min(length, sizing.maximum)
        return _GridLayoutConstraint("length", max(min_size, length))
    if sizing.kind == "percent":
        return _GridLayoutConstraint("percentage", sizing.value)
    if sizing.kind == "ratio":
        return _GridLayoutConstraint("ratio", sizing.value, sizing.denominator)
    if sizing.kind == "fit":
        length = (content_length if content_length is not None else 0) + (
            frame_size
        )
        if sizing.minimum is not None:
            length = max(length, sizing.minimum)
        if sizing.maximum is not None:
            length = min(length, sizing.maximum)
        return _GridLayoutConstraint("content", max(min_size, length))
    # fraction / fill
    weight = sizing.value
    if weight == 0:
        return _GridLayoutConstraint("min", max(min_size, 1))
    if min_size > 0:
        return _GridLayoutConstraint("min", min_size)
    return _GridLayoutConstraint("fill", weight)


def _resolve_slot_area(
    session: Any,
    slot_area: Area,
    field: GridFieldInfo,
    value: Any,
    direction: Direction,
) -> Area:
    """Complete a slot's geometry from the split result and its cross sizing.

    ``split_layout`` sizes each slot along the parent's layout axis
    (through ``_layout_constraint_for_field``); this stage resolves the
    *cross* axis through the same unified ``Sizing`` model, so both ``width``
    and ``height`` are first-class in any grid rather than the cross axis being
    an afterthought. Both axes therefore flow from one vocabulary — the layout
    axis via the ratatui split, the cross axis via ``Sizing.resolve``.

    A cross-constrained slot keeps its top-left corner. When the cross axis has
    no sizing or fills (the common case), the split slot is already final and
    this returns it unchanged after a single attribute check.
    """
    cross = _field_cross_sizing(field, direction)
    if cross is None or cross.is_fill:
        return slot_area

    horizontal = direction == "vertical"
    available = slot_area.width if horizontal else slot_area.height
    content: int | None = None
    if cross.is_fit:
        cross_direction: Direction = "horizontal" if horizontal else "vertical"
        measured = session.measure_field_slot(value, cross_direction, field)
        if measured <= 0:
            return slot_area
        content = measured + _grid_frame_size_for_field(field, cross_direction)

    length = max(1, min(cross.resolve(available, content), available))
    if length >= available:
        return slot_area
    if horizontal:
        return align_area(
            slot_area,
            length,
            slot_area.height,
            horizontal=field.horizontal_align,
        )
    return align_area(
        slot_area,
        slot_area.width,
        length,
        vertical=field.vertical_align,
    )


def _grid_overlay_area(inner: Area, field: GridFieldInfo) -> Area:
    """Center an out-of-flow overlay field within the grid's content area.

    ``width``/``height`` size the floating box (percent, cells, or ratio);
    an unset or filling axis spans the whole area. The box is clamped to
    ``inner`` and centered on both axes.
    """
    width = inner.width
    height = inner.height
    if field.width is not None and not field.width.is_fill:
        width = max(1, min(field.width.resolve(inner.width), inner.width))
    if field.height is not None and not field.height.is_fill:
        height = max(1, min(field.height.resolve(inner.height), inner.height))
    return align_area(
        inner,
        width,
        height,
        horizontal=field.horizontal_align or "center",
        vertical=field.vertical_align or "middle",
    )


def _layout_constraint_for_field(
    field: GridFieldInfo,
    direction: Direction,
    content_length: int | None = None,
) -> _GridLayoutConstraint:
    """Lower a field's layout-axis ``Sizing`` to a split constraint.

    A field with no explicit sizing on the layout axis fills the available
    space (respecting any frame-imposed minimum) — the unified equivalent of a
    ``fraction(1)`` weight.
    """
    min_size = _grid_min_size_for_field(field, direction)
    frame_size = _grid_frame_size_for_field(field, direction)
    axis_sizing = _field_axis_sizing(field, direction)
    if axis_sizing is not None:
        return _sizing_to_constraint(
            axis_sizing, min_size, frame_size, content_length
        )
    if min_size > 0:
        return _GridLayoutConstraint("min", min_size)
    return _GridLayoutConstraint("fill", 1)


def _coerce_text_field(value: str, annotation: Any) -> Any:
    """Coerce a ``str`` to ``Text`` when the field is annotated ``Text``.

    A field typed as ``Text`` (bare or in a union such as ``str | Text``)
    may take a plain string default/value; it is wrapped in ``Text(value)``
    so the renderer sees a component. Any other annotation leaves the
    string untouched.

    Args:
        value: The plain string being assigned.
        annotation: The field's type annotation, if any.

    Returns:
        A ``Text`` wrapping ``value`` when the annotation names ``Text``,
        otherwise the original string.
    """
    if annotation is None:
        return value
    from xnano.components.text import Text

    candidates = get_args(annotation) or (annotation,)
    if any(candidate is Text for candidate in candidates):
        return Text(value)
    return value


class _FactoryDefault:
    """Signature placeholder shown for a field with a default factory."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "<factory>"


_FACTORY_DEFAULT = _FactoryDefault()


def _build_grid_init(
    all_fields: dict[str, GridFieldInfo],
    defaults: dict[str, Any],
) -> Callable[..., None]:
    """Build a keyword-only ``__init__`` for a grid class.

    A plain closure over the field metadata rather than generated source:
    grid fields are keyword-only, so ``**kwargs`` matches the call
    contract exactly, and an explicit ``__signature__`` preserves
    introspection (``inspect.signature``, editors, help output) without
    running ``exec``.
    """
    factory_names = {
        name
        for name, field in all_fields.items()
        if field.default_factory is not None
    }

    required: list[str] = []
    optional: list[str] = []
    no_init: list[str] = []

    for name, field in all_fields.items():
        if field.init is False:
            no_init.append(name)
        elif name in defaults:
            optional.append(name)
        else:
            required.append(name)

    accepted = frozenset(required) | frozenset(optional)

    def __init__(self: Any, **kwargs: Any) -> None:
        for name in kwargs:
            if name not in accepted:
                raise TypeError(
                    f"{type(self).__name__}() got an unexpected keyword "
                    f"argument {name!r}"
                )
        for name in required:
            if name not in kwargs:
                raise TypeError(
                    f"{type(self).__name__}() missing required keyword-only "
                    f"argument {name!r}"
                )
            setattr(self, name, kwargs[name])
        for name in optional:
            if name in kwargs:
                setattr(self, name, kwargs[name])
            elif name in factory_names:
                setattr(self, name, defaults[name]())
            else:
                setattr(self, name, defaults[name])
        for name in no_init:
            if name in factory_names:
                setattr(self, name, defaults[name]())
            elif name in defaults:
                setattr(self, name, defaults[name])
            else:
                setattr(self, name, None)
        self._grid_init_field_states()
        self._grid_validate_init()
        self.__post_init__()

    parameters = [
        inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    for name in required:
        parameters.append(
            inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY)
        )
    for name in optional:
        default = _FACTORY_DEFAULT if name in factory_names else defaults[name]
        parameters.append(
            inspect.Parameter(
                name, inspect.Parameter.KEYWORD_ONLY, default=default
            )
        )
    # ``setattr`` (rather than a direct attribute assignment) keeps the
    # type checker happy about stamping ``__signature__`` onto a plain
    # function; ``inspect.signature`` reads it back either way.
    setattr(__init__, "__signature__", inspect.Signature(parameters))
    return __init__


def _collect_field_mouse_handlers(
    cls: type,
    namespace: dict[str, Any],
    layout_fields: dict[str, GridFieldInfo],
) -> dict[str, Any]:
    """Map layout field names to ``@on_mouse`` / ``@on_click`` handlers."""
    from xnano import hooks as EventHooks

    handlers: dict[str, Any] = {}
    for base in reversed(cls.__mro__):
        if base is object or base is cls:
            continue
        handlers.update(getattr(base, "_grid_field_handlers", {}))

    for name, member in namespace.items():
        if not callable(member):
            continue
        field_name = getattr(member, EventHooks.ON_MOUSE_FIELD_ATTR, None)
        if field_name is None:
            continue
        if field_name not in layout_fields:
            raise TypeError(
                f"{cls.__name__}.{name} is bound to field {field_name!r}, "
                f"which is not a layout field on this grid"
            )
        handlers[field_name] = member
    return handlers


class _GridMetaNamespace(dict[str, Any]):
    def __init__(self) -> None:
        super().__init__()
        self._grid_fields: dict[str, GridFieldInfo] = {}
        self._grid_state_fields: dict[str, GridFieldInfo] = {}

    def __setitem__(self, key: str, value: Any) -> None:
        if isinstance(value, GridFieldInfo):
            if value.state:
                self._grid_state_fields[key] = value
            else:
                self._grid_fields[key] = value
        super().__setitem__(key, value)


@dataclass_transform(
    field_specifiers=(Field, GridFieldInfo, dataclasses.field),
    kw_only_default=True,
)
# ABCMeta (not plain type) so grids can mix in abc.ABC:
# ``class Window(BaseGrid, abc.ABC)`` needs the two metaclasses related.
class _GridMeta(abc.ABCMeta):
    @classmethod
    def __prepare__(
        mcls,
        name: str,
        bases: tuple[type, ...],
        **grid_config: Any,
    ) -> _GridMetaNamespace:
        return _GridMetaNamespace()

    def __new__(
        mcls,
        name: str,
        bases: tuple[type, ...],
        namespace: _GridMetaNamespace,
        **grid_config: Unpack[GridSettings],
    ) -> type:
        cls = super().__new__(mcls, name, bases, namespace)

        declared = namespace.get("grid_settings")
        cfg = _merge_grid_settings(
            bases,
            grid_config,
            declared if isinstance(declared, dict) else None,
        )
        setattr(cls, "grid_settings", cfg)
        setattr(cls, "_grid_strict", cfg.get("strict", True))

        frame = Frame(
            background=cfg.get("background"),
            border=cfg.get("border"),
            border_color=cfg.get("border_color"),
            border_sides=cfg.get("border_sides"),
            title=cfg.get("title"),
            title_position=cfg.get("title_position"),
            padding=cfg.get("padding"),
        )
        setattr(cls, "_grid_frame", None if frame.is_empty() else frame)
        setattr(cls, "_grid_direction", cfg.get("direction", "vertical"))
        setattr(cls, "_grid_gap", int(cfg.get("gap", 0)))

        fields: dict[str, GridFieldInfo] = {}
        state_fields: dict[str, GridFieldInfo] = {}
        defaults: dict[str, Any] = {}
        field_annotations: dict[str, Any] = {}

        for base in reversed(cls.__mro__):
            if base is cls:
                continue
            fields.update(getattr(base, "_grid_fields", {}))
            state_fields.update(getattr(base, "_grid_state_fields", {}))
            field_annotations.update(
                getattr(base, "_grid_field_annotations", {})
            )
            defaults.update(getattr(base, "_grid_defaults", {}))

        # 1. Explicitly-declared GridFieldInfo instances captured by _GridMetaNamespace
        all_captured = {
            **namespace._grid_fields,
            **namespace._grid_state_fields,
        }
        for attr_name, field in all_captured.items():
            if attr_name in _GRID_RESERVED or attr_name.startswith("_"):
                continue
            if field.state:
                state_fields[attr_name] = field
            else:
                fields[attr_name] = field
                # Layout fields without an explicit default start as None and
                # stay hidden until a value is assigned.
                if attr_name not in defaults:
                    defaults[attr_name] = None
            if field.default is not UNSET:
                defaults[attr_name] = field.default
            elif field.default_factory is not None:
                defaults[attr_name] = field.default_factory

        # 2. Type-annotated attributes that are NOT GridFieldInfo → auto state fields
        # Python 3.14+ stores annotations lazily via __annotate_func__ instead
        # of eagerly in __annotations__.  Use inspect.get_annotations on the
        # already-created class to evaluate them safely.
        try:
            ns_annotations = inspect.get_annotations(cls, eval_str=True)
        except Exception:
            ns_annotations = namespace.get("__annotations__", {})
        for attr_name, annotation in ns_annotations.items():
            if attr_name.startswith("_") or attr_name in _GRID_RESERVED:
                continue
            field_annotations[attr_name] = annotation
            if attr_name in fields or attr_name in state_fields:
                continue
            raw = namespace.get(attr_name, UNSET)
            if isinstance(raw, (GridFieldInfo, type, property)):
                continue
            if callable(raw) and not isinstance(raw, GridFieldInfo):
                continue
            if raw is UNSET:
                state_fields[attr_name] = GridFieldInfo(state=True)
            else:
                state_fields[attr_name] = GridFieldInfo(
                    state=True, default=raw
                )
                defaults[attr_name] = raw

        # 3. Remaining plain values with no type annotation → layout fields
        for attr_name, raw in namespace.items():
            if attr_name.startswith("_") or attr_name in _GRID_RESERVED:
                continue
            if attr_name in fields or attr_name in state_fields:
                continue
            if isinstance(raw, (type, property, GridFieldInfo)) or callable(
                raw
            ):
                continue
            fields[attr_name] = GridFieldInfo(default=raw)
            defaults[attr_name] = raw

        # Ensure all layout fields have a default (None) so __init__ never
        # makes them required.
        for attr_name in fields:
            if attr_name not in defaults:
                defaults[attr_name] = None

        setattr(cls, "_grid_fields", fields)
        setattr(cls, "_grid_state_fields", state_fields)
        setattr(cls, "_grid_defaults", defaults)
        setattr(cls, "_grid_field_annotations", field_annotations)
        setattr(
            cls,
            "_grid_field_frames",
            {
                field_name: frame_from_field(field)
                for field_name, field in fields.items()
            },
        )

        # 4. Collect field-click handlers declared via on_mouse(field=...) / on_click(...)
        field_handlers = _collect_field_mouse_handlers(cls, namespace, fields)
        setattr(cls, "_grid_field_handlers", field_handlers)

        has_slide_fields = any(field.slide for field in fields.values())
        needs_mouse_geometry = bool(field_handlers) or has_slide_fields
        for base in cls.__mro__:
            if base is cls or base is object:
                continue
            if getattr(base, "_grid_has_slide_fields", False):
                has_slide_fields = True
            if getattr(base, "_grid_has_mouse_geometry", False):
                needs_mouse_geometry = True
        setattr(cls, "_grid_has_slide_fields", has_slide_fields)
        setattr(cls, "_grid_has_mouse_geometry", needs_mouse_geometry)

        # 5. Precompute static layout data
        _direction = cfg.get("direction", "vertical")
        needs_dynamic = any(
            _field_needs_content_measure(f, _direction) or f.visible is None
            for f in fields.values()
        )
        static_names: list[str] = []
        static_constraints: list[_GridLayoutConstraint] = []
        if not needs_dynamic:
            for field_name, field in fields.items():
                if field.visible is False:
                    continue
                static_names.append(field_name)
                static_constraints.append(
                    _layout_constraint_for_field(field, _direction)
                )

        setattr(cls, "_grid_needs_dynamic_layout", needs_dynamic)
        setattr(cls, "_grid_static_field_names", static_names)
        setattr(cls, "_grid_static_constraints", static_constraints)

        # 6. Detect overridden responsive render variants once per class.
        # An empty map lets the per-frame path skip breakpoint dispatch.
        setattr(
            cls,
            "_grid_responsive_renders",
            collect_responsive_overrides(cls, "grid_render_"),
        )

        all_fields = {**fields, **state_fields}
        if all_fields:
            type.__setattr__(
                cls, "__init__", _build_grid_init(all_fields, defaults)
            )

        return cls


class BaseGrid(AbstractInterface, metaclass=_GridMeta):
    """Declarative layout container for a terminal-based UI.

    BaseGrid-scoped settings may be declared on the class header
    (``class Dashboard(BaseGrid, direction="horizontal", gap=1): ...``),
    in a class-level ``grid_settings`` dict, or both — values in
    ``grid_settings`` override matching header kwargs.

    Attributes:
        grid_settings: Class-level layout and frame configuration.
        visible: Whether the grid is rendered.
        z: Layering order for overlapping grids.
        columns: Columns available during the current frame.
        rows: Rows available during the current frame.

    Examples:

    Layout fields render content; ``state=True`` fields hold app data.
    Nested ``BaseGrid`` subclasses compose larger layouts:

    ```python
    from xnano import BaseGrid, Field, Terminal

    class Sidebar(BaseGrid, direction="vertical"):
        nav: str = Field(default="Home", border="rounded", height="1fr")

    class App(BaseGrid, direction="horizontal", gap=1):
        sidebar: Sidebar = Field(default_factory=Sidebar, width="25%")
        content: str = Field(default="Main area", width="1fr")

        selected: int = Field(default=0, state=True)

    Terminal().run(App())
    ```

    Event hooks register handlers on the grid class. Use ``@on_click`` to
    scope mouse handlers to a layout field's region:

    ```python
    from xnano import BaseGrid, Context, Field, Terminal, hooks

    class Counter(BaseGrid, direction="vertical", gap=1):
        label: str = Field(default="Count: 0", height=1)
        body: str = Field(default="Click me", height="1fr")

        count: int = Field(default=0, state=True)

        @hooks.on_keyboard("up")
        def increment(self) -> None:
            self.count += 1
            self.label = f"Count: {self.count}"

        @hooks.on_keyboard("down")
        def decrement(self) -> None:
            self.count -= 1
            self.label = f"Count: {self.count}"

        @hooks.on_click("body")
        def on_body(self, ctx: Context) -> None:
            self.body = "Clicked!"

        @hooks.on_tick(1000)
        def reset_body(self) -> None:
            self.body = "Click me"

    Terminal().run(Counter())
    ```
    """

    grid_settings: ClassVar[GridSettings] = {}
    """Class-level grid configuration, like Pydantic's ``model_config``."""
    _grid_strict: ClassVar[bool] = True
    _grid_fields: ClassVar[dict[str, GridFieldInfo]] = {}
    _grid_state_fields: ClassVar[dict[str, GridFieldInfo]] = {}
    _grid_field_handlers: ClassVar[dict[str, Any]] = {}
    _grid_field_annotations: ClassVar[dict[str, Any]] = {}
    _grid_has_slide_fields: ClassVar[bool] = False
    _grid_has_mouse_geometry: ClassVar[bool] = False
    _grid_frame: ClassVar[Frame | None] = None
    _grid_direction: ClassVar[Direction] = "vertical"
    _grid_gap: ClassVar[int] = 0
    _grid_needs_dynamic_layout: ClassVar[bool] = False
    _grid_static_field_names: ClassVar[list[str]] = []
    _grid_static_constraints: ClassVar[list[_GridLayoutConstraint]] = []
    _grid_defaults: ClassVar[dict[str, Any]] = {}
    _grid_field_frames: ClassVar[dict[str, Frame | None]] = {}
    _grid_responsive_renders: ClassVar[dict[str, str]] = {}

    __xnano_grid__: ClassVar[bool] = True
    """Marks this class as a grid, for cheap identity checks.

    Faster and clearer than duck-typing ``_grid_fields``, and usable from
    layers that must not import ``BaseGrid`` — see ``is_grid``.
    """

    visible: bool = True
    """Whether this grid is rendered in the live session."""
    z: int = 0
    """Z-index used when layering overlapping grids."""
    columns: int = 0
    """Terminal columns available to this grid — set by the session each frame."""
    rows: int = 0
    """Terminal rows available to this grid — set by the session each frame."""

    def __init__(self) -> None:
        self._grid_init_field_states()
        self.__post_init__()

    def __post_init__(self) -> None:
        """Called at the end of the generated ``__init__``. Override to run post-construction logic."""

    def grid_post_init(self) -> None:
        """Called exactly once, when this grid is first attached to a live
        terminal — after its own hooks are bound, before its first paint.

        Unlike ``__post_init__`` (construction time, no terminal attached
        yet), ``ctx``/``ctx.state`` are live here. Override with either
        signature — the extra parameter is optional, matching every other
        ``@on_*`` hook, dispatched by arity at runtime (see ``_call_hook``):

            def grid_post_init(self) -> None: ...
            def grid_post_init(self, ctx: Context[MyState]) -> None: ...

        A static type checker sees the one-parameter form as an invalid
        override (this base declares zero); that's a known false positive
        for this flexible-arity hook pattern — add
        ``# ty: ignore[invalid-method-override]`` on the override line.
        """

    @property
    def grid_focused(self) -> bool:
        """Whether any of this grid's fields currently holds field focus.

        Live alongside per-component ``focused``: derived from the same
        per-frame focus flags, so ``self.grid_focused`` in a hook and
        ``@on_field("focused")`` both read the current state.
        """
        return any(
            bool(getattr(getattr(self, name, None), "focused", False))
            for name in getattr(self, "_grid_fields", {})
        )

    def _grid_annotation_for_field(
        self,
        name: str,
        field: GridFieldInfo,
    ) -> Any | None:
        ann = self._grid_field_annotations.get(name)
        if ann is not None:
            return ann
        if field.state:
            return None
        from xnano.utils.validation import layout_field_annotation

        return layout_field_annotation()

    def _grid_validate_field(
        self,
        name: str,
        value: Any,
        *,
        field: GridFieldInfo,
    ) -> Any:
        if value is None:
            return value
        ann = self._grid_annotation_for_field(name, field)
        if ann is None:
            return value
        from pydantic_core import ValidationError

        from xnano.core.exceptions import FieldValidationError
        from xnano.utils.validation import validate_type

        try:
            return validate_type(value, ann)
        except ValidationError as exc:
            raise FieldValidationError(name, exc) from exc

    def _grid_validate_init(self) -> None:
        if not self._grid_strict:
            return
        fields = self._grid_fields.items()
        state_fields = (
            (name, field)
            for name, field in self._grid_state_fields.items()
            if not field.strict
        )
        for name, field in itertools.chain(fields, state_fields):
            value = getattr(self, name, None)
            validated = self._grid_validate_field(name, value, field=field)
            if validated is not value:
                object.__setattr__(self, name, validated)

    def __setattr__(self, name: str, value: Any) -> None:
        field = self._grid_state_fields.get(name)
        if field is not None and field.strict:
            value = self._grid_validate_field(name, value, field=field)
        elif isinstance(value, str) and name in self._grid_fields:
            value = _coerce_text_field(
                value, self._grid_field_annotations.get(name)
            )
        object.__setattr__(self, name, value)
        # Live FieldState dirty bit + host notification (skip private attrs
        # and fields not yet tracked during construction).
        if not name.startswith("_") and hasattr(self, "_grid_field_states"):
            if name in self._grid_field_states or name in self._grid_fields:
                self.grid_mark_field_dirty(name)

    @property
    def grid_state(self) -> Any:
        """Return the active terminal's shared state, or ``None``."""
        from xnano.core.runtime import get_active_runtime

        runtime = get_active_runtime()
        return None if runtime is None else runtime.state

    @property
    @warn_renamed_attribute("BaseGrid.focused", "BaseGrid.grid_focused")
    def focused(self) -> bool:
        """Deprecated alias for ``grid_focused``."""
        return self.grid_focused

    @property
    @warn_renamed_attribute("BaseGrid.state", "BaseGrid.grid_state")
    def state(self) -> Any:
        """Deprecated alias for ``grid_state``."""
        return self.grid_state

    def _grid_call_render(self) -> None:
        """Invoke ``grid_render`` with the arity the subclass declared.

        Overrides may take zero extra parameters or a single ``Context``
        (like ``grid_post_init`` and every ``@on_*`` hook). ``invoke_hook``
        dispatches by cached arity; the ``Context`` is built the same way
        ``dispatch_post_init`` builds it. With no live runtime (bare
        offscreen paint) fall back to the no-argument call.
        """
        from xnano.core.runtime import get_active_runtime
        from xnano.utils.dispatch import invoke_hook
        from xnano.utils.introspection import (
            get_function_extra_parameter_count,
        )

        runtime = get_active_runtime()
        if runtime is None or (
            get_function_extra_parameter_count(type(self).grid_render) == 0
        ):
            self.grid_render()
            return
        from xnano.context import Context
        from xnano.core.dispatch import _CONTEXT_EVENT

        context = Context(
            event=_CONTEXT_EVENT, terminal=runtime, state=runtime.state
        )
        invoke_hook(self.grid_render, None, context)

    def grid_render(self) -> None:
        """Called each frame before layout.

        Override to refresh field values every frame. Initial values can be set
        with ``Field(default=...)``, ``default_factory``, or ``__post_init__``.

        Override with either signature — the extra ``Context`` parameter is
        optional, dispatched by arity like ``grid_post_init``:

            def grid_render(self) -> None: ...
            def grid_render(self, ctx: Context[MyState]) -> None: ...

        A static type checker sees the one-parameter form as an invalid
        override; add ``# ty: ignore[invalid-method-override]`` on the
        override line.
        """

    @responsive_noop
    def grid_render_extra_small(self) -> None:
        """Refine layout when the viewport is extra small (< 40 cols).

        Optional responsive counterpart to :meth:`grid_render`. Runs when
        the window enters this size tier — on the first render and on
        later resizes that cross into it — not every frame, so a
        per-frame ``@on_tick`` mutation is not overwritten by a size hook
        resetting the same field. Keep shared per-frame logic in
        ``grid_render`` and size-specific setup here. Overriding any
        ``grid_render_*`` variant opts the class into breakpoint dispatch;
        a class that overrides none pays no per-frame cost.
        """

    @responsive_noop
    def grid_render_small(self) -> None:
        """Refine layout when the viewport is small (40–79 cols).

        See :meth:`grid_render_extra_small`.
        """

    @responsive_noop
    def grid_render_medium(self) -> None:
        """Refine layout when the viewport is medium (80–119 cols).

        See :meth:`grid_render_extra_small`.
        """

    @responsive_noop
    def grid_render_large(self) -> None:
        """Refine layout when the viewport is large (120–159 cols).

        See :meth:`grid_render_extra_small`.
        """

    @responsive_noop
    def grid_render_extra_large(self) -> None:
        """Refine layout when the viewport is extra large (>= 160 cols).

        See :meth:`grid_render_extra_small`.
        """

    @overload
    def grid_play_effect(
        self,
        effect: AbstractEffect,
        *,
        fields: list[str] | None = None,
    ) -> bool: ...

    @overload
    def grid_play_effect(
        self,
        effect: KnownEffectKind,
        *,
        duration_ms: int = 300,
        color: ColorLike | None = None,
        background: ColorLike | None = None,
        direction: EffectMotion | None = None,
        gradient_length: int | None = None,
        randomness: int | None = None,
        interpolation: EffectInterpolation | None = None,
        effects: Sequence[AbstractEffect] | None = None,
        child: AbstractEffect | None = None,
        times: int | None = None,
        fields: list[str] | None = None,
        key: str | None = None,
    ) -> bool: ...

    @warn_renamed_attribute(
        "BaseGrid.grid_play_effect", "BaseGrid.grid_effect"
    )
    def grid_play_effect(
        self,
        effect: KnownEffectKind | AbstractEffect,
        *,
        duration_ms: int = 300,
        color: ColorLike | None = None,
        background: ColorLike | None = None,
        direction: EffectMotion | None = None,
        gradient_length: int | None = None,
        randomness: int | None = None,
        interpolation: EffectInterpolation | None = None,
        effects: Sequence[AbstractEffect] | None = None,
        child: AbstractEffect | None = None,
        times: int | None = None,
        fields: list[str] | None = None,
        key: str | None = None,
    ) -> bool:
        """Run a visual effect on one or more layout field areas.

        Each layout field is tagged with its name as an effect key during
        rendering, so effects can target field content rects on the frame
        after ``grid_render``.

        Pass a custom ``AbstractEffect`` subclass or
        provide a known effect kind with typed keyword arguments.

        Args:
            effect: A built effect instance or a known effect kind string.
            duration_ms: Duration of the effect in milliseconds.
            color: Foreground or accent color for color-driven effects.
            background: Background color for two-color effects.
            direction: Motion direction for slide and sweep effects.
            gradient_length: Gradient length for slide and sweep effects.
            randomness: Randomness for slide and sweep effects.
            interpolation: Interpolation curve for the effect.
            effects: Child effects for sequence and parallel composition.
            child: Child effect for repeat and delay composition.
            times: Repeat count for repeat effects.
            fields: Layout field names to target. When omitted or empty, no
                effect is started.
            key: Identity used to de-duplicate this effect per target
                field — see ``AbstractEffect.key``. Only meaningful when
                ``effect`` is a known-kind string; ignored when ``effect``
                is already a built ``AbstractEffect`` instance (set
                ``key`` on the instance itself in that case).

        Returns:
            ``True`` when at least one field area was found and an effect
            started.
        """
        return bool(
            self.grid_effect(
                effect,
                duration_ms=duration_ms,
                color=color,
                background=background,
                direction=direction,
                gradient_length=gradient_length,
                randomness=randomness,
                interpolation=interpolation,
                effects=effects,
                child=child,
                times=times,
                fields=fields,
                key=key,
            )
        )

    def grid_effect(
        self,
        effect: KnownEffectKind | AbstractEffect,
        *,
        duration_ms: int | None = None,
        color: ColorLike | None = None,
        background: ColorLike | None = None,
        direction: EffectMotion | None = None,
        gradient_length: int | None = None,
        randomness: int | None = None,
        interpolation: EffectInterpolation | None = None,
        effects: Sequence[AbstractEffect] | None = None,
        child: AbstractEffect | None = None,
        times: int | None = None,
        fields: list[str] | None = None,
        key: str | None = None,
    ) -> "EffectHandle":
        """Run a visual effect on one or more layout field areas.

        Returns an ``EffectHandle``: truthy when at least one field was
        targeted, with ``.active`` and ``.cancel()``, and usable as a
        context manager that cancels the effect on exit.

        Starting an effect never blocks. ``duration_ms`` is the animation
        length handed to the renderer, not a sleep — the effect advances
        one frame at a time, so hooks keep running while it plays. Omit it
        inside a ``with`` block and the effect repeats until the block
        exits.

        Args:
            effect: A built effect instance or a known effect kind string.
            duration_ms: Animation length in milliseconds. Defaults to
                300; omitted inside a ``with`` block the effect repeats
                until exit.
            color: Foreground or accent color for color-driven effects.
            background: Background color for two-color effects.
            direction: Motion direction for slide and sweep effects.
            gradient_length: Gradient length for slide and sweep effects.
            randomness: Randomness for slide and sweep effects.
            interpolation: Interpolation curve for the effect.
            effects: Child effects for sequence and parallel composition.
            child: Child effect for repeat and delay composition.
            times: Repeat count for repeat effects.
            fields: Layout field names to target. When omitted or empty,
                no effect is started.
            key: Identity used to de-duplicate this effect per target
                field — see ``AbstractEffect.key``. Calling with the same
                ``key`` every tick replaces the running effect rather than
                stacking new ones.

        Returns:
            A handle for the started effect.

        Examples:
            ```python
            self.grid_effect("fade", fields=["body"])

            with self.grid_effect("pulse", fields=["body"]):
                do_slow_work()
            ```
        """
        from xnano.core.runtime import get_active_runtime
        from xnano.effects import EffectHandle, resolve_effect

        runtime = get_active_runtime()
        if runtime is None:
            return EffectHandle()
        resolved_effect = resolve_effect(
            effect,
            duration_ms=300 if duration_ms is None else duration_ms,
            color=color,
            background=background,
            direction=direction,
            gradient_length=gradient_length,
            randomness=randomness,
            interpolation=interpolation,
            effects=effects,
            child=child,
            times=times,
            key=key,
        )
        keys = runtime.play_effect(resolved_effect, fields=fields)
        return EffectHandle(
            keys=tuple(keys),
            runtime=runtime,
            effect=resolved_effect,
            fields=tuple(fields or ()),
            loop_in_context=duration_ms is None,
        )

    def _grid_field_info(self, name: str) -> GridFieldInfo:
        overrides = getattr(self, "_grid_field_overrides", None)
        if overrides and name in overrides:
            return overrides[name]
        return self._grid_fields[name]

    def _grid_has_field_overrides(self) -> bool:
        overrides = getattr(self, "_grid_field_overrides", None)
        return bool(overrides)

    def _grid_needs_mouse_geometry(self) -> bool:
        if type(self)._grid_has_mouse_geometry:
            return True
        overrides = getattr(self, "_grid_field_overrides", None)
        if overrides and any(field.slide for field in overrides.values()):
            return True
        if type(self)._grid_field_handlers:
            return True
        for field_name in self._grid_fields:
            info = self._grid_field_info(field_name)
            if info.slide or info.group or info.scroll:
                return True
            value = getattr(self, field_name, None)
            if (
                isinstance(value, BaseGrid)
                and value._grid_needs_mouse_geometry()
            ):
                return True
            from xnano.utils.focus import is_focusable_component

            if is_focusable_component(value):
                return True
        return False

    def _grid_field_position(self, name: str) -> tuple[int, int]:
        positions = getattr(self, "_grid_field_positions", None)
        if positions and name in positions:
            return positions[name]
        return (0, 0)

    def _grid_set_field_position(
        self,
        name: str,
        position: tuple[int, int],
        *,
        parent_area: Area,
        slot_area: Area,
    ) -> tuple[int, int]:
        field = self._grid_field_info(name)
        clamped = _grid_clamp_slide_position(
            parent_area,
            slot_area,
            field.slide or [],
            position,
        )
        self.__dict__.setdefault("_grid_field_positions", {})[name] = clamped
        return clamped

    def grid_field_position(self, name: str) -> tuple[int, int]:
        """Return the parent-relative slide offset for a layout field."""
        return self._grid_field_position(name)

    def _grid_scroll_handle(self, name: str, axis: Axis = "y") -> Any:
        """Return (creating if needed) the ``ScrollHandle`` for a field.

        Handles are keyed by field name so the paint path and
        ``ctx.scroll(group)`` share one mutable offset per scroll region.
        """
        from xnano.types import ScrollHandle

        handles = getattr(self, "_grid_scroll_handles", None)
        if handles is None:
            handles = {}
            object.__setattr__(self, "_grid_scroll_handles", handles)
        handle = handles.get(name)
        if handle is None:
            handle = ScrollHandle(group=name, axis=axis)
            handles[name] = handle
        return handle

    def _grid_resolve_scroll(
        self,
        name: str,
        field: GridFieldInfo,
        value: Any,
        paint_area: Area,
    ) -> tuple[int, str]:
        """Clamp and resolve a scroll field's paint offset for one frame.

        Measures the content, clamps the handle offset to the available
        range, honors ``follow`` (snap to the tail), and writes the clamped
        offset back so ``ctx.scroll`` reflects reality.
        """
        from xnano.core.controller import content_scroll_extent

        axis = "x" if field.scroll == "horizontal" else "y"
        handle = self._grid_scroll_handle(name, axis)
        extent = content_scroll_extent(value, axis)
        view = paint_area.height if axis == "y" else paint_area.width
        max_offset = max(0, extent - view)
        offset = (
            max_offset if handle.follow else min(handle.offset, max_offset)
        )
        handle.offset = offset
        return offset, axis

    def _grid_field_needs_hit(
        self, field_name: str, field: GridFieldInfo
    ) -> bool:
        if field.slide:
            return True
        if field.group or field.scroll or field.autofocus:
            return True
        if _resolve_grid_mouse_handler(self, field_name) is not None:
            return True
        from xnano.utils.focus import is_focusable_component

        return is_focusable_component(getattr(self, field_name, None))

    def _grid_apply_field_config(
        self,
        name: str,
        field_config: dict[str, Any],
        *,
        caller: str,
        missing: str = "raise",
    ) -> None:
        """Validate and store per-instance style/layout overrides for ``name``.

        Shared by ``grid_set_field`` and ``grid_update_field`` — the only
        difference between the two callers is which keyword arguments they
        expose; the validation and override-storage logic is identical.

        ``missing="ignore"`` turns a missing or state-only target into a
        no-op instead of an exception, so an optional style patch (e.g. a
        border-color pulse from ``on_tick``) never has to be wrapped in
        ``try``/``except``. Unknown/forbidden keyword arguments still raise,
        as those signal a programming error rather than timing.
        """
        if name in self._grid_state_fields:
            if missing == "ignore":
                return
            raise TypeError(
                f"{caller}() cannot be used on state field {name!r} on "
                f"{type(self).__name__}"
            )
        if name not in self._grid_fields:
            if missing == "ignore":
                return
            raise AttributeError(
                f"{type(self).__name__} has no layout field {name!r}"
            )

        forbidden = _GRID_FIELD_IMMUTABLE_KEYS & field_config.keys()
        if forbidden:
            raise TypeError(
                f"{caller}() does not accept {', '.join(sorted(forbidden))}"
            )

        unknown = set(field_config) - _GRID_FIELD_CONFIG_KEYS
        if unknown:
            raise TypeError(
                f"{caller}() got unexpected keyword arguments: "
                f"{', '.join(sorted(unknown))}"
            )

        if not field_config:
            return

        if "class_name" in field_config:
            field_config = _expand_field_class_name_config(field_config)
        if any(key in field_config for key in _GRID_MODIFIER_FLAG_KEYS):
            field_config = _apply_field_modifier_flags(
                field_config,
                self._grid_field_info(name).modifiers,
            )
        if "slide" in field_config:
            field_config = {
                **field_config,
                "slide": _normalize_slide_axes(field_config["slide"]),
            }
        if "width" in field_config or "height" in field_config:
            from xnano.types import Sizing

            normalized = dict(field_config)
            if "width" in normalized:
                normalized["width"] = Sizing.parse(normalized["width"])
            if "height" in normalized:
                normalized["height"] = Sizing.parse(normalized["height"])
            field_config = normalized

        current = self._grid_field_info(name)
        # A no-op toggle (setting an attribute to the value it already
        # has) skips override creation entirely — cheap to call every
        # frame, and doesn't permanently drop the grid out of the static
        # layout fast path for a change that didn't change anything.
        if all(
            getattr(current, key) == value
            for key, value in field_config.items()
        ):
            return

        overrides = self.__dict__.setdefault("_grid_field_overrides", {})
        overrides[name] = dataclasses.replace(current, **field_config)

    def grid_set_field(
        self,
        name: str,
        value: Any = UNSET,
        *,
        position: tuple[int, int] | None = None,
        strict: bool = UNSET,
        slide: Sequence[Axis] | None = UNSET,
        visible: bool | None = UNSET,
        wireframe: bool | None = UNSET,
        foreground: ColorLike | None = UNSET,
        background: ColorLike | None = UNSET,
        fill: bool | None = UNSET,
        width: SizingLike | None = UNSET,
        height: SizingLike | None = UNSET,
        gap: int | None = UNSET,
        direction: Direction | None = UNSET,
        horizontal_align: Alignment | None = UNSET,
        vertical_align: VerticalAlignment | None = UNSET,
        border: Border | None = UNSET,
        border_sides: Sequence[Side] | None = UNSET,
        border_color: ColorLike | None = UNSET,
        title: str | None = UNSET,
        title_position: FrameTitlePosition | None = UNSET,
        padding: PaddingLike | None = UNSET,
        margin: PaddingLike | None = UNSET,
        z: int | None = UNSET,
        modifiers: Sequence[CharacterModifier] | None = UNSET,
        class_name: ClassNameLike | None = UNSET,
        bold: bool = UNSET,
        dim: bool = UNSET,
        italic: bool = UNSET,
        underline: bool = UNSET,
        slow_blink: bool = UNSET,
        rapid_blink: bool = UNSET,
        reversed: bool = UNSET,
        color: ColorLike | None = UNSET,
        align: Alignment | None = UNSET,
    ) -> None:
        """Set a layout field's runtime value and/or per-instance field metadata.

        Cannot be used on state fields. ``default``, ``default_factory``,
        ``init``, and ``state`` cannot be changed at runtime.

        For frequent, value-free style ticks (e.g. from ``on_tick`` or an
        effect callback), prefer ``grid_update_field`` — it skips the
        value/position handling this method carries for the general case.

        ``color`` is a deprecated alias for ``foreground``.
        """
        foreground = resolve_color_alias(
            foreground, color, unset=UNSET, stacklevel=3
        )
        horizontal_align = resolve_renamed_alias(
            horizontal_align,
            align,
            old="align",
            new="horizontal_align",
            unset=UNSET,
            stacklevel=3,
        )
        field_config: dict[str, Any] = {
            key: option
            for key, option in {
                "strict": strict,
                "slide": slide,
                "visible": visible,
                "wireframe": wireframe,
                "foreground": foreground,
                "background": background,
                "fill": fill,
                "width": width,
                "height": height,
                "gap": gap,
                "direction": direction,
                "horizontal_align": horizontal_align,
                "vertical_align": vertical_align,
                "border": border,
                "border_sides": border_sides,
                "border_color": border_color,
                "title": title,
                "title_position": title_position,
                "padding": padding,
                "margin": margin,
                "z": z,
                "modifiers": modifiers,
                "class_name": class_name,
                "bold": bold,
                "dim": dim,
                "italic": italic,
                "underline": underline,
                "slow_blink": slow_blink,
                "rapid_blink": rapid_blink,
                "reversed": reversed,
            }.items()
            if option is not UNSET
        }

        self._grid_apply_field_config(
            name, field_config, caller="grid_set_field"
        )

        if position is not None:
            slot = getattr(self, "_grid_last_slot_areas", {}).get(name)
            parent = getattr(self, "_grid_last_parent_area", None)
            if slot is not None and parent is not None:
                self._grid_set_field_position(
                    name,
                    position,
                    parent_area=parent,
                    slot_area=slot,
                )
            else:
                self.__dict__.setdefault("_grid_field_positions", {})[name] = (
                    position
                )

        if value is not UNSET:
            field = self._grid_field_info(name)
            if self._grid_strict:
                value = self._grid_validate_field(name, value, field=field)
            object.__setattr__(self, name, value)

    def grid_update_field(
        self,
        name: str,
        *,
        slide: Sequence[Axis] | None = UNSET,
        visible: bool | None = UNSET,
        wireframe: bool | None = UNSET,
        foreground: ColorLike | None = UNSET,
        background: ColorLike | None = UNSET,
        fill: bool | None = UNSET,
        width: SizingLike | None = UNSET,
        height: SizingLike | None = UNSET,
        gap: int | None = UNSET,
        direction: Direction | None = UNSET,
        horizontal_align: Alignment | None = UNSET,
        vertical_align: VerticalAlignment | None = UNSET,
        border: Border | None = UNSET,
        border_sides: Sequence[Side] | None = UNSET,
        border_color: ColorLike | None = UNSET,
        title: str | None = UNSET,
        title_position: FrameTitlePosition | None = UNSET,
        padding: PaddingLike | None = UNSET,
        margin: PaddingLike | None = UNSET,
        z: int | None = UNSET,
        modifiers: Sequence[CharacterModifier] | None = UNSET,
        class_name: ClassNameLike | None = UNSET,
        bold: bool = UNSET,
        dim: bool = UNSET,
        italic: bool = UNSET,
        underline: bool = UNSET,
        slow_blink: bool = UNSET,
        rapid_blink: bool = UNSET,
        reversed: bool = UNSET,
        color: ColorLike | None = UNSET,
        align: Alignment | None = UNSET,
    ) -> None:
        """Update a layout field's style/layout attributes, live, in-place.

        A narrower sibling of ``grid_set_field`` for frequent, value-free
        attribute changes — pulsing a border color from ``on_tick``,
        toggling a modifier from an effect callback. It has no ``value=``
        or ``position=`` parameters at all, so a per-frame style tick never
        pays for that method's value-validation branch. Optional style
        patches never raise: a missing or state-only ``name`` is a no-op
        (no ``try``/``except`` needed), though unknown keyword arguments
        still raise as a programming error.

        ``color`` is a deprecated alias for ``foreground``.
        """
        foreground = resolve_color_alias(
            foreground, color, unset=UNSET, stacklevel=3
        )
        horizontal_align = resolve_renamed_alias(
            horizontal_align,
            align,
            old="align",
            new="horizontal_align",
            unset=UNSET,
            stacklevel=3,
        )
        field_config: dict[str, Any] = {
            key: option
            for key, option in {
                "slide": slide,
                "visible": visible,
                "wireframe": wireframe,
                "foreground": foreground,
                "background": background,
                "fill": fill,
                "width": width,
                "height": height,
                "gap": gap,
                "direction": direction,
                "horizontal_align": horizontal_align,
                "vertical_align": vertical_align,
                "border": border,
                "border_sides": border_sides,
                "border_color": border_color,
                "title": title,
                "title_position": title_position,
                "padding": padding,
                "margin": margin,
                "z": z,
                "modifiers": modifiers,
                "class_name": class_name,
                "bold": bold,
                "dim": dim,
                "italic": italic,
                "underline": underline,
                "slow_blink": slow_blink,
                "rapid_blink": rapid_blink,
                "reversed": reversed,
            }.items()
            if option is not UNSET
        }
        self._grid_apply_field_config(
            name, field_config, caller="grid_update_field", missing="ignore"
        )

    def grid_set_frame(
        self,
        frame: Frame | None = UNSET,
        *,
        background: ColorLike | None = UNSET,
        border: Border | None = UNSET,
        border_color: ColorLike | None = UNSET,
        border_sides: Sequence[Side] | None = UNSET,
        title: str | None = UNSET,
        title_position: FrameTitlePosition | None = UNSET,
        padding: PaddingLike | None = UNSET,
    ) -> None:
        """Set this grid instance's outer frame (chrome + background fill).

        The public replacement for mutating the private ``_grid_frame``.
        Pass a whole ``frame`` to replace it outright, or individual keyword
        arguments to patch the current frame in place — a bare
        ``background`` fills the grid's whole area with no border required,
        so nested grids can be themed without any chrome. Pass ``frame=None``
        to clear the frame.
        """
        if frame is not UNSET:
            object.__setattr__(
                self, "_grid_frame", None if frame is None else frame
            )
            return
        current = getattr(self, "_grid_frame", None) or Frame()
        patch = {
            key: value
            for key, value in {
                "background": background,
                "border": border,
                "border_color": border_color,
                "border_sides": border_sides,
                "title": title,
                "title_position": title_position,
                "padding": padding,
            }.items()
            if value is not UNSET
        }
        if not patch:
            return
        updated = dataclasses.replace(current, **patch)
        object.__setattr__(
            self, "_grid_frame", None if updated.is_empty() else updated
        )

    def grid_set_background(self, background: ColorLike | None) -> None:
        """Fill this grid instance's whole area with ``background``.

        Shorthand for ``grid_set_frame(background=...)`` — the path for
        theming a nested grid, replacing private ``_grid_frame`` mutation.
        """
        self.grid_set_frame(background=background)

    def grid_schedule_update(
        self,
        callback: Callable[[], Any] | None = None,
        *,
        field: str | None = None,
    ) -> None:
        """Apply an update on the UI thread before the next frame.

        The thread-safe way to reflect background work in the UI: pass a
        ``callback`` to run on the runtime thread (so it can mutate this grid
        without racing the renderer), and/or a ``field`` to mark dirty. Safe
        to call from any thread; a no-op when no runtime is active.
        """
        from xnano.core.runtime import get_active_runtime

        runtime = get_active_runtime()

        def _apply() -> None:
            if callback is not None:
                callback()
            if field is not None:
                self.grid_mark_field_dirty(field)

        if runtime is None:
            _apply()
        else:
            runtime.call_soon(_apply)

    @warn_renamed_attribute("BaseGrid.set_frame", "BaseGrid.grid_set_frame")
    def set_frame(self, *args: Any, **kwargs: Any) -> None:
        """Deprecated alias for ``grid_set_frame``."""
        self.grid_set_frame(*args, **kwargs)

    @warn_renamed_attribute(
        "BaseGrid.set_background", "BaseGrid.grid_set_background"
    )
    def set_background(self, background: ColorLike | None) -> None:
        """Deprecated alias for ``grid_set_background``."""
        self.grid_set_background(background)

    @warn_renamed_attribute(
        "BaseGrid.schedule_update", "BaseGrid.grid_schedule_update"
    )
    def schedule_update(
        self,
        callback: Callable[[], Any] | None = None,
        *,
        field: str | None = None,
    ) -> None:
        """Deprecated alias for ``grid_schedule_update``."""
        self.grid_schedule_update(callback, field=field)

    def _grid_resolve_visible(self, field: GridFieldInfo, value: Any) -> bool:
        if field.visible is None:
            return value is not None
        return bool(field.visible)

    def _grid_field_frame(
        self, name: str, field: GridFieldInfo
    ) -> Frame | None:
        overrides = getattr(self, "_grid_field_overrides", None)
        if overrides and name in overrides:
            return frame_from_field(field)
        return self._grid_field_frames[name]

    def _grid_register_field_hit(
        self,
        field_name: str,
        paint_area: Area,
        *,
        slot_area: Area,
        parent_area: Area,
        slide_axes: list[str] | None = None,
    ) -> None:
        hits = getattr(self, "_grid_field_hits", None)
        if hits is None:
            hits = []
            object.__setattr__(self, "_grid_field_hits", hits)
        hits.append(
            _GridFieldHit(
                grid=self,
                field_name=field_name,
                area=paint_area,
                slot_area=slot_area,
                parent_area=parent_area,
                slide_axes=slide_axes or [],
            )
        )

    def _grid_build_frame(
        self,
        area: Area,
        session: Any,
        *,
        suppress_frame_border: bool = False,
        base_z: int = 0,
    ) -> None:
        self.columns = area.width
        self.rows = area.height
        self._grid_call_render()
        responsive = type(self)._grid_responsive_renders
        if responsive:
            self._grid_render_responsive(responsive, area)
        self._grid_assemble(
            area,
            session,
            suppress_frame_border=suppress_frame_border,
            base_z=base_z,
        )

    def _grid_render_responsive(
        self, responsive: dict[str, str], area: Area
    ) -> None:
        """Run the render variant for the viewport, only on size changes.

        These variants fire when the window crosses into a new breakpoint
        (a resize), not every frame — so a per-frame ``@on_tick`` mutation
        is not clobbered by a size hook resetting the same field each
        frame. The first render establishes the initial breakpoint and
        counts as the opening resize.

        Breakpoints follow the live window, not this grid's slot, so a
        nested grid reacts to terminal/browser resizes the same way the
        root does. Only reached when the class overrides at least one
        ``grid_render_*`` variant.
        """
        from xnano.core.runtime import get_active_runtime

        runtime = get_active_runtime()
        width = runtime.size[0] if runtime is not None else area.width
        current = breakpoint_for_width(width)
        if runtime is not None:
            if runtime._grid_breakpoints.get(id(self)) == current:
                return
            runtime._grid_breakpoints[id(self)] = current
        method_name = responsive.get(current)
        if method_name is not None:
            getattr(self, method_name)()

    def _grid_frame_for_paint(self, suppress_border: bool) -> Frame | None:
        """Return this grid's frame, dropping its border when the parent
        Field already owns it (chrome-owns-the-border rule)."""
        frame = self._grid_frame
        if frame is None or not suppress_border or frame.border is None:
            return frame
        return dataclasses.replace(
            frame, border=None, border_color=None, border_sides=None
        )

    def _grid_assemble(
        self,
        area: Area,
        session: Any,
        *,
        suppress_frame_border: bool = False,
        base_z: int = 0,
    ) -> None:
        if not self.visible:
            return

        self._grid_last_parent_area = area
        self._grid_last_slot_areas = {}
        self._grid_field_hits = []

        # z is a single global painter's layer for the whole frame, so a
        # nested grid stacks on top of its parent's base rather than resetting
        # to zero: fold the incoming base into this grid's own ``z``.
        grid_z = base_z + self.z

        grid_frame = self._grid_frame_for_paint(suppress_frame_border)

        fields = self._grid_fields

        if not fields:
            if grid_frame is not None:
                session.paint_frame(area, grid_frame, z=grid_z)
            return

        active_names: list[str] = []
        active_fields: list[GridFieldInfo] = []
        active_values: list[Any] = []
        active_constraints: list[_GridLayoutConstraint] = []

        use_static_layout = (
            not self._grid_needs_dynamic_layout
            and not self._grid_has_field_overrides()
        )

        if use_static_layout:
            for index, field_name in enumerate(self._grid_static_field_names):
                field = self._grid_field_info(field_name)
                value = getattr(self, field_name, None)
                if value is None and field.visible is None:
                    active_names.clear()
                    break
                active_names.append(field_name)
                active_fields.append(field)
                active_values.append(value)
                active_constraints.append(self._grid_static_constraints[index])

        if not active_names:
            for field_name in fields:
                field = self._grid_field_info(field_name)
                value = getattr(self, field_name, None)
                if not self._grid_resolve_visible(field, value):
                    continue
                content_length: int | None = None
                if _field_needs_content_measure(field, self._grid_direction):
                    available_width = 0
                    if self._grid_direction == "vertical":
                        available_width = max(
                            0,
                            _grid_inner_width(area, self._grid_frame)
                            - _grid_frame_size_for_field(field, "horizontal"),
                        )
                    content_length = session.measure_field_slot(
                        value,
                        self._grid_direction,
                        field,
                        available_width=available_width,
                    )
                active_names.append(field_name)
                active_fields.append(field)
                active_values.append(value)
                active_constraints.append(
                    _layout_constraint_for_field(
                        field, self._grid_direction, content_length
                    )
                )

        if not active_names:
            if grid_frame is not None:
                session.paint_frame(area, grid_frame, z=grid_z)
            return

        inner = area
        if grid_frame is not None:
            inner = session.paint_frame(area, grid_frame, z=grid_z)

        if any(field.overlay for field in active_fields):
            # Overlay fields leave the flow: the split sizes only the in-flow
            # fields, and each overlay is centered over ``inner`` and painted
            # last (highest paint order, on top of the panels).
            flow_names: list[str] = []
            flow_fields: list[GridFieldInfo] = []
            flow_values: list[Any] = []
            flow_constraints: list[_GridLayoutConstraint] = []
            overlay_names: list[str] = []
            overlay_fields: list[GridFieldInfo] = []
            overlay_values: list[Any] = []
            for name, field, value, constraint in zip(
                active_names,
                active_fields,
                active_values,
                active_constraints,
            ):
                if field.overlay:
                    overlay_names.append(name)
                    overlay_fields.append(field)
                    overlay_values.append(value)
                else:
                    flow_names.append(name)
                    flow_fields.append(field)
                    flow_values.append(value)
                    flow_constraints.append(constraint)
            flow_slots = (
                session.split_layout(
                    inner,
                    self._grid_direction,
                    self._grid_gap,
                    flow_constraints,
                )
                if flow_constraints
                else []
            )
            overlay_slots = [
                _grid_overlay_area(inner, field) for field in overlay_fields
            ]
            active_names = flow_names + overlay_names
            active_fields = flow_fields + overlay_fields
            active_values = flow_values + overlay_values
            slot_areas = flow_slots + overlay_slots
        else:
            slot_areas = session.split_layout(
                inner,
                self._grid_direction,
                self._grid_gap,
                active_constraints,
            )

        collect_mouse_geometry = self._grid_needs_mouse_geometry()

        for index, slot_area in enumerate(slot_areas):
            field_name = active_names[index]
            field = active_fields[index]
            value = active_values[index]
            if not field.overlay:
                # An overlay already carries its final centered geometry.
                slot_area = _resolve_slot_area(
                    session, slot_area, field, value, self._grid_direction
                )
            self._grid_last_slot_areas[field_name] = slot_area
            # Always-on LayoutMap (Stage): record geometry; never tied to
            # wireframe — overlay only reads this map.
            from xnano.core.runtime import get_active_runtime

            runtime = get_active_runtime()
            stage = None if runtime is None else runtime.stage
            if stage is not None and hasattr(stage, "areas"):
                stage.areas[field_name] = slot_area
            slide_axes = field.slide or []
            paint_area = _grid_slide_paint_area(
                area,
                slot_area,
                slide_axes,
                self._grid_field_position(field_name),
            )
            if field.margin is not None:
                paint_area = _grid_inset_area_for_margin(
                    paint_area, Padding.parse(field.margin)
                )
            if collect_mouse_geometry and self._grid_field_needs_hit(
                field_name, field
            ):
                self._grid_register_field_hit(
                    field_name,
                    paint_area,
                    slot_area=slot_area,
                    parent_area=area,
                    slide_axes=slide_axes,
                )
            # A field may lift its whole slot onto its own layer; ``None``
            # inherits this grid's folded z.
            field_z = grid_z if field.z is None else grid_z + field.z
            # An overlay occludes what it floats over: clear its area first so
            # glyphs beneath the popup do not bleed through.
            if field.overlay:
                paint_clear = getattr(session, "paint_clear", None)
                if paint_clear is not None:
                    paint_clear(paint_area, z=field_z)
            field_frame = self._grid_field_frame(field_name, field)
            if field_frame is not None:
                paint_chrome = getattr(session, "paint_chrome", None)
                if paint_chrome is not None and hasattr(field, "get_style"):
                    paint_area = paint_chrome(
                        paint_area, field.get_style(), z=field_z
                    )
                else:
                    paint_area = session.paint_frame(
                        paint_area, field_frame, z=field_z
                    )
            # The wireframe is a debug skeleton for the field's allocated
            # cells; paint it *before* the value so live content renders
            # above the dotted grid rather than being covered by it.
            if field.wireframe:
                paint_wireframe = getattr(
                    session, "paint_field_wireframe", None
                )
                if paint_wireframe is not None:
                    paint_wireframe(paint_area, z=field_z)
            if value is None:
                continue
            scroll_offset = 0
            scroll_axis = "y"
            if field.scroll:
                scroll_offset, scroll_axis = self._grid_resolve_scroll(
                    field_name, field, value, paint_area
                )
            session.paint_field_slot(
                value,
                paint_area,
                field,
                parent_z=field_z,
                effect_key=field_name,
                owner=self,
                owner_field_name=field_name,
                scroll_offset=scroll_offset,
                scroll_axis=scroll_axis,
            )


def _grid_slide_paint_area(
    parent_area: Area,
    slot_area: Area,
    slide_axes: list[str],
    position: tuple[int, int],
) -> Area:
    if not slide_axes:
        return slot_area

    x = slot_area.x
    y = slot_area.y
    if "x" in slide_axes:
        x = parent_area.x + position[0]
    if "y" in slide_axes:
        y = parent_area.y + position[1]

    max_x = parent_area.x + parent_area.width - slot_area.width
    max_y = parent_area.y + parent_area.height - slot_area.height
    x = max(parent_area.x, min(x, max_x))
    y = max(parent_area.y, min(y, max_y))
    return Area(
        x=x,
        y=y,
        width=slot_area.width,
        height=slot_area.height,
    )


def _grid_clamp_slide_position(
    parent_area: Area,
    slot_area: Area,
    slide_axes: list[str],
    position: tuple[int, int],
) -> tuple[int, int]:
    x = position[0]
    y = position[1]
    if "x" in slide_axes:
        x = max(0, min(x, parent_area.width - slot_area.width))
    if "y" in slide_axes:
        y = max(0, min(y, parent_area.height - slot_area.height))
    return (x, y)


def _resolve_grid_mouse_handler(
    grid: BaseGrid, field_name: str
) -> Callable[..., Any] | None:
    """Return the field-bound mouse handler for ``field_name`` on ``grid``."""
    from xnano import hooks as EventHooks

    for cls in type(grid).__mro__:
        if not (isinstance(cls, type) and issubclass(cls, BaseGrid)):
            continue
        handlers = cls.__dict__.get("_grid_field_handlers")
        if not isinstance(handlers, dict) or field_name not in handlers:
            continue
        attr = handlers[field_name]
        if not hasattr(attr, EventHooks.ON_MOUSE_HOOK_ATTR):
            return None
        return attr.__get__(grid, cls)
    return None


__all__ = (
    "BaseGrid",
    "GridSettings",
)
