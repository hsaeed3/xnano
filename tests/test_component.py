"""Tests for xnano.component module - declarative component system."""

import dataclasses
import pytest
from xnano.buffer import Buffer, render_widget
from xnano.component import Component
from xnano.layout import Rectangle
from xnano.widgets import Paragraph


@dataclasses.dataclass
class CustomHeader(Component[str]):
    """A custom component for testing."""

    def render(self, area: Rectangle) -> Paragraph:
        return Paragraph(self.state)


class TestComponent:
    """Tests for Component class."""

    def test_abstract_class_instantiation(self):
        with pytest.raises(TypeError):
            Component()  # type: ignore

    def test_component_rendering(self):
        area = Rectangle(x=0, y=0, width=20, height=2)
        buf = Buffer.empty(area)

        comp = CustomHeader(state="Test Component")
        render_widget(comp, area, buf)

        # Check that the component successfully rendered its contents to the buffer
        lines = buf.lines()
        assert lines[0].startswith("Test Component")

    def test_component_state_update(self):
        comp = CustomHeader(state="Initial")
        updated = False

        def on_update(c: CustomHeader):
            nonlocal updated
            updated = True
            assert c.state == "New Title"

        comp.register_on_update(on_update)
        comp.update_state("New Title")

        assert updated
        assert comp.state == "New Title"

    def test_component_update_invalid_attribute(self):
        comp = CustomHeader(state="Test")
        with pytest.raises(AttributeError):
            comp.update(non_existent_field="value")
