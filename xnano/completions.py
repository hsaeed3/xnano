# xnano
# hammad saeed // 2024

# main exports

__all__ = [
    # completions // no client
    "completion",
    "acompletion",
    # methods
    "generate_code",
    "function",
    "generate_system_prompt",
    "generate_qa_pairs",
    "validate",
    "avalidate",
    "classify",
    "aclassify",
    "extract",
    "aextract",
]

# imports

from .resources.completions.main import completion, acompletion
from .resources.completions.classifier import classify, aclassify
from .resources.completions.extractor import extract, aextract
from .resources.completions.code_generators import generate_code, function
from .resources.completions.prompting import generate_system_prompt
from .resources.completions.question_answer import generate_qa_pairs
from .resources.completions.validator import validate, avalidate
