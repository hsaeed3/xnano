# completion chat model parameter type

from .chat_models import ChatModels
from typing import Union


# base param type
ChatModel = Union[
    str,
    ChatModels
]
