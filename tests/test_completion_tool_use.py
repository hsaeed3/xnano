# Tool Use Test for .completion()

from xnano import completion
from pydantic import BaseModel
import pytest


# Test tool calling with openai function
def test_completion_with_openai_function():

    tool = {
        'type': 'function',
        'function': {
            'name': 'book_flight',
            'strict': True,
            'parameters': {
                'properties': {
                    'destination': {'title': 'Destination', 'type': 'string'},
                    'return_date': {'title': 'Return Date', 'type': 'string'}
                },
                'required': ['destination', 'return_date'],
                'title': 'book_flight',
                'type': 'object',
                'additionalProperties': False
            }
        }
    }

    response = completion(
        "Book a flight to Tokyo for return on 2025-01-01",
        tools = [tool]
    )

    assert response.choices[0].message.tool_calls[0].function.name == "book_flight"


def test_completion_with_function_tool():

    def book_flight(destination: str, return_date: str):
        return f"Booking a flight to {destination} for return on {return_date}"

    response = completion(
        "Book a flight to Tokyo for return on 2025-01-01",
        tools = [book_flight]
    )

    assert response.choices[0].message.tool_calls[0].function.name == "book_flight"


def test_completion_with_pydantic_model_tool():

    class BookFlight(BaseModel):
        destination: str
        return_date: str

    response = completion(
        "Book a flight to Tokyo for return on 2025-01-01",
        tools = [BookFlight]
    )

    assert response.choices[0].message.tool_calls[0].function.name == "BookFlight"


def test_completion_with_tool_execution():

    def book_flight(destination: str, return_date: str):
        return f"Booking a flight to {destination} for return on {return_date}"

    response = completion(
        "Book a flight to Tokyo for return on 2025-01-01",
        tools = [book_flight],
        run_tools = True
    )

    assert response.choices[0].message.content != None


def test_completion_with_tool_execution_and_returned_messages():

    def book_flight(destination: str, return_date: str):
        return f"Booking a flight to {destination} for return on {return_date}"

    response = completion(
        "Book a flight to Tokyo for return on 2025-01-01",
        tools = [book_flight],
        run_tools = True,
        return_messages = True
    )

    assert isinstance(response, list)
    assert len(response) == 3