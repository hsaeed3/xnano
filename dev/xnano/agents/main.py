# main
# agents

from ..completions import completion
from ..types._openai import ChatCompletionModality, ChatCompletionPredictionContentParam, ChatCompletionAudioParam
from ..types.completions.completions_arguments import CompletionsArguments
from ..types.context.context import Context
from ..types.chat_models.chat_model import ChatModel
from ..types.instructor.instructor_mode import InstructorMode
from ..types.messages.message_type import MessageType
from ..types.responses.response import Response
from ..types.responses.response_model_type import ResponseModelType
from ..types.tools.tool_choice import ToolChoice
from ..types.tools.tool_type import ToolType

from pydantic import BaseModel


class Agent(BaseModel):

    # for it's internal messages


class Agents:

    def __init__(
            self,
            verbose : bool = False
    ):
        
        self.verbose = verbose