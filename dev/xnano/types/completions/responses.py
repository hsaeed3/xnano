# completion response

from pydantic import BaseModel
from typing import Union, Type, List
from ..openai import ChatCompletion

# response
Response = Union[
    # standard completion
    ChatCompletion, List[ChatCompletion],
    # all structured output formats
    Type[BaseModel], List[Type[BaseModel]],
    str, list[str], int , float, bool, list[int], list[float], list[bool], list
]