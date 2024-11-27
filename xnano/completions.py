# xnano . completions

__all__ = [
    "completion",
    "async_completion"
]

# methods located at
# xnano.resources.completions.main
# this resource is the core of the library

from .resources.completions._routing import completion, async_completion