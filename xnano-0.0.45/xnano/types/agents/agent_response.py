from litellm import ModelResponse
from pydantic import BaseModel
from typing import Optional


class AgentResponse(ModelResponse):

    workflow : Optional[BaseModel] = None
