# completion response

from pydantic import BaseModel
from typing import Union, Type, List
from ..openai import ChatCompletion
from ..pydantic.base_model_mixin import BaseModelMixin

# response
Response = Union[
    # standard completion
    ChatCompletion, List[ChatCompletion],
    Type[BaseModelMixin], List[Type[BaseModelMixin]],
    # all structured output formats
    Type[BaseModel], List[Type[BaseModel]],
    str, list[str], int , float, bool, list[int], list[float], list[bool], list
]