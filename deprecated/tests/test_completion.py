# Completion Tests

import asyncio
from typing import Generator
from xnano import completion, async_completion
from pydantic import BaseModel
import pytest


# ------------------------------------------------------------
# base tests
# ------------------------------------------------------------


def test_completion_defaults():
    response = completion({"role": "user", "content": "Hello, world!"})

    assert isinstance(response.choices[0].message.content, str)


def test_completion_string_input():
    response = completion("Hello, world!")

    assert isinstance(response.choices[0].message.content, str)


def test_completion_stream():
    response = completion("Repeat after me: I am a happy person", stream=True)

    content = ""

    for chunk in response:
        content += chunk.choices[0].delta.content or ""

    assert "happy" in content.lower()


@pytest.mark.asyncio
async def test_completion_async():
    response = await async_completion("Hello, world!")

    assert isinstance(response.choices[0].message.content, str)


# ------------------------------------------------------------
# context tests
# ------------------------------------------------------------


def test_completion_context():
    context = "My favorite color is blue."

    response = completion(
        "What is my favorite color?",
        context=context,
    )

    assert "blue" in response.choices[0].message.content


# ------------------------------------------------------------
# structured output tests
# ------------------------------------------------------------


def test_completion_structured_output_with_pydantic_response_model():
    class User(BaseModel):
        name: str
        age: int

    response = completion("Extract john is 20 years old", response_model=User)

    assert isinstance(response, User)

    assert isinstance(response.name, str)
    assert isinstance(response.age, int)


# using string response model
def test_completion_structured_output_with_string_response_model():
    response = completion(
        "Extract john is 20 years old", response_model=["name", "age : int"]
    )

    assert isinstance(response.name, str)
    assert isinstance(response.age, int)


# using type hint response model
def test_completion_structured_output_with_type_hint_response_model():
    response = completion("Extract john is 20 years old", response_model=int)

    assert isinstance(response, int)
    assert response == 20


# test with `response_format`
def test_completion_structured_output_with_response_format():
    class User(BaseModel):
        name: str
        age: int

    response = completion("Extract john is 20 years old", response_format=User)

    assert isinstance(response, User)

    assert isinstance(response.name, str)
    assert isinstance(response.age, int)


def test_completion_structured_output_with_instructor_mode():
    class User(BaseModel):
        name: str
        age: int

    response = completion(
        "Extract john is 20 years old",
        model="anthropic/claude-3-5-haiku-latest",
        response_model=User,
        instructor_mode="markdown_json_mode",
    )

    assert isinstance(response, User)

    assert isinstance(response.name, str)
    assert isinstance(response.age, int)


# ------------------------------------------------------------
# tool use tests
# ------------------------------------------------------------


# Test tool calling with openai function
def test_completion_with_openai_function():
    tool = {
        "type": "function",
        "function": {
            "name": "book_flight",
            "strict": True,
            "parameters": {
                "properties": {
                    "destination": {"title": "Destination", "type": "string"},
                    "return_date": {"title": "Return Date", "type": "string"},
                },
                "required": ["destination", "return_date"],
                "title": "book_flight",
                "type": "object",
                "additionalProperties": False,
            },
        },
    }

    response = completion(
        "Book a flight to Tokyo for return on 2025-01-01", tools=[tool]
    )

    assert response.choices[0].message.tool_calls[0].function.name == "book_flight"


def test_completion_with_function_tool():
    def book_flight(destination: str, return_date: str):
        return f"Booking a flight to {destination} for return on {return_date}"

    response = completion(
        "Book a flight to Tokyo for return on 2025-01-01", tools=[book_flight]
    )

    assert response.choices[0].message.tool_calls[0].function.name == "book_flight"


def test_completion_with_pydantic_model_tool():
    class BookFlight(BaseModel):
        destination: str
        return_date: str

    response = completion(
        "Book a flight to Tokyo for return on 2025-01-01", tools=[BookFlight]
    )

    assert response.choices[0].message.tool_calls[0].function.name == "BookFlight"


def test_completion_with_tool_execution():
    def book_flight(destination: str, return_date: str):
        return f"Booking a flight to {destination} for return on {return_date}"

    response = completion(
        "Book a flight to Tokyo for return on 2025-01-01",
        tools=[book_flight],
        run_tools=True,
    )

    assert response.choices[0].message.content != None


def test_completion_with_tool_execution_and_returned_messages():
    def book_flight(destination: str, return_date: str):
        return f"Booking a flight to {destination} for return on {return_date}"

    response = completion(
        "Book a flight to Tokyo for return on 2025-01-01",
        tools=[book_flight],
        run_tools=True,
        return_messages=True,
    )

    assert isinstance(response, list)
    assert len(response) == 3


# ------------------------------------------------------------
# batch completions tests
# ------------------------------------------------------------


# single model, multiple thread batch job
def test_single_model_batch_job():
    messages = [
        [{"role": "user", "content": "How are you?"}],
        [
            {"role": "system", "content": "The user's favorite color is green."},
            {"role": "user", "content": "What is my favorite color?"},
        ],
    ]

    response = completion(messages=messages, model="openai/gpt-4o-mini")

    assert len(response) == 2
    assert isinstance(response[0].model_dump(), dict)
    assert isinstance(response[1].model_dump(), dict)


# test mutiple model batch job
def test_multiple_model_batch_job():
    models = ["openai/gpt-4o", "openai/gpt-4o-mini"]

    response = completion({"role": "user", "content": "hi"}, model=models)

    assert len(response) == 2
    assert isinstance(response[0].model_dump(), dict)
    assert isinstance(response[1].model_dump(), dict)


# test batch structured outputs
def test_batch_job_structured_outputs():
    class User(BaseModel):
        name: str
        age: int

    response = completion(
        [
            [{"role": "user", "content": "Extract john is 20 years old"}],
            [{"role": "user", "content": "Extract jane is 30 years old"}],
        ],
        response_model=User,
    )

    assert isinstance(response[0].model_dump(), dict)
    assert isinstance(response[1].model_dump(), dict)

    assert response[0].name.lower() == "john"
    assert response[1].name.lower() == "jane"


# multiple model batch job with structured outputs
def test_multiple_model_batch_job_structured_outputs():
    class User(BaseModel):
        name: str
        age: int

    models = ["openai/gpt-4o", "openai/gpt-4o-mini"]

    response = completion(
        "extract john is 20 years old", model=models, response_model=User
    )

    assert len(response) == 2
    assert isinstance(response[0].model_dump(), dict)
    assert isinstance(response[1].model_dump(), dict)

    assert response[0].name.lower() == "john"
    assert response[1].name.lower() == "john"
