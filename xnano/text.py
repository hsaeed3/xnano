# xnano . text
# text readers//processors

__all__ = [
    "text_reader",
    "text_embeddings",
    "text_chunker"
]

from .resources.text._routing import (
    text_reader,
    text_embeddings,
    text_chunker
)
