# Agent State Resource

from ....lib import console, XNANOException

from ....types.agents.agent_properties import AgentProperties
from ....types.agents.agent_state import AgentState

from ...utils.messages import verify_messages_integrity, swap_system_prompt


class AgentStateResource:

    """Manages the state of an agent"""

    def __init__(
            self,
            state : AgentState,
            properties : AgentProperties,
            verbose : bool = False
    ):

        self.verbose = verbose

        self._send_console_message(properties, f"Initialized with {len(state.current_messages)} previous messages")


    def _send_console_message(self, properties : AgentProperties, message : str):

        if self.verbose:
            console.message(
                f"[bold red]{properties.name} [dim]({properties.role})[/dim][/bold red] | [bold dark_cyan]State[/bold dark_cyan] - [dim]{message}[/dim]"
            )