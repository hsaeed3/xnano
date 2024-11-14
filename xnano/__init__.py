# hammad saeed // 2024
# no classes now imported at top level

__all__ = [
    "completion",
    "acompletion",
    "generate_code",
    "function",
    "generate_system_prompt",
    "classify",
    "aclassify",
    "extract",
    "aextract",
    "validate",
    "avalidate",
    "generate_qa_pairs",
    "text_reader",
    "text_chunker",
    "generate_embeddings",
    "web_reader",
    "web_scraper",
    "web_search",
    "web_url_search",
    "generate_image",
    "generate_audio",
    "generate_transcription",
    "TOOLS",
    "console",
    "patch",
    "unpatch",
    "messages",
    "format_messages",
    "swap_system_prompt",
    "add_message",
    "repair_messages",
]

# imports

from .completions import (
    completion,
    acompletion,
    generate_code,
    function,
    generate_system_prompt,
    classify,
    aclassify,
    extract,
    aextract,
    validate,
    avalidate,
    generate_qa_pairs,
)

from ._lib import console

from .models import patch, unpatch

from .data import (
    text_reader,
    text_chunker,
    generate_embeddings,
    web_reader,
    web_scraper,
    web_search,
    web_url_search,
)

from .multimodal import generate_image, generate_audio, generate_transcription

from .tools import TOOLS

from .utils import (
    messages,
    add_message,
    format_messages,
    swap_system_prompt,
    repair_messages,
    convert_yaml_to_pydantic,
    convert_to_openai_tool,
)
