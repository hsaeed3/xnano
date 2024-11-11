__all__ = [
    # completions / main
    "Completions",
    "completion", "acompletion",

    # basemodel / pydantic
    "BaseModel",
    "patch", "unpatch",

    # llm resources
    "classify", 
    "extract",
    "coder", 
    "function",

    # data
    "chunk",
    "embedding",
    "read",
    "read_url",
    "scrape",
    "web_search",

    "audio",
    "image",
    "transcribe"
]


from .completions import (
    Completions, completion, acompletion
)

from .pydantic import (
    BaseModel, patch, unpatch
)

from .resources.classifier import classify
from .resources.extractor import extract
from .resources.code_generators import coder, function
from .resources.multimodal import audio, image, transcribe

from .data.chunker import chunk
from .data.embedder import embedding
from .data.reader import read
from .data.scraper import scrape
from .data.url_reader import read_url
from .data.web_search import web_search

