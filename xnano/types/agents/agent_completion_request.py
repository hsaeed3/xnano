# Agent Completion Request

from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union, Type



class AgentCompletionRequest(BaseModel):

    """A request to generate a completion for an agent"""

    # Required Params
    messages : List[Dict[str, Any]] 
    model : str

    # dsl params
    agents : Optional[List] = None
    workflows : Optional[List] = None

    # Instructor Specific
    instructor_mode : Optional[str] = None
    response_model : Optional[Type[BaseModel]] = None

    # Tool Specific
    tools : Optional[List] = None
    run_tools : Optional[bool] = None
    return_messages : Optional[bool] = None

    # Optional
    base_url : Optional[str] = None
    api_key : Optional[str] = None
    organization : Optional[str] = None
    temperature : Optional[float] = None
    max_tokens : Optional[int] = None
    top_p : Optional[float] = None
    frequency_penalty : Optional[float] = None
    presence_penalty : Optional[float] = None
    tool_choice : Optional[str] = None
    parallel_tool_calls : Optional[bool] = None

