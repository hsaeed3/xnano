# xnano
# hammad saeed // 2024

# main exports

__all__ = [
    # completions // no client
    "completion",
    "acompletion",

    # methods
    "generate_code", "function",
    "generate_system_prompt",

    # lib
    "console",
]

# imports

from ._lib import console

from .resources.completions.main import completion, acompletion
from .resources.completions.code_generators import generate_code, function
from .resources.completions.prompting import generate_system_prompt


