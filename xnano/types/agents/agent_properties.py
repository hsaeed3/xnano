# Agent Properties

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Union


class AgentProperties(BaseModel):

    """
    Global Agent Properties
    

    All agents in the xnano framework will run off one instance of these properties.
    The resource handlers do not initialize their own properties/configurations; just
    modify the instance of these properties.
    """

    # dsl

    name : str = Field(description = "The name of the agent")
    role : str = Field(description = "The role of the agent")
    instructions : Optional[str] = Field(description = "The instructions of the agent")

    workflows : Optional[List] = Field(description = "The workflows of the agent")
    tools : Optional[List] = Field(description = "The tools of the agent")
    agents : Optional[List] = Field(description = "The helper/worker agents of the agent")

    # completion / llm params

    model : str = Field(description = "The model to use for the agent")
    base_url : Optional[str] = Field(description = "The base url to use for the agent")
    api_key : Optional[str] = Field(description = "The api key to use for the agent")
    organization : Optional[str] = Field(description = "The organization to use for the agent")
    temperature : Optional[float] = Field(description = "The temperature to use for the agent")
    max_tokens : Optional[int] = Field(description = "The max tokens to use for the agent")
    top_p : Optional[float] = Field(description = "The top p to use for the agent")
    frequency_penalty : Optional[float] = Field(description = "The frequency penalty to use for the agent")
    presence_penalty : Optional[float] = Field(description = "The presence penalty to use for the agent")
    tool_choice : Optional[str] = Field(description = "The tool choice to use for the agent")
    parallel_tool_calls : Optional[bool] = Field(description = "The parallel tool calls to use for the agent")

    instructor_mode : Optional[str] = Field(description = "The instructor mode to use for the agent")