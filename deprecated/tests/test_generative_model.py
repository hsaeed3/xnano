# Generative Model Tests

from xnano import GenerativeModel, model_patch
from pydantic import BaseModel
from typing import Literal
import pytest


# Initializing Model Directly
def test_generative_model_init():
    class Person(GenerativeModel):
        name: str
        age: int

    person = Person(name="John", age=30)

    assert person.name == "John" and person.age == 30
    assert isinstance(person, Person) and issubclass(Person, BaseModel)


# Patching Pydantic Models
def test_generative_model_patch():
    @model_patch
    class Person(BaseModel):
        name: str
        age: int

    person = Person(name="John", age=30)

    assert person.name == "John" and person.age == 30


# -------------------------------------------------------------------------------------------------
# Generation Tests
# -------------------------------------------------------------------------------------------------


def test_generative_model_generate_single():
    class Information(GenerativeModel):
        instruction: str

    information = Information.model_generate()

    assert information.instruction is not None


def test_generative_model_generate_single_with_messages():
    class Information(GenerativeModel):
        instruction: str

    information = Information.model_generate(messages="How do i tie my shoes?")

    assert information.instruction is not None
    assert "shoe" in information.instruction.lower()


def test_generative_model_generate_multiple():
    class Person(GenerativeModel):
        name: str
        age: int

    people = Person.model_generate(n=2)

    assert len(people) == 2


def test_generative_model_field_regeneration():
    class Weather(GenerativeModel):
        condition: Literal["summer", "winter", "spring", "fall"]
        weather: str

    weather = Weather(condition="summer", weather="snowing")

    weather = weather.model_generate(
        messages="Please update the condition", fields=["condition"]
    )

    assert weather.condition != "summer"
    assert weather.condition in ["winter", "spring", "fall"]


# -------------------------------------------------------------------------------------------------
# Completion Tests
# -------------------------------------------------------------------------------------------------


def test_generative_model_completion():
    class Color(GenerativeModel):
        color: str

    color = Color(color="blue")

    response = color.model_completion(messages="What is my favorite color?")

    assert "blue" in response.choices[0].message.content.lower()
