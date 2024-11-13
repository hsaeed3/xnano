from .chat_models import ChatModels
from .context import Context
from .instructor import InstructorMode
from .messages import Message
from .response_models import ResponseModel
from .tools import ToolType, ToolChoice
from ._openai import (
    ChatCompletionAudioParam,
    ChatCompletionModality,
    ChatCompletionPredictionContentParam,
)

from typing import List, Optional, Union


# -------------------------------------------------------------------------------------------------
# chat models param
# -------------------------------------------------------------------------------------------------
CompletionChatModelsParam = Union[str, ChatModels]


# -------------------------------------------------------------------------------------------------
# completion messages param
# -------------------------------------------------------------------------------------------------
CompletionMessagesParam = Union[str, Message, List[Message], List[List[Message]]]


# -------------------------------------------------------------------------------------------------
# completion context param
# -------------------------------------------------------------------------------------------------
CompletionContextParam = Optional[Context]


# -------------------------------------------------------------------------------------------------
# instructor generation mode param
# -------------------------------------------------------------------------------------------------
CompletionInstructorModeParam = Optional[InstructorMode]


# -------------------------------------------------------------------------------------------------
# completion response model param
# -------------------------------------------------------------------------------------------------
CompletionResponseModelParam = Optional[ResponseModel]


# -------------------------------------------------------------------------------------------------
# completion tools param
# -------------------------------------------------------------------------------------------------
CompletionToolsParam = Optional[List[ToolType]]


# -------------------------------------------------------------------------------------------------
# completion tool choice param
# -------------------------------------------------------------------------------------------------
CompletionToolChoiceParam = Optional[ToolChoice]


# -------------------------------------------------------------------------------------------------
# openai converted params
# -------------------------------------------------------------------------------------------------
CompletionAudioParam = Optional[ChatCompletionAudioParam]
CompletionModalityParam = Optional[ChatCompletionModality]
CompletionPredictionContentParam = Optional[ChatCompletionPredictionContentParam]
