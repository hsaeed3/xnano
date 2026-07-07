"""xnano.beta.grid

---

This module provides the `Grid` base class and related types for building
structured, declarative terminal user interfaces. Grids use annotated
`Field` descriptors to define slots/areas with associated layout, sizing,
and style information, and can be configured via the `GridSettings` class.
Grids support flex-style, nested, and stateful layouts, with unified
rendering and event integration.

Example:

    **Defining a Grid:**

    ```python
    from xnano.beta import Grid, Field

    class MyGrid(Grid):
        # title and content are renderable fields if annotated with
        # ``xnano.beta.Field`` and will be displayed on the terminal when
        # ran
        title: str = Field(default="My Grid")
        content: str = Field(default="Hello, world!")

        # data & context are stateful fields and have no rendering
        # behavior
        context: dict[str, Any] | None = None
        data: int = Field(default=0, state=True)
    ```

    **Nested Grids:**

    Grids can also be nested within other grids to create more complex
    layouts

    ```python
    class Box(Grid, direction="vertical", gap=1):
        text: str = Field(default="")

    class Container(Grid):
        left: Box = Field()
        right: Box = Field()
    ```

    **Configuring Settings:**

    You can apply ``xnano.beta.GridSettings`` to a ``Grid`` in one
    of three ways:

        On the class header:

        ```python
        class MyGrid(Grid, direction="horizontal", gap=1):
            ...
        ```

        In a class-level, pydantic-like ``grid_settings`` dict:

        ```python
        class MyGrid(Grid):
            grid_settings = {
                "direction": "horizontal",
                "gap": 1,
            }
            ...

        class MyGrid(Grid):
            grid_settings: GridSettings = GridSettings(
                direction="horizontal",
                gap=1,
            )
            ...
        ```

    **Hooks:**

    You can add event hooks, which can be triggered by various event types,
    (see ``xnano.beta.hooks`` for all possible hooks), and provide a access
    to the runtime context of the live terminal session.

    ```python
    from xnano.beta import Grid, Field, Context
    from xnano.beta.hooks import on_keyboard

    class MyGrid(Grid):
        @on_keyboard("a")
        def on_a(self, ctx: Context) -> None:
            self.data += 1
    ```
"""

from __future__ import annotations

import dataclasses
import inspect
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Literal,
    Sequence,
    TypeAlias,
    TypedDict,
    overload,
)

if sys.version_info < (3, 11):
    from typing_extensions import dataclass_transform, NotRequired, Unpack
else:
    from typing import dataclass_transform, NotRequired, Unpack

from xnano.beta.color import ColorLike
from xnano.beta.frame import Frame, FrameTitlePosition

if TYPE_CHECKING:
    from xnano.beta.effects import (
        AbstractEffect,
        EffectInterpolation,
        EffectMotion,
        KnownEffectKind,
    )
from xnano.beta.fields import (
    UNSET,
    GridFieldInfo,
    Field,
    _normalize_slide_axes,
)
from xnano.beta.types import Area, Border, Direction, Side, PaddingLike


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


_GRID_FIELD_CONFIG_KEYS: frozenset[str] = frozenset(
    {
        "strict",
        "slide",
        "visible",
        "color",
        "background",
        "size",
        "flex",
        "fit",
        "gap",
        "direction",
        "align",
        "border",
        "border_sides",
        "border_color",
        "title",
        "title_position",
        "padding",
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


@dataclasses.dataclass(frozen=True, slots=True)
class _GridLayoutConstraint:
    kind: Literal["length", "percentage", "fill", "content"]
    value: int = 1


@dataclasses.dataclass(frozen=True, slots=True)
class _GridFieldHit:
    grid: "Grid"
    field_name: str
    area: Area
    slot_area: Area
    parent_area: Area
    slide_axes: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True, slots=True)
class _GridSlideCapture:
    grid: "Grid"
    field_name: str
    parent_area: Area
    slot_area: Area
    grab_x: int
    grab_y: int
    slide_axes: list[str]


class GridSettings(TypedDict, total=False):
    """Rendering, layout and frame releated settings that can be applied onto
    a ``Grid`` subclass.
    """

    color: NotRequired[ColorLike]
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


def _merge_grid_settings(
    bases: tuple[type, ...],
    class_kwargs: GridSettings,
    declared: GridSettings | None = None,
) -> GridSettings:
    """Merge grid settings from bases, class-header kwargs, and body dict."""
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


def _layout_constraint_for_field(
    field: GridFieldInfo,
    content_length: int | None = None,
) -> _GridLayoutConstraint:
    if field.fit:
        return _GridLayoutConstraint(
            "content",
            max(0, content_length if content_length is not None else 0),
        )
    size = field.size
    if size is not None:
        if isinstance(size, tuple):
            return _GridLayoutConstraint("percentage", int(size[0] * 100))
        if isinstance(size, float):
            return _GridLayoutConstraint("percentage", int(size * 100))
        if isinstance(size, int):
            return _GridLayoutConstraint("length", size)
    return _GridLayoutConstraint(
        "fill", field.flex if field.flex is not None else 1
    )


def _build_grid_init(
    all_fields: dict[str, GridFieldInfo],
    defaults: dict[str, Any],
) -> Callable[..., None]:
    _MISSING = object()
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

    params = ["self", "*"]
    params.extend(required)
    for name in optional:
        if name in factory_names:
            params.append(f"{name}=__missing__")
        else:
            params.append(f"{name}=__defaults__['{name}']")

    lines = [f"def __init__({', '.join(params)}):"]
    for name in required + optional:
        if name in factory_names:
            lines.append(
                f"    self.{name} = __defaults__['{name}']() "
                f"if {name} is __missing__ else {name}"
            )
        else:
            lines.append(f"    self.{name} = {name}")
    for name in no_init:
        if name in factory_names:
            lines.append(f"    self.{name} = __defaults__['{name}']()")
        elif name in defaults:
            lines.append(f"    self.{name} = __defaults__['{name}']")
        else:
            lines.append(f"    self.{name} = None")
    lines.append("    self._grid_validate_init()")
    lines.append("    self.__post_init__()")

    globs: dict[str, Any] = {
        "__defaults__": defaults,
        "__missing__": _MISSING,
    }
    exec("\n".join(lines), globs)  # noqa: S102
    return globs["__init__"]


def _collect_field_mouse_handlers(
    cls: type,
    namespace: dict[str, Any],
    layout_fields: dict[str, GridFieldInfo],
) -> dict[str, Any]:
    """Map layout field names to ``@on_mouse`` / ``@on_click`` handlers."""
    from xnano.beta.hooks import _EventHooksRegistry as EventHooks

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
class _GridMeta(type):
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
            if getattr(base, "_grid_needs_mouse_geometry", False):
                needs_mouse_geometry = True
        setattr(cls, "_grid_has_slide_fields", has_slide_fields)
        setattr(cls, "_grid_needs_mouse_geometry", needs_mouse_geometry)

        # 5. Precompute static layout data
        needs_dynamic = any(
            f.fit or isinstance(f.size, float) or f.visible is None
            for f in fields.values()
        )
        static_names: list[str] = []
        static_constraints: list[_GridLayoutConstraint] = []
        if not needs_dynamic:
            for field_name, field in fields.items():
                if field.visible is False:
                    continue
                static_names.append(field_name)
                static_constraints.append(_layout_constraint_for_field(field))

        setattr(cls, "_grid_needs_dynamic_layout", needs_dynamic)
        setattr(cls, "_grid_static_field_names", static_names)
        setattr(cls, "_grid_static_constraints", static_constraints)

        all_fields = {**fields, **state_fields}
        if name != "Grid" and all_fields:
            type.__setattr__(
                cls, "__init__", _build_grid_init(all_fields, defaults)
            )

        return cls


class Grid(metaclass=_GridMeta):
    """Declarative layout container for a terminal-based UI.

    Grid-scoped settings may be declared on the class header
    (``class Dashboard(Grid, direction="horizontal", gap=1): ...``),
    in a class-level ``grid_settings`` dict, or both — values in
    ``grid_settings`` override matching header kwargs.

    Examples:

    Layout fields render content; ``state=True`` fields hold app data.
    Nested ``Grid`` subclasses compose larger layouts:

    ```python
    from xnano.beta import Field, Grid, Terminal

    class Sidebar(Grid, direction="vertical"):
        nav: str = Field(default="Home", border="rounded", flex=1)

    class App(Grid, direction="horizontal", gap=1):
        sidebar: Sidebar = Field(default_factory=Sidebar, size=0.25)
        content: str = Field(default="Main area", flex=1)

        selected: int = Field(default=0, state=True)

    Terminal().run(App())
    ```

    Event hooks register handlers on the grid class. Use ``@on_click`` to
    scope mouse handlers to a layout field's region:

    ```python
    from xnano.beta import (
        Context,
        Field,
        Grid,
        Terminal,
        on_click,
        on_keyboard,
        on_tick,
    )

    class Counter(Grid, direction="vertical", gap=1):
        label: str = Field(default="Count: 0", size=1)
        body: str = Field(default="Click me", flex=1)

        count: int = Field(default=0, state=True)

        @on_keyboard("up")
        def increment(self) -> None:
            self.count += 1
            self.label = f"Count: {self.count}"

        @on_keyboard("down")
        def decrement(self) -> None:
            self.count -= 1
            self.label = f"Count: {self.count}"

        @on_click("body")
        def on_body(self, ctx: Context) -> None:
            self.body = "Clicked!"

        @on_tick(1000)
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
    _grid_needs_mouse_geometry: ClassVar[bool] = False
    _grid_frame: ClassVar[Frame | None] = None
    _grid_direction: ClassVar[Direction] = "vertical"
    _grid_gap: ClassVar[int] = 0
    _grid_needs_dynamic_layout: ClassVar[bool] = False
    _grid_static_field_names: ClassVar[list[str]] = []
    _grid_static_constraints: ClassVar[list[_GridLayoutConstraint]] = []
    _grid_defaults: ClassVar[dict[str, Any]] = {}

    visible: bool = True
    """Whether this grid is rendered in the live session."""
    z: int = 0
    """Z-index used when layering overlapping grids."""
    columns: int = 0
    """Terminal columns available to this grid — set by the session each frame."""
    rows: int = 0
    """Terminal rows available to this grid — set by the session each frame."""

    def __init__(self) -> None:
        self.__post_init__()

    def __post_init__(self) -> None:
        """Called at the end of the generated ``__init__``. Override to run post-construction logic."""

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
        from xnano.beta.utils.validation import layout_field_annotation

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

        from xnano.beta.exceptions import FieldValidationError
        from xnano.beta.utils.validation import validate_type

        try:
            return validate_type(value, ann)
        except ValidationError as exc:
            raise FieldValidationError(name, exc) from exc

    def _grid_validate_init(self) -> None:
        if not self._grid_strict:
            return
        for name, field in {
            **self._grid_fields,
            **self._grid_state_fields,
        }.items():
            value = getattr(self, name, None)
            validated = self._grid_validate_field(name, value, field=field)
            if validated is not value:
                object.__setattr__(self, name, validated)

    def __setattr__(self, name: str, value: Any) -> None:
        field = self._grid_state_fields.get(name)
        if field is not None and field.strict:
            value = self._grid_validate_field(name, value, field=field)
        object.__setattr__(self, name, value)

    @property
    def state(self) -> Any:
        """Return the active terminal's shared state, or ``None``."""
        from xnano.beta.terminal import _ACTIVE_TERMINAL

        terminal = _ACTIVE_TERMINAL.get()
        return None if terminal is None else terminal.state

    def grid_render(self) -> None:
        """Called each frame before layout.

        Override to refresh field values every frame. Initial values can be set
        with ``Field(default=...)``, ``default_factory``, or ``__post_init__``.
        """

    @overload
    def grid_play_effect(
        self,
        effect: AbstractEffect,
        *,
        fields: list[str] | None = None,
        key: str | None = None,
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
            key: Optional unique effect id prefix. Each field uses
                ``field_name`` when omitted, or ``{key}:{field_name}`` when set.

        Returns:
            ``True`` when at least one field area was found and an effect
            started.
        """
        from xnano.beta.effects import resolve_native_effect
        from xnano.beta.terminal import _ACTIVE_TERMINAL

        terminal = _ACTIVE_TERMINAL.get()
        if terminal is None:
            return False
        native_effect = resolve_native_effect(
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
        )
        return terminal.session.grid_play_effect(
            native_effect,
            fields=fields,
            key=key,
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
        if type(self)._grid_needs_mouse_geometry:
            return True
        overrides = getattr(self, "_grid_field_overrides", None)
        if overrides and any(field.slide for field in overrides.values()):
            return True
        if type(self)._grid_field_handlers:
            return True
        for field_name in self._grid_fields:
            if self._grid_field_info(field_name).slide:
                return True
            value = getattr(self, field_name, None)
            if isinstance(value, Grid) and value._grid_needs_mouse_geometry():
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

    def field_position(self, name: str) -> tuple[int, int]:
        """Return the parent-relative slide offset for a layout field."""
        return self._grid_field_position(name)

    def _grid_field_needs_hit(
        self, field_name: str, field: GridFieldInfo
    ) -> bool:
        if field.slide:
            return True
        return _resolve_grid_mouse_handler(self, field_name) is not None

    def grid_set_field(
        self,
        name: str,
        value: Any = UNSET,
        *,
        position: tuple[int, int] | None = None,
        **field_config: Any,
    ) -> None:
        """Set a layout field's runtime value and/or per-instance field metadata.

        Cannot be used on state fields. ``default``, ``default_factory``,
        ``init``, and ``state`` cannot be changed at runtime.
        """
        if name in self._grid_state_fields:
            raise TypeError(
                f"grid_set_field() cannot be used on state field {name!r} on "
                f"{type(self).__name__}"
            )
        if name not in self._grid_fields:
            raise AttributeError(
                f"{type(self).__name__} has no layout field {name!r}"
            )

        forbidden = _GRID_FIELD_IMMUTABLE_KEYS & field_config.keys()
        if forbidden:
            raise TypeError(
                f"grid_set_field() does not accept {', '.join(sorted(forbidden))}"
            )

        unknown = set(field_config) - _GRID_FIELD_CONFIG_KEYS
        if unknown:
            raise TypeError(
                "grid_set_field() got unexpected keyword arguments: "
                f"{', '.join(sorted(unknown))}"
            )

        if field_config:
            if "slide" in field_config:
                field_config = {
                    **field_config,
                    "slide": _normalize_slide_axes(field_config["slide"]),
                }
            overrides = self.__dict__.setdefault("_grid_field_overrides", {})
            overrides[name] = dataclasses.replace(
                self._grid_field_info(name),
                **field_config,
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

    def _grid_resolve_visible(self, field: GridFieldInfo, value: Any) -> bool:
        if field.visible is None:
            return value is not None
        return bool(field.visible)

    def _grid_field_frame(self, field: GridFieldInfo) -> Frame | None:
        f = Frame(
            background=field.background,
            border=field.border,
            border_color=field.border_color,
            border_sides=list(field.border_sides)
            if field.border_sides is not None
            else None,
            title=field.title,
            title_position=field.title_position,
            padding=field.padding,
        )
        return None if f.is_empty() else f

    def _grid_register_field_hit(
        self,
        field_name: str,
        paint_area: Area,
        *,
        slot_area: Area,
        parent_area: Area,
        slide_axes: list[str] | None = None,
    ) -> None:
        from xnano.beta.terminal import _ACTIVE_TERMINAL

        terminal = _ACTIVE_TERMINAL.get()
        if terminal is None or not terminal._mouse_geometry_active:
            return
        terminal._field_hits.append(
            _GridFieldHit(
                grid=self,
                field_name=field_name,
                area=paint_area,
                slot_area=slot_area,
                parent_area=parent_area,
                slide_axes=slide_axes or [],
            )
        )

    def _grid_build_frame(self, area: Area, session: Any) -> None:
        self.columns = area.width
        self.rows = area.height
        self.grid_render()
        self._grid_assemble(area, session)

    def _grid_assemble(self, area: Area, session: Any) -> None:
        if not self.visible:
            return

        self._grid_last_parent_area = area
        self._grid_last_slot_areas = {}

        fields = self._grid_fields

        if not fields:
            if self._grid_frame is not None:
                session.grid_paint_frame(area, self._grid_frame, z=self.z)
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
                if field.fit:
                    content_length = session.grid_measure_slot(
                        value, self._grid_direction, field
                    )
                active_names.append(field_name)
                active_fields.append(field)
                active_values.append(value)
                active_constraints.append(
                    _layout_constraint_for_field(field, content_length)
                )

        if not active_names:
            if self._grid_frame is not None:
                session.grid_paint_frame(area, self._grid_frame, z=self.z)
            return

        inner = area
        if self._grid_frame is not None:
            inner = session.grid_paint_frame(area, self._grid_frame, z=self.z)

        slot_areas = session.grid_split_layout(
            inner,
            self._grid_direction,
            self._grid_gap,
            active_constraints,
        )

        for index, slot_area in enumerate(slot_areas):
            field_name = active_names[index]
            field = active_fields[index]
            value = active_values[index]
            self._grid_last_slot_areas[field_name] = slot_area
            slide_axes = field.slide or []
            paint_area = _grid_slide_paint_area(
                area,
                slot_area,
                slide_axes,
                self._grid_field_position(field_name),
            )
            if self._grid_field_needs_hit(field_name, field):
                self._grid_register_field_hit(
                    field_name,
                    paint_area,
                    slot_area=slot_area,
                    parent_area=area,
                    slide_axes=slide_axes,
                )
            field_frame = self._grid_field_frame(field)
            if field_frame is not None:
                paint_area = session.grid_paint_frame(
                    paint_area, field_frame, z=self.z
                )
            if value is None:
                continue
            session.grid_paint_slot(
                value,
                paint_area,
                field,
                parent_z=self.z,
                effect_key=field_name,
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
    grid: Grid, field_name: str
) -> Callable[..., Any] | None:
    """Return the field-bound mouse handler for ``field_name`` on ``grid``."""
    from xnano.beta.hooks import _EventHooksRegistry as EventHooks

    for cls in type(grid).__mro__:
        if not (isinstance(cls, type) and issubclass(cls, Grid)):
            continue
        handlers = cls.__dict__.get("_grid_field_handlers")
        if not isinstance(handlers, dict) or field_name not in handlers:
            continue
        attr = handlers[field_name]
        if not hasattr(attr, EventHooks.ON_MOUSE_HOOK_ATTR):
            return None
        return attr.__get__(grid, cls)
    return None
