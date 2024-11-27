from ...types.agents.agent_model import AgentModel
from ...types.agents.state import State
from ...types.agents.agent_response import AgentResponse
from ...types.completions.params import (
    CompletionMessagesParam,
    CompletionChatModelsParam,
    CompletionInstructorModeParam,
    CompletionResponseModelParam,
    CompletionToolChoiceParam,
    CompletionToolsParam,
)
from ...types.embeddings.memory import Memory
from .step import Steps

# - external ----------------------------------------------------
import json
from pydantic import BaseModel, create_model
from typing import Dict, List, Literal, Optional, Union, Type


Agent = Type["Agent"]
AgentResources = Type["AgentResources"]


class Agent:

    """
    base class for all agents in the xnano library.

    capabilities:
        - 'on-message' based - built to integrate both as a chatbot or an autogen style agent
        - multi-agent collaboration - ability to chat & collaborate on workflows with multiple agents
        - memory - uses xnano's vector store module for long term memory & summarization for short term memory
        - 'workflows' - use pydantic models like tools to create workflows with steps
        - 'steps' - like workflows but with much-much more fine-grained control over each step
    """

    state: State
    config: AgentModel
    resources: AgentResources

    def __init__(
            self,
            role : str = "assistant",
            name : Optional[str] = None,
            instructions : Optional[str] = None,
            planning : Optional[bool] = False,
            workflows : Optional[List[BaseModel]] = None,
            summarization_steps : Optional[int] = 5,
            memory : Optional[List[Memory]] = None,
            model : Union[CompletionChatModelsParam, str] = "openai/gpt-4o-mini",
            instructor_mode : Optional[CompletionInstructorModeParam] = None,
            base_url : Optional[str] = None,
            api_key : Optional[str] = None,
            organization : Optional[str] = None,
            messages : Optional[CompletionMessagesParam] = None,
            verbose : bool = False,
            agents : Optional[List[Agent]] = None,
    ) -> None:
        """
        Initializes an agent with the given parameters.

        Example:
            ```python
            agent = Agent(role="user", name="my_agent")
            ```

            or

            ```python
            agent = Agent(
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
        ...

    # ----------------------------------------------------------
    # - HELPERS
    # ----------------------------------------------------------

    def add_messages_to_state(
            self,
            messages : CompletionMessagesParam
    ) -> None:
        """
        Persists messages to the agent's internal state message thread

        Args:
            messages (CompletionMessagesParam): The messages to persist

        Returns:
            None
        """
        ...

    def get_messages_from_state(self) -> CompletionMessagesParam:
        """
        Retrieves messages from the agent's internal state message thread

        Example:
            ```python
            messages = agent.get_messages_from_state()
            ```

        Returns:
            CompletionMessagesParam: The messages from the agent's internal state message thread
        """
        ...

    def add_response_to_state(
            self,
            response : AgentResponse,
            instructor : bool = False,
    ) -> None:
        """
        Persists a response to the agent's internal state

        Example:
            ```python
            agent.add_response_to_state(response)
            ```

        Args:
            response (AgentResponse): The response to persist
            instructor (bool): Whether the response is an instructor response

        Returns:
            None
        """
        ...

    def get_system_prompt(
            self,
            tools : Optional[List[BaseModel]] = None,
    ) -> str:
        """
        Retrieves the system prompt for the agent

        Example:
            ```python
            system_prompt = agent.get_system_prompt()
            ```

        Args:
            tools (Optional[List[BaseModel]]): The tools to use for the system prompt

        Returns:
            str: The system prompt for the agent
        """
        ...

    # ----------------------------------------------------------
    # - SUMMARIZATION
    # ----------------------------------------------------------

    def build_summary(
            self,
            model : Optional[Union[CompletionChatModelsParam, str]] = None,
            api_key : Optional[str] = None,
            base_url : Optional[str] = None,
            organization : Optional[str] = None,
    ) -> str:
        """
        Builds a summary of the agent's internal state message thread &
        adds it to the summary thread.

        **Note**: This method will remove the original messages from the message thread.

        Args:
            model (Optional[Union[CompletionChatModelsParam, str]]): The model to use for the summary
            api_key (Optional[str]): The API key to use for the summary
            base_url (Optional[str]): The base URL to use for the summary
            organization (Optional[str]): The organization to use for the summary

        Returns:
            str: The summary of the agent's internal state message thread
        """
        ...

    # ----------------------------------------------------------
    # - WORKFLOWS
    # ----------------------------------------------------------

    def get_workflows(
            self,
            workflows : Optional[List[BaseModel]] = None,
    ) -> List[BaseModel]:
        """
        Retrieves the workflows for the agent, along with any additional
        workflows passed in as an argument.

        Args:
            workflows (Optional[List[BaseModel]]): The additional workflows to use

        Returns:
            List[BaseModel]: The workflows for the agent
        """
        ...

    def workflow(
        self,
        workflow: BaseModel,
        messages: Optional[CompletionMessagesParam] = None,
        agents: Optional[List[Agent]] = None,
        # completion specific params
        model: Optional[Union[CompletionChatModelsParam, str]] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        organization: Optional[str] = None,
        tools: Optional[CompletionToolsParam] = None,
        instructor_mode: Optional[CompletionInstructorModeParam] = None,
        response_model: Optional[CompletionResponseModelParam] = None,
        tool_choice: Optional[CompletionToolChoiceParam] = None,
        parallel_tool_calls: Optional[bool] = False,
    ) -> AgentResponse:
        """
        Executes a specified workflow directly, without running workflow selection pipeline.

        Example:
            ```python
            from pydantic import BaseModel, Field

            class MyWorkflow(BaseModel):
                write_code: str = Field(description="Write a web scraper in python")
                format_code : str

            response = agent.workflow(MyWorkflow)

            print(response.workflow)
            ```

        Args:
            workflow (BaseModel): The workflow to execute
            messages (Optional[CompletionMessagesParam]): The messages to use for the workflow
            agents (Optional[List[Agent]]): The agents to collaborate with
            model (Optional[Union[CompletionChatModelsParam, str]]): The model to use for the workflow
            base_url (Optional[str]): The base URL to use for the workflow
            api_key (Optional[str]): The API key to use for the workflow
            organization (Optional[str]): The organization to use for the workflow
            tools (Optional[CompletionToolsParam]): The tools to use for the workflow
            instructor_mode (Optional[CompletionInstructorModeParam]): The instructor mode to use for the workflow
            response_model (Optional[CompletionResponseModelParam]): The response model to use for the workflow
            tool_choice (Optional[CompletionToolChoiceParam]): The tool choice to use for the workflow
            parallel_tool_calls (Optional[bool]): Whether to use parallel tool calls for the workflow

        Returns:
            AgentResponse: The response from the workflow
        """
        ...

    # ----------------------------------------------------------
    # - COMPLETIONS
    # ----------------------------------------------------------
   
    def completion(
        self,
        messages : Optional[CompletionMessagesParam] = None,
        agents : Optional[List[Agent]] = None,
        workflows : Optional[List[BaseModel]] = None,
        # completion specific params
        model : Optional[Union[CompletionChatModelsParam, str]] = None,
        base_url : Optional[str] = None,
        api_key : Optional[str] = None,
        organization : Optional[str] = None,
        tools : Optional[CompletionToolsParam] = None,
        instructor_mode : Optional[CompletionInstructorModeParam] = None,
        response_model : Optional[CompletionResponseModelParam] = None,
        tool_choice : Optional[CompletionToolChoiceParam] = None,
        parallel_tool_calls : Optional[bool] = False,
    ) -> AgentResponse:
        """
        Runs an agent chat 'completion' & saves user inputs, workflows & assistant responses to the agent's internal state.

        ## Notes:

        ### Response Format:
        - The response will be in a standard chat completion format.
        - If a workflow is ran, the response will contain a `response.workflow` attribute that contains the results of the workflow.

        ### Workflows:
        - If an agent has been given workflows, it will use a workflow selection pipeline to determine which workflow to run.
        - If a workflow is selected, it will be fully executed before the completion response is returned.

        ### Tools:
        - Currently all python functions are automatically executed.
        - This framework encourages the use of generating pydantic models for the arguments of your tools, and executing them that way.
            - This provides the ability of querying for individual arguments, or even multiple tools at once.
            - This also gives the benefit of all arguments being properly typed & validated.

        ### Multi-Agent Collaboration
        - If multiple agents are given, or helper agents are defined at init level; it will run a multi-agent collaborative completion.
        - All agents will be given the opportunity to run, and will be allowed to see the entire message history at the time of their turn.
        - If nested agents have workflows, they will also run their workflow selection pipeline.

        # Examples:
            **Standard Completion:**
            ```python
            response = agent.completion(messages="Hello, how are you?")
            ```

            **Workflow Execution:**
            ```python
            response = agent.completion(workflow=MyWorkflow)
            ```

            **Multi-Agent Collaboration:**
            ```python
            response = agent.completion(agents=[agent1, agent2])
            ```

            **Getting Responses:**
            ```python
            # to print response content
            print(response.choices[0].message.content)

            # to get the workflow results
            print(response.workflow)
            ```

        Args:
            messages (Optional[CompletionMessagesParam]): The messages to use for the completion
            agents (Optional[List[Agent]]): The agents to collaborate with
            workflows (Optional[List[BaseModel]]): The workflows to execute
            model (Optional[Union[CompletionChatModelsParam, str]]): The model to use for the completion
            base_url (Optional[str]): The base URL to use for the completion
            api_key (Optional[str]): The API key to use for the completion
            organization (Optional[str]): The organization to use for the completion
            tools (Optional[CompletionToolsParam]): The tools to use for the completion
            instructor_mode (Optional[CompletionInstructorModeParam]): The instructor mode to use for the completion
            response_model (Optional[CompletionResponseModelParam]): The response model to use for the completion
            tool_choice (Optional[CompletionToolChoiceParam]): The tool choice to use for the completion
            parallel_tool_calls (Optional[bool]): Whether to use parallel tool calls for the completion

        Returns:
            AgentResponse: The response from the completion
        """
        ...

    def run_completion(
        self,
        messages: Optional[CompletionMessagesParam] = None,
        agents: Optional[List[Agent]] = None,
        # completion specific params
        model : Optional[Union[CompletionChatModelsParam, str]] = None,
        base_url : Optional[str] = None,
        api_key : Optional[str] = None,
        organization : Optional[str] = None,
        tools : Optional[CompletionToolsParam] = None,
        instructor_mode : Optional[CompletionInstructorModeParam] = None,
        response_model : Optional[CompletionResponseModelParam] = None,
        tool_choice : Optional[CompletionToolChoiceParam] = None,
        parallel_tool_calls : Optional[bool] = False,
        workflows : Optional[List[BaseModel]] = None
    ) -> AgentResponse:
        """
        Runs an agent chat 'completion'. Does not save to the agent's internal state.

        ## Notes:

        ### Response Format:
        - The response will be in a standard chat completion format.
        - If a workflow is ran, the response will contain a `response.workflow` attribute that contains the results of the workflow.

        ### Workflows:
        - If an agent has been given workflows, it will use a workflow selection pipeline to determine which workflow to run.
        - If a workflow is selected, it will be fully executed before the completion response is returned.

        ### Tools:
        - Currently all python functions are automatically executed.
        - This framework encourages the use of generating pydantic models for the arguments of your tools, and executing them that way.
            - This provides the ability of querying for individual arguments, or even multiple tools at once.
            - This also gives the benefit of all arguments being properly typed & validated.

        ### Multi-Agent Collaboration
        - If multiple agents are given, or helper agents are defined at init level; it will run a multi-agent collaborative completion.
        - All agents will be given the opportunity to run, and will be allowed to see the entire message history at the time of their turn.
        - If nested agents have workflows, they will also run their workflow selection pipeline.

        # Examples:
            **Standard Completion:**
            ```python
            response = agent.completion(messages="Hello, how are you?")
            ```

            **Workflow Execution:**
            ```python
            response = agent.completion(workflow=MyWorkflow)
            ```

            **Multi-Agent Collaboration:**
            ```python
            response = agent.completion(agents=[agent1, agent2])
            ```

            **Getting Responses:**
            ```python
            # to print response content
            print(response.choices[0].message.content)

            # to get the workflow results
            print(response.workflow)
            ```

        Args:
            messages (Optional[CompletionMessagesParam]): The messages to use for the completion
            agents (Optional[List[Agent]]): The agents to collaborate with
            workflows (Optional[List[BaseModel]]): The workflows to execute
            model (Optional[Union[CompletionChatModelsParam, str]]): The model to use for the completion
            base_url (Optional[str]): The base URL to use for the completion
            api_key (Optional[str]): The API key to use for the completion
            organization (Optional[str]): The organization to use for the completion
            tools (Optional[CompletionToolsParam]): The tools to use for the completion
            instructor_mode (Optional[CompletionInstructorModeParam]): The instructor mode to use for the completion
            response_model (Optional[CompletionResponseModelParam]): The response model to use for the completion
            tool_choice (Optional[CompletionToolChoiceParam]): The tool choice to use for the completion
            parallel_tool_calls (Optional[bool]): Whether to use parallel tool calls for the completion

        Returns:
            AgentResponse: The response from the completion
        """
        ...

    # ----------------------------------------------------------
    # - STEPS
    # ----------------------------------------------------------

    def steps(self) -> Steps:
        """
        Create a new step execution handler

        Example:
            ```python
            steps = agent.steps()

            @steps.step("collect_data")
            def collect_data(agent: Agent, state: StepState, input_data: Dict):
                response = agent.completion(
                    messages="Collect relevant data for analysis"
                )
                return {"data": response.choices[0].message.content}
            
            @steps.step("analyze_data", depends_on=["collect_data"])
            def analyze_data(agent: Agent, state: StepState, input_data: Dict):
                data = input_data["collect_data"]["data"]
                response = agent.completion(
                    messages=f"Analyze this data: {data}"
                )
                return {"analysis": response.choices[0].message.content}
            ```

        Args:
            None

        Returns:
            Steps: A new step execution handler
        """
        ...

    # ----------------------------------------------------------
    # - COLLABORATION
    # ----------------------------------------------------------

    def collaborate(
        self,
        messages: Optional[CompletionMessagesParam] = None,
        agents: Optional[List[Agent]] = None,
        max_steps: int = 5,
        # completion specific params
        model: Optional[Union[CompletionChatModelsParam, str]] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        organization: Optional[str] = None,
        tools: Optional[CompletionToolsParam] = None,
        instructor_mode: Optional[CompletionInstructorModeParam] = None,
        response_model: Optional[CompletionResponseModelParam] = None,
        tool_choice: Optional[CompletionToolChoiceParam] = None,
        parallel_tool_calls: Optional[bool] = False,
        workflows: Optional[List[BaseModel]] = None,
    ) -> AgentResponse:
        """
        Conducts a task-oriented conversation until completion or max steps reached.
        Maintains thread state and integrates with existing agent capabilities.

        Example:
            ```python
            response = agent.conversation(
                messages="Write a web scraper in python",
                agents=[agent1, agent2],
                max_steps=10,
            )
            ```

        Args:
            messages (Optional[CompletionMessagesParam]): The messages to use for the conversation
            agents (Optional[List[Agent]]): The agents to collaborate with
            max_steps (int): The maximum number of steps to run
            model (Optional[Union[CompletionChatModelsParam, str]]): The model to use for the conversation
            base_url (Optional[str]): The base URL to use for the conversation
            api_key (Optional[str]): The API key to use for the conversation
            organization (Optional[str]): The organization to use for the conversation
            tools (Optional[CompletionToolsParam]): The tools to use for the conversation
            instructor_mode (Optional[CompletionInstructorModeParam]): The instructor mode to use for the conversation
            response_model (Optional[CompletionResponseModelParam]): The response model to use for the conversation
            tool_choice (Optional[CompletionToolChoiceParam]): The tool choice to use for the conversation
            parallel_tool_calls (Optional[bool]): Whether to use parallel tool calls for the conversation
            workflows (Optional[List[BaseModel]]): The workflows to execute

        Returns:
            AgentResponse: The response from the conversation
        """
        ...

    def update_instructions(
        self,
        instructions: str
    ):
        """
        Updates the agent's instructions

        Example:
            ```python
            agent.update_instructions("You are a helpful assistant")
            ```

        Args:
            instructions (str): The new instructions for the agent

        Returns:
            None
        """
        ...

    def reset_state(self):
        """
        Resets the agent's internal state

        Example:
            ```python
            agent.reset_state()
            ```
        """
        ...

    def plan(
        self,
        messages: Optional[CompletionMessagesParam] = None,
        agents: Optional[List[Agent]] = None,
        model: Optional[Union[CompletionChatModelsParam, str]] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        organization: Optional[str] = None,
        tools: Optional[CompletionToolsParam] = None,
        instructor_mode: Optional[CompletionInstructorModeParam] = None,
        response_model: Optional[CompletionResponseModelParam] = None,
        tool_choice: Optional[CompletionToolChoiceParam] = None,
        parallel_tool_calls: Optional[bool] = False,
        workflows: Optional[List[BaseModel]] = None,
    ) -> List[AgentResponse]:
        """
        Generates a plan to accomplish the given task and executes it step by step.

        Args:
            messages (Optional[CompletionMessagesParam]): Initial messages or user request.
            agents (Optional[List[Agent]]): Other agents to collaborate with.
            model (Optional[Union[CompletionChatModelsParam, str]]): Model to use for completions.
            base_url (Optional[str]): Base URL for the API.
            api_key (Optional[str]): API key for authentication.
            organization (Optional[str]): Organization identifier.
            tools (Optional[CompletionToolsParam]): Tools available to the agent.
            instructor_mode (Optional[CompletionInstructorModeParam]): Instructor mode settings.
            response_model (Optional[CompletionResponseModelParam]): Expected response model.
            tool_choice (Optional[CompletionToolChoiceParam]): Tool choice parameters.
            parallel_tool_calls (Optional[bool]): Whether to run tool calls in parallel.
            workflows (Optional[List[BaseModel]]): Workflows available to the agent.

        Returns:
            List[AgentResponse]: The list of responses from executing each step.
        """
        ...