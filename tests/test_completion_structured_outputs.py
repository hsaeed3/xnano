# Structured Outputs Test

from xnano import completion
from pydantic import BaseModel
import pytest


# standard instructor completion
def test_structured_output_with_pydantic_response_model():

    class User(BaseModel):
        name: str
        age: int

    response = completion(
        "Extract john is 20 years old",
        response_model = User
    )

    assert isinstance(response, User)

    assert isinstance(response.name, str)
    assert isinstance(response.age, int)


# using string response model
def test_structured_output_with_string_response_model():

    response = completion(
        "Extract john is 20 years old",
        response_model = ["name", "age : int"]
    )

    assert isinstance(response.name, str)
    assert isinstance(response.age, int)


# using type hint response model
def test_structured_output_with_type_hint_response_model():

    response = completion(
        "Extract john is 20 years old",
        response_model = int
    )

    assert isinstance(response, int)
    assert response == 20


# test with `response_format`
def test_structured_output_with_response_format():

    class User(BaseModel):
        name: str
        age: int

    response = completion(
        "Extract john is 20 years old",
        response_format = User
    )

    assert isinstance(response, User)

    assert isinstance(response.name, str)
    assert isinstance(response.age, int)


def test_structured_output_with_instructor_mode():

    class User(BaseModel):
        name: str
        age: int

    response = completion(
        "Extract john is 20 years old",

        model = "anthropic/claude-3-5-haiku-latest",
        response_model = User,
        instructor_mode = "markdown_json_mode"
    )

    assert isinstance(response, User)

    assert isinstance(response.name, str)
    assert isinstance(response.age, int)


