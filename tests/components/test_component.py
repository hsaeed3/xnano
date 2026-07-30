"""tests.components.test_component"""

from __future__ import annotations

from typing import Any, cast

import xnano.components as components
from xnano.components.component import Component, ComponentRenderContext
from xnano.components.schema import Column
from xnano.types import Area, Size


def test_public_component_exports_are_resolvable() -> None:
    for name in components.__all__:
        assert getattr(components, name) is not None
    assert set(dir(components)) >= set(components.__all__)


def test_unknown_component_export_has_normal_attribute_error() -> None:
    try:
        getattr(components, "MissingHero")
    except AttributeError as error:
        assert "MissingHero" in str(error)
    else:
        raise AssertionError("missing export unexpectedly resolved")


def test_component_default_extension_contracts_are_noops() -> None:
    component = Component()
    ctx = ComponentRenderContext[Any](
        area=Area(x=1, y=2, width=10, height=4),
        state={"ready": True},
    )
    area = ctx.area

    assert component.focused is False
    assert component.get_frame() is None
    assert component.get_size(ctx) == Size(width=0, height=0)
    assert component.before_render(ctx, area) == area
    assert component.after_render(ctx, area) is None
    assert component.compose(ctx) is None
    assert component.compose_extra_small(ctx) is None
    assert component.compose_small(ctx) is None
    assert component.compose_medium(ctx) is None
    assert component.compose_large(ctx) is None
    assert component.compose_extra_large(ctx) is None
    assert component.handle_keyboard(cast(Any, object())) is False
    assert component.handle_paste("text") is False


def test_component_descriptors_are_inherited_without_shared_mutation() -> None:
    class Base(Component):
        value: int = Column(header="Base")

    class Child(Base):
        pass

    assert Base._declared["value"].name == "value"
    assert Child._declared["value"].name == "value"
    assert Child._declared["value"] is Base._declared["value"]
