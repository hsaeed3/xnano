# Generator Function Tests

from pydantic import BaseModel
from xnano import (
    generate_classification,
    generate_code,
    generate_extraction,
    generate_function,
    generate_qa_pairs,
    generate_sql,
    generate_questions,
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
        inputs = inputs,
        labels = labels,
        classification = "single"
    )

    assert isinstance(response, list)

    assert response[0].label == "positive"
    assert response[1].label == "negative"


def test_generators_multi_label_classification():

    inputs = ["I am a happy and sad person"]
    labels = ["positive", "negative"]

    response = generate_classification(
        inputs = inputs,
        labels = labels,
        classification = "multi"
    )

    assert isinstance(response.label, list)

    assert response.label == ["positive", "negative"]


# ------------------------------------------------------------
# code generation
# ------------------------------------------------------------


def test_generators_code_generation():

    response = generate_code(
        instructions = "Create a logger named `my_logger` that logs to the console"
    )

    from logging import Logger

    assert isinstance(response, Logger)


def test_generators_function_generator():

    @generate_function()
    def add_two_numbers(a: int, b: int) -> int:
        """A function that adds two numbers"""

    assert add_two_numbers(2, 3) == 5


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
