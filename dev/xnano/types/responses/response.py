# completion response

from pydantic import BaseModel
from openai.types.chat.chat_completion import ChatCompletion
from .response_model import ResponseModel
from typing import Union, Type, List
from ..basemodel.basemodel import BaseModel as BaseModelMixin

# response
Response = Union[
    # standard completion
    ChatCompletion, List[ChatCompletion],
    Type[ResponseModel], List[Type[ResponseModel]],
    Type[BaseModelMixin], List[Type[BaseModelMixin]],
    # all structured output formats
    Type[BaseModel], List[Type[BaseModel]],
    str, list[str], int , float, bool, list[int], list[float], list[bool], list
]