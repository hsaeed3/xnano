# Generation Resource for Agents

from ....lib import console, XNANOException
from ....types.agents.agent_properties import AgentProperties
from ....types.agents.agent_completion_request import AgentCompletionRequest
from ....types.agents.agent_state import AgentState

from ...completions.main import completion


class AgentGenerationResource:

    """Creates completions for agents"""

    def __init__(
            self,
            properties : AgentProperties,
            verbose : bool = False
    ):

        self.properties = properties
        self.verbose = verbose

        self._send_console_message("Initialized")


    def _send_console_message(self, message : str):

        if self.verbose:
            console.message(f"[bold red]{self.properties.name} [dim]({self.properties.role})[/dim][/bold red] | [bold plum3]Generations[/bold plum3] - [dim]{message}[/dim]")


    def return_stream(self, properties : AgentProperties, request : AgentCompletionRequest):

        try:

            return completion(
                messages = request.messages,
                model = request.model,
                temperature = request.temperature,
                max_tokens = request.max_tokens,
                top_p = request.top_p,
                frequency_penalty = request.frequency_penalty,
                presence_penalty = request.presence_penalty,
                tools = request.tools,
                tool_choice = request.tool_choice,
                parallel_tool_calls = request.parallel_tool_calls,
                base_url = request.base_url,
                api_key = request.api_key,
                organization = request.organization,
                instructor_mode = request.instructor_mode,
                response_model = request.response_model,
            )
        
        except Exception as e:
            raise XNANOException(f"Error generating completion for {properties.name}, using model {request.model}: {e}")


    def get_completion_response(self, properties : AgentProperties, request : AgentCompletionRequest):

        try:

            return completion(
                messages = request.messages,
                model = request.model,
                temperature = request.temperature,
                max_tokens = request.max_tokens,
                top_p = request.top_p,
                frequency_penalty = request.frequency_penalty,
                presence_penalty = request.presence_penalty,
                tools = request.tools,
                tool_choice = request.tool_choice,
                parallel_tool_calls = request.parallel_tool_calls,
                base_url = request.base_url,
                api_key = request.api_key,
                organization = request.organization,
                instructor_mode = request.instructor_mode,
                response_model = request.response_model,
                run_tools = request.run_tools,
                return_messages = request.return_messages
            )
        
        except Exception as e:
            raise XNANOException(f"Error generating completion for {properties.name}, using model {request.model}: {e}")



