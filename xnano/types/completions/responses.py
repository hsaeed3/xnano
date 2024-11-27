# response
from pydantic import BaseModel
from typing import Union, Type, List, Generator
from ._openai import ChatCompletion, Stream, ChatCompletionChunk, AsyncStream
from ..models.mixin import BaseModelMixin


StreamingResponse = Stream[ChatCompletionChunk]


AsyncStreamingResponse = AsyncStream[ChatCompletionChunk]


# response
Response = Union[
    # standard completion
    ChatCompletion,
    BaseModelMixin,
]
