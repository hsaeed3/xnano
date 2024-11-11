
__all__ = [
    # base completions 
    "Completions",
    "completion", "acompletion",
    # code generation
    "coder", "function",

    # pydantic utility
    "BaseModel", "Field", "patch", "unpatch",

    # documents
    "read_documents",

    # nlp
    "classify", "aclassify",
    "extract", "aextract",
    "chunk", "embedding",

    # embeddings
    "Embeddings",
]


# completions // code gen
from .completions import Completions, completion, acompletion, coder, function
# pydantic
from .pydantic import BaseModel, Field, patch, unpatch
# docs
from .documents import read_documents
# nlp
from .nlp import classify, aclassify, extract, aextract, chunk, embedding
# embeddings
from .embeddings import Embeddings