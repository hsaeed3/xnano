# Generator Function Tests

from pydantic import BaseModel
from xnano import (
    generate_classification,
    generate_code,
    generate_extraction,
    generate_function,
    generate_qa_pairs,
    generate_sql,
    generate_system_prompt,
    generate_validation,
    generate_chunks,
)
import pytest


# ------------------------------------------------------------
# classification
# ------------------------------------------------------------


def test_generators_single_label_classification():
    inputs = ["I am a happy person", "I am a sad person"]
    labels = ["positive", "negative"]

    response = generate_classification(
        inputs=inputs, labels=labels, classification="single"
    )

    assert isinstance(response, list)

    assert response[0].label == "positive"
    assert response[1].label == "negative"


def test_generators_multi_label_classification():
    inputs = ["I am a happy and sad person"]
    labels = ["positive", "negative"]

    response = generate_classification(
        inputs=inputs, labels=labels, classification="multi"
    )

    assert isinstance(response.label, list)

    assert response.label == ["positive", "negative"]


# ------------------------------------------------------------
# code generation
# ------------------------------------------------------------


def test_generators_code_generation():
    response = generate_code(
        instructions="Create a logger named `my_logger` that logs to the console"
    )

    from logging import Logger

    assert isinstance(response, Logger)


def test_generators_function_generator():
    @generate_function()
    def add_two_numbers(a: int, b: int) -> int:
        """A function that adds two numbers"""

    assert add_two_numbers(2, 3) == 5


# ------------------------------------------------------------
# sql
# ------------------------------------------------------------


def test_generators_sql_query():
    class Content(BaseModel):
        title: str
        content: str

    content = Content(
        title="My First Post", content="This is the content of my first post"
    )

    response = generate_sql(
        input=content,
        objective="Create a SQL query to get the title and content of the post",
    )

    assert isinstance(response.query, str)


# ------------------------------------------------------------
# extraction
# ------------------------------------------------------------


def test_generators_extraction():
    class Extraction(BaseModel):
        name: str
        age: int

    response = generate_extraction(
        target=Extraction, text="My name is John and I am 30 years old"
    )

    assert isinstance(response, Extraction)
    assert response.name == "John"
    assert response.age == 30


def test_generators_extraction_batch_inputs():
    class Extraction(BaseModel):
        name: str
        age: int

    inputs = [
        "My name is John and I am 30 years old",
        "My name is Jane and I am 25 years old",
    ]

    response = generate_extraction(
        target=Extraction, text=inputs, process="batch", batch_size=1
    )

    assert len(response) == 2

    assert response[0].name.lower() == "john"
    assert response[0].age == 30
    assert response[1].name.lower() == "jane"
    assert response[1].age == 25


# ----------------------------------------------------------
# system prompts
# ----------------------------------------------------------


def test_generators_system_prompt():
    response = generate_system_prompt(
        instructions="Create a system prompt for a chatbot with tools",
        response_format="dict",
    )

    assert "role" in response[0]
    assert response[0]["content"] is not None


# ----------------------------------------------------------
# qa pairs
# ----------------------------------------------------------


def test_generators_create_qa_pairs():
    response = generate_qa_pairs(
        input_text="""
        Is your child having trouble tying their shoes? Need tips on teaching your child to tie their shoes? Follow the Occupational Therapy Institute’s instructions on How to Tie Your Shoes in 6 Steps!

        Hold one lace in each hand and pull to make shoes tighter.
        Cross over laces to make an "X."
        Tuck the top lace under the bottom lace and pull it through. Pull to tighten.
        Make bunny loops on both sides and make an "X."
        Take the bottom loop and tuck it over top loop. Pull through.
        Pull on bunny ears to make tighter. Repeat steps 4 & 5 for extra security!
        """,
        num_questions=2,
    )

    assert isinstance(response.questions, list)

    assert len(response.questions) == 2

    for question in response.questions:
        assert question.question is not None
        assert question.answer is not None


# ----------------------------------------------------------
# validator
# ----------------------------------------------------------


def test_generators_validator_guardrails():
    response = generate_validation(
        inputs="I want to jump off a cliff",
        guardrails="Ensure the conversation is safe & appropriate",
    )

    assert response.violates_guardrails == True


# ------------------------------------------------------------
# chunker
# ------------------------------------------------------------


def test_generators_chunk_generation():
    text = """
    How do I decide what to put in a paragraph?

    Before you can begin to determine what the composition of a particular paragraph will be, you must first decide on an argument and a working thesis statement for your paper. What is the most important idea that you are trying to convey to your reader? The information in each paragraph must be related to that idea. In other words, your paragraphs should remind your reader that there is a recurrent relationship between your thesis and the information in each paragraph. A working thesis functions like a seed from which your paper, and your ideas, will grow. The whole process is an organic one—a natural progression from a seed to a full-blown paper where there are direct, familial relationships between all of the ideas in the paper.

    The decision about what to put into your paragraphs begins with the germination of a seed of ideas; this “germination process” is better known as brainstorming. There are many techniques for brainstorming; whichever one you choose, this stage of paragraph development cannot be skipped. Building paragraphs can be like building a skyscraper: there must be a well-planned foundation that supports what you are building. Any cracks, inconsistencies, or other corruptions of the foundation can cause your whole paper to crumble.

    So, let's suppose that you have done some brainstorming to develop your thesis. What else should you keep in mind as you begin to create paragraphs? Every paragraph in a paper should be:

    Unified: All of the sentences in a single paragraph should be related to a single controlling idea (often expressed in the topic sentence of the paragraph).
    Clearly related to the thesis: The sentences should all refer to the central idea, or thesis, of the paper (Rosen and Behrens 119).
    Coherent: The sentences should be arranged in a logical manner and should follow a definite plan for development (Rosen and Behrens 119).
    Well-developed: Every idea discussed in the paragraph should be adequately explained and supported through evidence and details that work together to explain the paragraph's controlling idea (Rosen and Behrens 119).
    How do I organize a paragraph?

    There are many different ways to organize a paragraph. The organization you choose will depend on the controlling idea of the paragraph. Below are a few possibilities for organization, with links to brief examples:

    Narration: Tell a story. Go chronologically, from start to finish. (See an example.)
    Description: Provide specific details about what something looks, smells, tastes, sounds, or feels like. Organize spatially, in order of appearance, or by topic. (See an example.)
    Process: Explain how something works, step by step. Perhaps follow a sequence—first, second, third. (See an example.)
    Classification: Separate into groups or explain the various parts of a topic. (See an example.)
    Illustration: Give examples and explain how those examples support your point. (See an example in the 5-step process below.)
    """

    chunks = generate_chunks(text)

    assert isinstance(chunks, list)
