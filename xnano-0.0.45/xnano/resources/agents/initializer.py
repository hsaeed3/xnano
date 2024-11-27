# agent initializer method

from . import helpers
# - types-------------------------------------------------------
from ...types.completions.params import (
    CompletionMessagesParam,
    CompletionChatModelsParam,
    CompletionInstructorModeParam,
    CompletionToolsParam,
)
from ...types.embeddings.memory import Memory

from .agent import Agent

from typing import Optional, List, Union
from pydantic import BaseModel


def create_agent(
    role : str = "Assistant",
    # optional
    name : Optional[str] = helpers.get_random_name(),
    instructions : Optional[str] = None,
    planning : Optional[bool] = False,
    workflows : Optional[List[BaseModel]] = None,
    summarization_steps : Optional[int] = 5,
    agents: Optional[List['Agent']] = None,
    tools: Optional[List[CompletionToolsParam]] = None,
    # agent memory -- utilized differently than .completion(memory = ...)
    memory : Optional[List[Memory]] = None,
    # agent completion config params
    model : Union[CompletionChatModelsParam, str] = "openai/gpt-4o-mini",
    instructor_mode : Optional[CompletionInstructorModeParam] = None,
    base_url : Optional[str] = None,
    api_key : Optional[str] = None,
    organization : Optional[str] = None,
    messages : Optional[CompletionMessagesParam] = None,
    verbose : bool = False,
) -> Agent:
    """
    Initializes an agent with the given parameters.

    Example:
        ```python
        import xnano as x

        agent = x.create_agent(role="user", name="my_agent")
        ```

        or

        ```python
        agent = x.create_agent(
            role="user",
            name="my_agent",
            instructions="You are a helpful assistant",
            planning=True,
        )
        ```

    Args:
        role (str): The role of the agent.
        name (Optional[str]): The name of the agent.
        instructions (Optional[str]): The instructions for the agent.
        planning (Optional[bool]): Whether the agent should plan its actions.
        workflows (Optional[List[BaseModel]]): A list of pydantic models to use as workflows.
        summarization_steps (Optional[int]): The number of steps to use for summarization.
        memory (Optional[List[Memory]]): A list of memories to use for the agent.
        model (Union[CompletionChatModelsParam, str]): The model to use for the agent.
        instructor_mode (Optional[CompletionInstructorModeParam]): The instructor mode to use for the agent.
        base_url (Optional[str]): The base URL for the agent.
        api_key (Optional[str]): The API key for the agent.
        organization (Optional[str]): The organization for the agent.
        messages (Optional[CompletionMessagesParam]): The messages for the agent.
        verbose (bool): Whether to print verbose output.
        agents (Optional[List[Agent]]): A list of agents to collaborate with.
    """
    return Agent(
        role=role,
        name=name,
        instructions=instructions,
        planning=planning,
        workflows=workflows,
        summarization_steps=summarization_steps,
        memory=memory,
        model=model,
        instructor_mode=instructor_mode,
        base_url=base_url,
        api_key=api_key,
        organization=organization,
        messages=messages,
        tools=tools,
        verbose=verbose,
        agents=agents,
    )
