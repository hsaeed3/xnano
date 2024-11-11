# message parameter type

from .message import Message
from typing import Union, List


# base param type
MessageType = Union[
    str,
    Message,
    List[Message],
    List[List[Message]]
]