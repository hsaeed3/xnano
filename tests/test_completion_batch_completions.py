# Batch Completions test for .completion()

from xnano import completion
from pydantic import BaseModel
import pytest


# single model, multiple thread batch job
def test_single_model_batch_job():

    messages = [
        [{"role" : "user", "content" : "How are you?"}],
        [
            {"role" : "system", "content" : "The user's favorite color is green."},
            {"role" : "user", "content" : "What is my favorite color?"}
        ]
    ]

    response = completion(
        messages = messages,
        model = "openai/gpt-4o-mini"
    )

    assert len(response) == 2
    assert isinstance(response[0].model_dump(), dict)
    assert isinstance(response[1].model_dump(), dict)


# test mutiple model batch job
def test_multiple_model_batch_job():

    models = ["openai/gpt-4o", "openai/gpt-4o-mini"]

    response = completion(
        {"role" : "user", "content" : "hi"},
        model = models
    )

    assert len(response) == 2
    assert isinstance(response[0].model_dump(), dict)
    assert isinstance(response[1].model_dump(), dict)


# test batch structured outputs
def test_batch_job_structured_outputs():

    class User(BaseModel):
        name: str
        age: int

    response = completion(
        [[{"role": "user", "content": "Extract john is 20 years old"}], [{"role": "user", "content": "Extract jane is 30 years old"}]],
        response_model = User
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
        "extract john is 20 years old",
        model = models,
        response_model = User
    )

    assert len(response) == 2
    assert isinstance(response[0].model_dump(), dict)
    assert isinstance(response[1].model_dump(), dict)

    assert response[0].name.lower() == "john"
    assert response[1].name.lower() == "john"
