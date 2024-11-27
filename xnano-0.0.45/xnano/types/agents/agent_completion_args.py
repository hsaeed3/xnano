# Agent Completion Args

from pydantic import BaseModel
from typing import Optional, Dict, List, Union, Any


class AgentCompletionArgs(BaseModel):

    class Config:
        arbitrary_types_allowed = True

    messages : Optional[Union[List, Dict, str]] = None

    model : Optional[str] = None

    api_key : Optional[str] = None

    organization : Optional[str] = None

    base_url : Optional[str] = None


    agents : Optional[Union[List[Any], Any]] = None

    tools : Optional[List[Any]] = None

    instructor_mode : Optional[str] = None

    response_model : Optional[Any] = None

    tool_choice : Optional[str] = None

    parallel_tool_calls : Optional[bool] = None


    