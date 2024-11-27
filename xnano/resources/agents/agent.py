# Xnano Agents

# The Agent class is the base and only import you will need to 
# build any workflow/configuration off of this framework.

# -----------------------------------------------------------------

from ...types.agents.agent_properties import AgentProperties
from ...types.agents.agent_state import AgentState

from ...types.embeddings.memory import Memory
from ...types.completions.params import (
    CompletionMessagesParam,
    CompletionAudioParam,
    CompletionChatModelsParam,
    CompletionContextParam,
    CompletionInstructorModeParam,
    CompletionResponseModelParam,
    CompletionModalityParam,
    CompletionPredictionContentParam,
    CompletionToolChoiceParam,
    CompletionToolsParam,
)
from typing import Optional, List, Dict, Union, Type, Any

from ...lib import console, XNANOException
from .helpers import get_random_name
from pydantic import BaseModel

from .resources.agent_generation_resource import AgentGenerationResource
from .resources.agent_prompting_resource import AgentPromptingResource
from .resources.agent_state_resource import AgentStateResource

# -----------------------------------------------------------------

# Typing
Agent = Type['Agent']

# -----------------------------------------------------------------


class Agent:


    """Base Agent Class for xnano agents"""


    def __init__(
            self,
            # dsl
            name : str = get_random_name(),
            role : str = "Assistant",
            instructions : Optional[str] = None,
            workflows : Optional[List[BaseModel]] = None,
            tools : Optional[CompletionToolsParam] = None,
            agents : Optional[List[Agent]] = None,

            # completion / llm params
            model : str = "gpt-4o-mini",
            base_url : Optional[str] = None,
            api_key : Optional[str] = None,
            organization : Optional[str] = None,
            temperature : Optional[float] = None,
            max_tokens : Optional[int] = None,
            top_p : Optional[float] = None,
            frequency_penalty : Optional[float] = None,
            presence_penalty : Optional[float] = None,
            tool_choice : Optional[CompletionToolChoiceParam] = None,
            parallel_tool_calls : Optional[bool] = None,

            # preset list of messages
            messages : Optional[List[Dict[str, Any]]] = None,

            # instructor
            instructor_mode : Optional[CompletionInstructorModeParam] = None,

            # verbosity
            verbose : Optional[bool] = False,
    ):
        
        # verbosity
        self.verbose = verbose
        
        # initialize properties
        self.properties = AgentProperties(
            name = name,
            role = role,
            instructions = instructions,
            workflows = workflows,
            tools = tools,
            agents = agents,

            # completion / llm params
            model = model,
            base_url = base_url,
            api_key = api_key,
            organization = organization,
            temperature = temperature,
            max_tokens = max_tokens,
            top_p = top_p,
            frequency_penalty = frequency_penalty,
            presence_penalty = presence_penalty,
            tool_choice = tool_choice,
            parallel_tool_calls = parallel_tool_calls,

            instructor_mode = instructor_mode,
        )

        # initialize state
        self.state = AgentState(
            current_messages = messages if messages else [],
            summary_messages = [],
            current_message_count = 0
        )

        self._initialize_resources()


    def _initialize_resources(self):

        # State & Message Thread Management
        self.state_resource = AgentStateResource(
            state = self.state,
            properties = self.properties,
            verbose = self.verbose
        )

        # Completions & Generation Resource
        self.generation_resource = AgentGenerationResource(
            properties = self.properties,
            verbose = self.verbose
        )

        # Prompting Resource
        self.prompting_resource = AgentPromptingResource(
            properties = self.properties,
            verbose = self.verbose
        )

# -----------------------------------------------------------------
# Completion Methods
# -----------------------------------------------------------------


    def _run_chat_completion(
            self,
            messages : CompletionMessagesParam,

            response_model : Optional[Type[BaseModel]] = None,
            tools : Optional[CompletionToolsParam] = None,
            run_tools : Optional[bool] = None,
            return_messages : Optional[bool] = None,

            model : Union[str, CompletionChatModelsParam] = "openai/gpt-4o-mini",
            base_url : Optional[str] = None,
            api_key : Optional[str] = None,
            organization : Optional[str] = None,
            temperature : Optional[float] = None,
            max_tokens : Optional[int] = None,
            top_p : Optional[float] = None,
            frequency_penalty : Optional[float] = None,
            presence_penalty : Optional[float] = None,
            tool_choice : Optional[CompletionToolChoiceParam] = None,
            parallel_tool_calls : Optional[bool] = None,
            instructor_mode : Optional[CompletionInstructorModeParam] = None,
    ):
        
        pass
        

