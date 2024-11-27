# Agent Prompting Resource

from ....lib import console, XNANOException

from ...completions.resources.tool_calling import convert_to_tool

from ....types.agents.agent_properties import AgentProperties
from ....types.agents.agent_completion_request import AgentCompletionRequest

from typing import Type


class AgentPromptingResource:

    """Manages system prompts & instructions for agent generations"""

    def __init__(
            self,
            properties : AgentProperties,
            verbose : bool = False
    ):
        
        self.verbose = verbose

        self._send_console_message(properties, "Initialized")


    def _send_console_message(self, properties : AgentProperties, message : str):

        if self.verbose:
            console.message(f"[bold red]{properties.name} [dim]({properties.role})[/dim][/bold red] | [bold tan]Prompt Manager[/bold tan] - [dim]{message}[/dim]")


    def get_tool_names_string(self, properties : AgentProperties, request : AgentCompletionRequest):

        tool_names = []
        tool_descriptions = []

        if request.tools:
            for tool in request.tools:
                if isinstance(tool, str):
                    tool_names.append(tool)
                else:
                    converted_tool = convert_to_tool(tool)
                    tool_names.append(converted_tool.name)
                    tool_descriptions.append(converted_tool.description)

        if properties.tools:
            for tool in properties.tools:
                if isinstance(tool, str):
                    tool_names.append(tool)
                else:
                    converted_tool = convert_to_tool(tool)
                    tool_names.append(converted_tool.name)
                    tool_descriptions.append(converted_tool.description)
        
        formatted_tools = []
        for i, name in enumerate(tool_names):
            if i < len(tool_descriptions):
                formatted_tools.append(f"{name} ({tool_descriptions[i]})")
            else:
                formatted_tools.append(name)
        return ", ".join(formatted_tools)
    

    def get_agents_string(self, properties : AgentProperties, request : AgentCompletionRequest):
        agents = []
        if request.agents:
            agents.extend(request.agents)

        if properties.agents:
            agents.extend(properties.agents)

        agent_string = ""

        if agents:
            agent_string = "You are working closely with the following team members: \n"

            for agent in agents:
                agent_string += f"- {agent.properties.name}, a {agent.properties.role} \n"

        return agent_string

    def get_workflows_string(self, properties : AgentProperties, request : AgentCompletionRequest):
        workflows = []

        if request.workflows:
            workflows.extend(request.workflows)

        if properties.workflows:
            workflows.extend(properties.workflows)

        workflows_string = ""

        if workflows:
            workflows_string = "You have the following workflows available to you: \n"

            for workflow in workflows:
                workflows_string += f"- {workflow.__class__.__name__}; {workflow.__class__.__doc__ if workflow.__class__.__doc__ else ''} \n"

        return workflows_string
    

    def get_base_instruction_string(self, properties : AgentProperties, request : AgentCompletionRequest):

        base_instruction = (
            f"You are {properties.name}, a world class {properties.role}.\n"
            "As a genius expert, you are able to respond to conversations/tasks & queries with the utmost accuracy and efficiency in relation to your capabilities."
        )

        return 
