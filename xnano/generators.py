# xnano . generators

__all__ = [
    "generate_code",
    "generate_function",
    "generate_classification",
    "async_generate_classification",
    "generate_chunks",
    "generate_extraction",
    "async_generate_extraction",
    "generate_sql",
    "generate_system_prompt",
    "generate_qa_pairs",
    "generate_answers",
    "generate_questions",
    "generate_validation",
    "async_generate_validation",
    "generate_web_extraction"
]

# xnano follows a generate_ namespace, to help
# identify functions that use LLMS to make calls
# this is essentially so things like a confusion of

# .text_chunker() & .generate_chunks() are easily distinguishable
# as one not being an llm method

from .resources.generators._routing import (
    generate_code,
    generate_function,
    generate_classification,
    async_generate_classification,
    generate_chunks,
    generate_extraction,
    async_generate_extraction,
    generate_sql,
    generate_system_prompt,
    generate_qa_pairs,
    generate_answers,
    generate_questions,
    generate_validation,
    async_generate_validation,
    generate_web_extraction 
)
