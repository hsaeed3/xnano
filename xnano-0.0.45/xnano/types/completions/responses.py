# response
from pydantic import BaseModel
from typing import Union, Type, List
from ._openai import ChatCompletion
from ..models.mixin import BaseModelMixin

# response
Response = Union[
    # standard completion
    ChatCompletion,
    List[ChatCompletion],
    BaseModelMixin,
    List[BaseModelMixin],
    # simple types
    str,
    list[str],
    int,
    float,
    bool,
    list[int],
    list[float],
    list[bool],
    list,
]
