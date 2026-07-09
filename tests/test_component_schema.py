"""Tests for the declarative descriptor + metaclass infrastructure."""

from __future__ import annotations

from typing import cast

from xnano.beta.components.schema import (
    Column,
    ComponentDescriptor,
    DeclarativeComponentMeta,
    Series,
)


def _declared(cls: type) -> dict[str, ComponentDescriptor]:
    return cast(dict[str, ComponentDescriptor], getattr(cls, "_declared"))


# ---------------------------------------------------------------------------
# Column value / text / color resolution
# ---------------------------------------------------------------------------


def test_column_header_derived_from_name() -> None:
    col = Column()
    col.name = "latency_ms"
    assert col.resolve_header() == "Latency Ms"


def test_column_header_explicit() -> None:
    col = Column(header="RPS")
    col.name = "rps"
    assert col.resolve_header() == "RPS"


def test_column_value_from_dict() -> None:
    col = Column()
    col.name = "status"
    assert col.resolve_value({"status": "ok"}) == "ok"


def test_column_value_from_object() -> None:
    class Row:
        status = "degraded"

    col = Column()
    col.name = "status"
    assert col.resolve_value(Row()) == "degraded"


def test_column_value_missing_is_none() -> None:
    col = Column()
    col.name = "missing"
    assert col.resolve_value({"a": 1}) is None


def test_column_accessor_overrides_lookup() -> None:
    col = Column(accessor=lambda row: row["a"] + row["b"])
    col.name = "sum"
    assert col.resolve_value({"a": 2, "b": 3}) == 5


def test_column_text_default_str() -> None:
    col = Column()
    assert col.resolve_text(42) == "42"


def test_column_text_none_is_empty() -> None:
    col = Column()
    assert col.resolve_text(None) == ""


def test_column_text_format_template() -> None:
    col = Column(format="{}ms")
    assert col.resolve_text(12) == "12ms"


def test_column_text_format_callable() -> None:
    col = Column(format=lambda v: f"${v:.2f}")
    assert col.resolve_text(3) == "$3.00"


def test_column_static_color() -> None:
    col = Column(color="green")
    assert col.resolve_color("anything") == "green"


def test_column_value_dependent_color() -> None:
    col = Column(color=lambda v: "green" if v == "ok" else "red")
    assert col.resolve_color("ok") == "green"
    assert col.resolve_color("bad") == "red"


def test_column_value_dependent_background() -> None:
    col = Column(background=lambda v: "black" if v else None)
    assert col.resolve_background(True) == "black"
    assert col.resolve_background(False) is None


# ---------------------------------------------------------------------------
# Series resolution
# ---------------------------------------------------------------------------


def test_series_label_derived_from_name() -> None:
    s = Series()
    s.name = "p99"
    assert s.resolve_label() == "p99"


def test_series_label_explicit() -> None:
    s = Series(label="99th percentile")
    s.name = "p99"
    assert s.resolve_label() == "99th percentile"


def test_series_is_component_descriptor() -> None:
    assert isinstance(Series(), ComponentDescriptor)
    assert isinstance(Column(), ComponentDescriptor)


# ---------------------------------------------------------------------------
# Metaclass capture
# ---------------------------------------------------------------------------


class _Declared(metaclass=DeclarativeComponentMeta):
    a = Column()
    b = Column(header="Bee")
    plain = 5  # not a descriptor — left alone


def test_metaclass_captures_descriptors() -> None:
    assert set(_declared(_Declared)) == {"a", "b"}


def test_metaclass_sets_descriptor_names() -> None:
    assert _declared(_Declared)["a"].name == "a"
    assert _declared(_Declared)["b"].name == "b"


def test_metaclass_removes_descriptors_from_class() -> None:
    # descriptors are captured, not left as raw class attributes
    assert not isinstance(getattr(_Declared, "a", None), Column)


def test_metaclass_leaves_non_descriptors() -> None:
    assert _Declared.plain == 5


def test_metaclass_preserves_declaration_order() -> None:
    assert list(_declared(_Declared)) == ["a", "b"]


# ---------------------------------------------------------------------------
# Inheritance
# ---------------------------------------------------------------------------


class _Base(metaclass=DeclarativeComponentMeta):
    x = Column()


class _Child(_Base):
    y = Column()


def test_metaclass_inherits_base_descriptors() -> None:
    assert set(_declared(_Child)) == {"x", "y"}


def test_metaclass_base_unaffected_by_child() -> None:
    assert set(_declared(_Base)) == {"x"}


def test_metaclass_inheritance_order_base_first() -> None:
    assert list(_declared(_Child)) == ["x", "y"]
