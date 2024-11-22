# xnano.resources.agents.agent
# base agent client for xnano

# important resources
# xnano.resources.agents.helpers
    # - base helpers
# xnano.resources.agents.completions
    # - completion handlers
# xnano.resources.agents.messages
    # - message & thread handling
# xnano.resources.agents.workflows
    # - workflow handling
# xnano.resources.agents.planning
    # - chain of thought & planning handler
# xnano.resources.agents.memory
    # - summarization & memory creation / vector embedding handling

# - imports ----------------------------------------------------
from ..._lib import console, XNANOException
from . import helpers
from ..utils import messages as messages_utils
from ..completions.main import completion, acompletion
from ..completions.resources.tool_calling import convert_to_tool
from .step import Steps
# - types-------------------------------------------------------
from ...types.agents.agent_model import AgentModel
from ...types.agents.agent_completion_args import AgentCompletionArgs
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
from litellm import ModelResponse
from ...types.completions.responses import Response
from ...types.embeddings.memory import Memory

# - external ----------------------------------------------------
import json
from pydantic import BaseModel, create_model
from typing import Dict, List, Literal, Optional, Union, Type


Agent = Type["Agent"]


# --------------------------------------------------------------
# RESOURCES
# --------------------------------------------------------------

class AgentResources:

    convert_to_tool = convert_to_tool
    messages = messages_utils
    helpers = helpers

    """
    Agent Helper Resources
    """

    # - // messages

    @staticmethod
    def collect_message_from_cli():
        try:
            message = console.input(
                message = f"[bold italic] Enter your message:[/bold italic] [bold red]>>[/bold red]"
            )
        except KeyboardInterrupt:
            return XNANOException(
                message = "Keyboard Interrupt.. Try entering a message again"
            )
        
        return [{"role" : "user", "content" : message}]
        
    @staticmethod
    def format_new_messages(
        messages : CompletionMessagesParam
    ) -> List[Dict]:
        
        if isinstance(messages, str):
            messages = [{"role" : "user", "content" : messages}]
        
        if isinstance(messages, Dict):
            messages = [messages]

        try:
            messages = AgentResources.messages.verify_messages_integrity(
                messages = messages
            )
        except Exception as e:
            raise XNANOException(
                message = f"Error formatting new messages: {e}"
            )
        
        return messages

    # - // responses

    @staticmethod
    def build_response_type(
        response : Response,
        workflow : Optional[BaseModel] = None,
        instructor : bool = False
    ):
        """
        Types response
        """

        if not instructor:
            return AgentResponse(
                workflow = workflow,
                **response.model_dump()
            )
        else:
            return response

    # - // tools

    @staticmethod
    def get_tool_names(
        tools : Optional[CompletionToolsParam] = None,
    ):
        
        tool_names = []

        if not tools:
            return None

        try:
            for tool in tools:
                if isinstance(tool, str):
                    tool_names.append(tool)
                else:
                    tool = AgentResources.convert_to_tool(tool)
                    tool_names.append(tool.name)
        except Exception as e:
            raise XNANOException(
                message = f"Error getting tool names: {e}"
            )

        return tool_names

    # - // workflows

    @staticmethod
    def build_empty_workflow_model(
        workflow : BaseModel
    ) -> BaseModel:
        try:
            workflow_empty_model = create_model(
                workflow.__class__.__name__,
                **{name: (Optional[field.annotation], None) for name, field in workflow.model_fields.items()}
            )

            return workflow_empty_model()
        except Exception as e:
            raise XNANOException(
                message = f"Error building empty workflow model: {e}"
            )

    @staticmethod
    def build_all_workflow_string_descriptions(
        workflows : Optional[List[BaseModel]] = None
    ) -> str:
        
        if not workflows:
            return ""
        
        try:
            workflow_names = []
            workflow_docs = []
            if workflows:
                workflow_names = [workflow.model_json_schema()["title"] for workflow in workflows]
                workflow_docs = [workflow.model_json_schema()["description"] for workflow in workflows]

        except Exception as e:
            raise XNANOException(f"Error building workflow string descriptions: {e}")
        
        workflow_string = "\n".join([f"{name}: {doc if doc else ''}" for name, doc in zip(workflow_names, workflow_docs)])

        return workflow_string

# --------------------------------------------------------------
# AGENT CLASS 
# --------------------------------------------------------------

class Agent:

    """
    Base agent class for all agentic workflows/completions & multi
    agent pipelines
    """

    # base level resources
    resources = AgentResources

    def __init__(
            self,
            # agent dsl params
            # required
            role : str,
            # optional
            name : Optional[str] = helpers.get_random_name(),
            instructions : Optional[str] = None,
            planning : Optional[bool] = False,
            workflows : Optional[List[BaseModel]] = None,
            summarization_steps : Optional[int] = 5,
            agents: Optional[List['Agent']] = None,
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
    ):
        
        # VERBOSITY
        # cli outputs for debugging and progress
        self.verbose = verbose

        # STATE
        # handles message and summarization states
        self.state = State(
            messages = messages if messages else [],
            summary_thread = [],
            count = 0
        )

        # AGENT CONFIG
        self.config = AgentModel(
            role = role, name = name, instructions = instructions,
            workflows = workflows,
            summarization_steps = summarization_steps,
            planning = planning,
            model = model, base_url = base_url, api_key = api_key,
            organization = organization,
            instructor_mode = instructor_mode,
            agents = agents
        )

        if self.verbose and agents:
            console.message(
                f"Initialized with [bold gold1]{len(agents)}[/bold gold1] team agents"
            )

        if self.verbose:
            console.message(
                f"New [bold gold1]agent[/bold gold1], [bold red]{name}[/bold red] initialized with role: [bold sky_blue1]{role}[/bold sky_blue1]"
            )

        # ----------------------------------------------------------
    
    # ----------------------------------------------------------
    # STEPS
    # ----------------------------------------------------------

    def steps(self) -> Steps:
        """Create a new step execution handler"""
        return Steps(self, verbose=self.verbose)

    # ----------------------------------------------------------
    # - internal helper methods
    # ----------------------------------------------------------

    def _get_tools(
            self,
            tools : Optional[CompletionToolsParam] = None
    ):
        if tools:
            if self.config.tools:
                return self.config.tools + tools
            else:
                return tools
        else:
            if self.config.tools:
                return self.config.tools
            else:
                return None

    # ----------------------------------------------------------
    # - public helper methods
    # ----------------------------------------------------------

    # - // messages // state

    def add_messages_to_state(
            self,
            messages : CompletionMessagesParam
    ):
        try:
            self.state.messages.extend(messages)

            if self.verbose:
                console.message(
                    f"Added [bold gold1]{len(messages)}[/bold gold1] messages to state"
                )
        except Exception as e:
            raise XNANOException(
                message = f"Error adding messages to state: {e}"
            )

    def get_messages_from_state(
            self
    ):
        try:
            return self.state.summary_thread + self.state.messages
        except Exception as e:
            raise XNANOException(
                message = f"Error getting messages from state: {e}"
            )
        
    def add_response_to_state(
            self,
            response : AgentResponse,
            instructor : bool = False,
    ):
        
        if instructor:
            self.state.messages.append(
                {
                    "role" : "assistant",
                    "content" : response.model_dump_json(indent = 2)
                }
            )
            if self.verbose:
                console.message(f"Added [bold sky_blue1]Instructor[/bold sky_blue1] response to state thread for [bold red]{self.config.name}[/bold red]")

            return
        
        if isinstance(response, ModelResponse) and not hasattr(response, 'workflow'):
            self.state.messages.append(response.choices[0].message.model_dump())
            return
        
        if response.workflow is not None:
            self.state.messages.extend(
                [
                    {
                        "role" : "assistant",
                        "content" : (
                            "I have constructed the following object, now usable for reference"
                            f"\n\n{response.workflow.model_dump_json(indent = 2)}"
                            )
                    },
                    {
                        "role" : "user",
                        "content" : (
                            "Use the object to continue your response."
                        )
                    }
                ]
            )
            if self.verbose:
                console.message(f"Added [bold sky_blue1]Workflow[/bold sky_blue1] to state thread for [bold red]{self.config.name}[/bold red]")
        else:
            self.state.messages.append(response.choices[0].message.model_dump())

            if self.verbose:
                console.message(f"Added [bold sky_blue1]Completion[/bold sky_blue1] response to state thread for [bold red]{self.config.name}[/bold red]")

        return

    # - // instruction (system prompt)

    def get_system_prompt(
            self,
            tools : Optional[CompletionToolsParam] = None
    ) -> Dict:
        tool_names = AgentResources.get_tool_names(tools)

        instruction_prompt = self.resources.helpers.build_instruction(
            name = self.config.name, role = self.config.role,
            tool_names = tool_names, instructions = self.config.instructions
        )

        if self.verbose:
            console.message(f"Built instruction system prompt for [bold red]{self.config.name}[/bold red]")

        return instruction_prompt

    # - // summarization

    def build_summary(
            self,
            model : Optional[Union[CompletionChatModelsParam, str]] = None,
            api_key : Optional[str] = None,
            base_url : Optional[str] = None,
            organization : Optional[str] = None
    ):
        messages = self.state.messages

        try:
            summary = completion(
                messages = [
                    {"role" : "system", "content" : (
                            "You are a Pulitzer Prize winning journalist. You are tasked with summarizing the following conversation into a concise and informative summary.\n\n"
                            "## INSTRUCTIONS\n"
                            "- Read through the entire given conversation\n"
                            "- Identify the key points, themes and main ideas\n"
                            "- Generate a summary in a detailed list based format\n"
                            "- DO NOT INCLUDE AN INTRODUCTION OR TITLE TO THE SUMMARY\n\n"
                            "## CONVERSATION:"
                        )
                    },
                    {
                        "role" : "user",
                        "content" : json.dumps(messages)
                    }
                ],
                model = self.config.model if not model else model, api_key = self.config.api_key if not api_key else api_key, base_url = self.config.base_url if not base_url else base_url,
                organization = self.config.organization if not organization else organization,
                verbose = self.verbose
            )
        except Exception as e:
            raise XNANOException(
                message = f"Error building summary: {e}"
            )
        
        self.state.summary_thread.append(
            {"role" : "user", "content" : (
                    "The conversation proceeded as follows:\n\n"
                    f"{json.dumps(summary.choices[0].message.content)}"
                )
            }
        )

        self.state.messages = []
        self.state.count = 0

        return summary.choices[0].message.content

    # - // completion handler 

    def _build_completion_request(
            self,
            # required
            messages : CompletionMessagesParam,
            # optional
            # agent dsl params
            agents : Optional[List[Agent]] = None,
            # completion specific params
            model : Optional[Union[CompletionChatModelsParam, str]] = None,
            base_url : Optional[str] = None,
            api_key : Optional[str] = None,
            organization : Optional[str] = None,
            tools : Optional[CompletionToolsParam] = None,
            instructor_mode : Optional[CompletionInstructorModeParam] = None,
            response_model : Optional[CompletionResponseModelParam] = None,
            tool_choice : Optional[CompletionToolChoiceParam] = None,
            parallel_tool_calls : Optional[bool] = False
    ) -> AgentCompletionArgs:
        
        # add internal state messages to completion messages if applicable
        internal_messages = self.get_messages_from_state()

        if self.verbose:
            console.message(f"Found [bold gold1]{len(internal_messages)}[/bold gold1] internal messages")

        if len(internal_messages) > 0:
            messages = internal_messages + messages

        if tools:
            if self.config.tools:
                tools = self.config.tools + tools
        else:
            if self.config.tools:
                tools = self.config.tools

        # build instruction
        instruction_prompt = self.get_system_prompt(tools)

        messages = self.resources.messages.swap_system_prompt(
            messages = messages, system_prompt = instruction_prompt
        )

        args = AgentCompletionArgs(
            messages = messages,
            agents = agents,
            model = model if model else self.config.model,
            base_url = base_url if base_url else self.config.base_url,
            api_key = api_key if api_key else self.config.api_key,
            organization = organization if organization else self.config.organization,
            tools = tools,
            instructor_mode = instructor_mode if instructor_mode else self.config.instructor_mode,
            response_model = response_model,
            tool_choice = tool_choice,
            parallel_tool_calls = parallel_tool_calls
        )

        if self.verbose:
            console.message(f"Built completion request for [bold red]{self.config.name}[/bold red]")

        return args
    
    def _run_completion(
            self,
            args : AgentCompletionArgs,
            response_model : Optional[CompletionResponseModelParam] = None
    ):
        
        if self.verbose:
            console.message(f"Running completion for [bold red]{self.config.name}[/bold red], with [bold gold1]{len(args.messages)}[/bold gold1] messages")

        try:
            return completion(
                messages = args.messages,
                model = args.model,
                base_url = args.base_url,
                api_key = args.api_key,
                organization = args.organization,
                tools = args.tools,
                mode = args.instructor_mode,
                response_model = response_model if response_model else args.response_model,
                tool_choice = args.tool_choice,
                parallel_tool_calls = args.parallel_tool_calls,
                context = "You have access to the following workflows: \n\n" + self.resources.build_all_workflow_string_descriptions(
                    workflows = self.config.workflows
                ) + "\n Do not hallucinate or make up tools that are not listed.",
                run_tools = True
            )
        except Exception as e:
            raise XNANOException(
                message = f"Error running completion: {e}"
            )
    
    # ----------------------------------------------------------
    # - workflows
    # ----------------------------------------------------------

    def get_workflows(
            self,
            workflows : Optional[List[BaseModel]] = None
    ):
        if not workflows:
            return self.config.workflows or []
        if not self.config.workflows:
            return workflows
        return self.config.workflows + workflows

    def _determine_if_workflow_required(
            self,
            args : AgentCompletionArgs,
            workflows : Optional[List[BaseModel]] = None
    ) -> bool:
        
        workflows = self.get_workflows(workflows)

        if len(workflows) == 0:
            return False
        
        workflow_string = self.resources.build_all_workflow_string_descriptions(
            workflows = workflows
        )

        class WorkflowRequired(BaseModel):
            required : bool

        messages = [
            {"role" : "system", "content" : (
                    "You are a world class tool selector. Given a list of tools, you must accurately determine whether or not the current point of the conversation requires the use of a tool.\n\n"
                    f"## TOOLS\n{workflow_string}\n\n"
                )
            },
            *args.messages
        ]

        try:
            required = completion(
                messages = messages,
                model = args.model, api_key = args.api_key, base_url = args.base_url,
                mode = args.instructor_mode, response_model = WorkflowRequired,
                verbose = self.verbose
            )
        except Exception as e:
            raise XNANOException(
                message = f"Error determining if workflow is required: {e}"
            )

        return required.required

    def _select_workflow_to_run(
            self,
            args : AgentCompletionArgs,
            workflows : Optional[List[BaseModel]] = None
    ):
        
        # get workflows
        workflows = self.get_workflows(workflows)

        # build workflow string
        workflow_string = self.resources.build_all_workflow_string_descriptions(
            workflows = workflows
        )

        workflow_names = [workflow.model_json_schema()["title"] for workflow in workflows]

        # build workflow selection model
        Selection = create_model(
            'Selection',
            tool=(Literal[tuple(workflow_names)], ...)
        )

        messages = [
            {
                "role" : "system",
                "content" : (
                    "You are a world class tool selector. Given a list of tools, you must accurately determine which tool to use.\n\n"
                    f"## TOOLS\n{workflow_string}\n\n"
                )
            },
            *args.messages,
            {
                "role" : "user",
                "content" : "Do we need to run a tool to continue?"
            },
            {
                "role" : "assistant",
                "content" : "I've determined that a tool is required to continue."
            },
            {
                "role" : "user",
                "content" : "Please select the most appropriate tool to use."
            }
        ]

        selection = completion(
            messages = messages,
            model = args.model, api_key = args.api_key, base_url = args.base_url,
            mode = args.instructor_mode, response_model = Selection,
            verbose = self.verbose
        )

        selected_workflow = selection.tool

        for workflow in workflows:
            if workflow.model_json_schema()["title"] == selected_workflow:

                if self.verbose:
                    console.message(f"Selected workflow: [bold red]{workflow.__class__.__name__}[/bold red]")

                return workflow

        raise XNANOException(f"Selected workflow '{selected_workflow}' not found in workflow list")
    
    def _execute_workflow(
            self,
            workflow : BaseModel,
            args : AgentCompletionArgs
    ):
        
        completed_workflow = {}

        if self.verbose:
            console.message(f"Executing workflow: [bold red]{workflow.model_json_schema()['title']}[/bold red]")

        # Split Model into List of Field Types
        field_types = [field.annotation for field in workflow.model_fields.values()]

        # Get Workflow Name and Description
        workflow_name = workflow.model_json_schema()["title"]
        workflow_description = workflow.model_json_schema()["description"]

        # Build Workflow Schema
        workflow_schema = "\n".join(
            str(field_type) 
            for field_type in field_types
        )

        system_prompt = (
            f"You are a now working as a world class object constructor specializing in tasks including {workflow_description}. You are currently building {workflow_name}.\n"
            f"{workflow_name} is defined as follows:\n"
            f"{workflow_schema}\n\n"
            "Use your knowledge and skills to construct the object accurately and efficiently."
        )

        messages = args.messages.copy()

        # get instruction
        instruction = self.get_system_prompt(args.tools)

        instruction = instruction['content'] + "\n\n" + system_prompt

        instruction = {"role" : "system", "content" : instruction}

        messages = self.resources.messages.swap_system_prompt(
            messages = messages, system_prompt = instruction
        )
        
        # run steps for each field type
        for field_name, field_info in workflow.model_fields.items():

            field_type = field_info.annotation

            if not field_type == BaseModel:

                messages.append({
                    "role" : "user",
                    "content" : (
                        f"You are currently building the {field_name} field of {workflow_name}. "
                        f"Utilize your tools and skills to construct the field accurately and efficiently."
                    )
                })

                # build response model
                try:
                    field_response_model = create_model(
                        field_name.capitalize(),
                        **{field_name: (field_type, ...)}
                    )
                except Exception as e:
                    raise XNANOException(f"Error building field response model for agent [bold red]{self.config.name}[/bold red]: {e}")
                
                try:
                    field_response = completion(
                        messages = messages,
                        model = args.model, api_key = args.api_key, base_url = args.base_url,
                        mode = args.instructor_mode, response_model = field_response_model,
                        verbose = self.verbose, run_tools = True
                    )
                except Exception as e:
                    raise XNANOException(f"Error running field completion for agent [bold red]{self.config.name}[/bold red]: {e}")

                
                # add field response to completed workflow
                try:
                    completed_workflow[field_name] = getattr(field_response, field_name)

                    messages.append({
                        "role" : "assistant",
                        "content" : (
                            f"I have generated the {field_name} field for {workflow_name}:\n"
                            f"{json.dumps(getattr(field_response, field_name))}"
                        )
                    })

                    if self.verbose:
                        console.message(f"Added [bold gold1]{field_name}[/bold gold1] field to completed workflow for [bold red]{self.config.name}[/bold red]")

                except Exception as e:
                    raise XNANOException(f"Error adding field response to completed workflow for agent [bold red]{self.config.name}[/bold red]: {e}")
                
            else:

                messages.append({
                    "role" : "user",
                    "content" : (
                        f"We need to construct a nested workflow for the {field_name} field of {workflow_name}."
                    )
                })

                try:
                    field_response = self._execute_workflow(
                        workflow = field_type,
                        args = args
                    )
                except Exception as e:
                    raise XNANOException(f"Error executing nested workflow for agent [bold red]{self.config.name}[/bold red]: {e}")
                
                if self.verbose:
                    console.message(f"Added nested workflow field response to schema [bold red]{workflow_name}[/bold red] for agent [bold red]{self.config.name}[/bold red]")
                
                try:
                    completed_workflow[field_name] = field_response

                    messages.append({
                        "role" : "assistant",
                        "content" : (
                            f"I have completed the nested workflow for [bold red]{field_name}[/bold red] field in [bold red]{workflow_name}[/bold red]:\n"
                            f"{json.dumps(getattr(field_response, field_name))}"
                        )
                    })
                except Exception as e:
                    raise XNANOException(f"Error adding nested workflow field response to completed workflow for agent [bold red]{self.config.name}[/bold red]: {e}")
                
        response = workflow(**completed_workflow)

        if self.verbose:
            console.message(f"Completed workflow: [bold sky_blue1]{workflow_name}[/bold sky_blue1] with [bold red]{self.config.name}[/bold red]")

        return response

    # ----------------------------------------------------------
    # - multi agent
    # ----------------------------------------------------------

    def _build_agent_query(
            self,
            agent: 'Agent',
            messages: CompletionMessagesParam,
    ) -> str:
        """
        Builds a targeted query for a specific agent based on current context
        """
        try:
            query_model = create_model(
                'QueryBuilder',
                query=(str, ...),
                reasoning=(str, ...)
            )

            # Build context-aware prompt
            query_messages = [
                {"role": "system", "content": (
                    f"You are an expert query constructor working with {self.config.name}. "
                    f"Your task is to formulate a specific question or request for {agent.config.name}, "
                    f"who has the following role: {agent.config.role}\n\n"
                    "Based on the current conversation context, construct a targeted query that will "
                    "help advance the current objective."
                )},
                *messages,
                {"role": "user", "content": (
                    "Based on this context, what specific question or request should be asked to "
                    f"{agent.config.name} to help with the current situation? Provide both the query "
                    "and your reasoning."
                    "Ensure that you indicate who you are, and what your role is."
                )}
            ]

            query_response = completion(
                messages=query_messages,
                model=self.config.model,
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                organization=self.config.organization,
                response_model=query_model,
                mode = self.config.instructor_mode,
                verbose=self.verbose
            )

            if self.verbose:
                console.message(
                    f"Generated query for [bold red]{agent.config.name}[/bold red] with reasoning: "
                    f"[bold sky_blue1]{query_response.reasoning}[/bold sky_blue1]"
                )

            return query_response.query

        except Exception as e:
            raise XNANOException(
                message=f"Error building agent query: {e}"
            )
        
    def _converse_with_agents(
            self,
            agents: List['Agent'],
            messages: CompletionMessagesParam,
    ) -> List[Dict]:
        """
        Manages conversations with multiple agents, collecting their responses
        and formatting them for integration into the main conversation
        """
        if not agents:
            return []

        queries = []
        agent_names = []
        all_responses = []
        workflow_responses = []

        try:
            # Generate queries and get responses from each agent
            for agent in agents:
                query = self._build_agent_query(agent, messages)
                
                # Ensure query is properly formatted
                if isinstance(query, str):
                    query = [{"role": "user", "content": query}]
                
                queries.append(query)
                agent_names.append(agent.config.name)

                # Get response from agent using their own configuration
                response = agent.completion(
                    messages=query,
                    instructor_mode=agent.config.instructor_mode,
                    model=agent.config.model,
                    api_key=agent.config.api_key,
                    base_url=agent.config.base_url,
                    organization=agent.config.organization,
                    workflows=agent.config.workflows
                )

                # Handle workflow responses separately
                if hasattr(response, 'workflow') and response.workflow is not None:
                    workflow_responses.append(
                        f"\nWorkflow from {agent.config.name}:\n"
                        f"```json\n{response.workflow.model_dump_json(indent=2)}\n```"
                    )

                # Format response content
                if hasattr(response, 'choices') and response.choices:
                    response_content = response.choices[0].message.content
                else:
                    response_content = response.model_dump_json(indent=2)

                all_responses.append(
                    f"\nResponse from {agent.config.name}:\n{response_content}"
                )

            # Create properly formatted messages
            query_summary = {
                "role": "assistant",
                "content": (
                    "I have consulted with the following agents:\n\n" +
                    "\n".join([
                        f"- {name}: {query['content'] if isinstance(query, dict) else query}" 
                        for name, query in zip(agent_names, queries)
                    ])
                )
            }

            consolidated_response = {
                "role": "assistant",
                "content": (
                    "Here are the responses from all consulted agents:" +
                    "".join(all_responses) +
                    ("" if not workflow_responses else "\n\nWorkflows generated:" + "".join(workflow_responses))
                )
            }

            # Ensure all messages are properly formatted before returning
            messages_to_return = [query_summary, consolidated_response]
            for msg in messages_to_return:
                if "role" not in msg:
                    msg["role"] = "assistant"
                if "content" not in msg:
                    msg["content"] = str(msg)

            return messages_to_return

        except Exception as e:
            raise XNANOException(
                message=f"Error in agent conversation: {e}"
            )

    # ----------------------------------------------------------
    # - completions
    # ----------------------------------------------------------

    # - // runner (does not save to state)

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
        
        completed_workflow = None
        
        if not messages:
            messages = self.resources.collect_message_from_cli()

        messages = self.resources.format_new_messages(messages)

        # Handle one-time agent collaborations
        if agents:
            agent_messages = self._converse_with_agents(agents, messages)
            messages.extend(agent_messages)

        # Handle team agent consultations
        if self.config.agents:
            required_agents = self._determine_required_agents(messages)
            if required_agents:
                team_messages = self._get_team_agent_responses(messages, required_agents)
                messages.extend(team_messages)

        args = self._build_completion_request(
            messages=messages,
            agents=agents,
            model=model,
            base_url=base_url,
            api_key=api_key,
            organization=organization,
            tools=tools,
            instructor_mode=instructor_mode,
            response_model=response_model,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls
        )

        # Check if workflow is needed
        workflows = self.get_workflows(workflows)
        if workflows and self._determine_if_workflow_required(args=args, workflows=workflows):
            # Select and execute workflow
            workflow = self._select_workflow_to_run(args=args, workflows=workflows)
            completed_workflow = self._execute_workflow(workflow=workflow, args=args)

            # Return workflow response
            return self.resources.build_response_type(
                response=ModelResponse(
                    choices=[{
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(completed_workflow.model_dump(), indent=2)
                        }
                    }]
                ),
                workflow=completed_workflow,
                instructor=True if response_model else False
            )

        # Update context to include both workflows and team agents
        team_context = ""
        if self.config.agents:
            team_roles = "\n".join([
                f"- {agent.config.name}: {agent.config.role}"
                for agent in self.config.agents
            ])
            team_context = f"\n\nYou have access to the following team members:\n{team_roles}"

        workflow_context = self.resources.build_all_workflow_string_descriptions(
            workflows=self.config.workflows
        )

        context = (
            "You have access to the following workflows: \n\n" +
            workflow_context +
            team_context +
            "\nDo not hallucinate or make up tools/team members that are not listed."
        )

        try:
            return completion(
                messages=args.messages,
                model=args.model,
                base_url=args.base_url,
                api_key=args.api_key,
                organization=args.organization,
                tools=args.tools,
                mode=args.instructor_mode,
                response_model=response_model if response_model else args.response_model,
                tool_choice=args.tool_choice,
                parallel_tool_calls=args.parallel_tool_calls,
                context=context,
                run_tools=True
            )
        except Exception as e:
            raise XNANOException(
                message=f"Error running completion: {e}"
            )

    # - // main

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
        
        if not messages:
            messages = self.resources.collect_message_from_cli()

        messages = self.resources.format_new_messages(messages)

        # run completion
        try:
            response = self.run_completion(
                messages = messages, agents = agents,
                model = model, base_url = base_url, api_key = api_key,
                organization = organization, tools = tools,
                instructor_mode = instructor_mode, response_model = response_model,
                tool_choice = tool_choice, parallel_tool_calls = parallel_tool_calls,
                workflows = workflows
            )

            # add messages to state on success
            self.add_messages_to_state(messages)

            # add response to state (handles workflow automatically)
            self.add_response_to_state(
                response = response,
                instructor = True if response_model else False
            )

        except Exception as e:
            raise XNANOException(
                message = f"Error running completion: {e}"
            )

        # build summary if needed
        try:

            self.state.count += 1

            if self.state.count >= self.config.summarization_steps:
                self.build_summary(
                    model = model, api_key = api_key, base_url = base_url,
                    organization = organization
                )

        except Exception as e:
            raise XNANOException(
                message = f"Error incrementing summarization count: {e}"
            )

        return response

    def _determine_required_agents(
            self,
            messages: CompletionMessagesParam,
    ) -> List[str]:
        """
        Determines which agents from the team would be useful for the current context
        """
        if not self.config.agents:
            return []

        try:
            # Ensure messages are properly formatted
            if isinstance(messages, str):
                messages = [{"role": "user", "content": messages}]
            elif isinstance(messages, dict):
                messages = [messages]

            # Create dynamic model for agent selection
            AgentSelection = create_model(
                'AgentSelection',
                required_agents=(List[str], ...)
            )

            # Build agent roles string
            agent_roles = "\n".join([
                f"- {agent.config.name}: {agent.config.role}"
                for agent in self.config.agents
            ])

            # Query for needed agents
            selection = completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert team coordinator. Given the available team members "
                            "and the current conversation context, determine which team members would "
                            "be most helpful at this point.\n\n"
                            f"Available team members:\n{agent_roles}\n\n"
                            "Return ONLY the names of team members that would be genuinely useful "
                            "for the current context. Return an empty list if no team members are needed."
                        )
                    },
                    *messages
                ],
                model=self.config.model,
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                organization=self.config.organization,
                mode=self.config.instructor_mode,
                response_model=AgentSelection,
                verbose=self.verbose
            )

            if self.verbose:
                console.message(
                    f"Selected [bold gold1]{len(selection.required_agents)}[/bold gold1] team agents for current context"
                )

            return selection.required_agents

        except Exception as e:
            raise XNANOException(
                message=f"Error determining required agents: {e}"
            )

    def _get_team_agent_responses(
            self,
            messages: CompletionMessagesParam,
            required_agents: List[str]
    ) -> List[Dict]:
        """
        Gets responses from required team agents
        """
        if not required_agents:
            return []

        selected_agents = [
            agent for agent in self.config.agents
            if agent.config.name in required_agents
        ]

        return self._converse_with_agents(selected_agents, messages)
    
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
        Executes a specific workflow directly without running the workflow selection pipeline.
        Takes the same arguments as completion() but requires a workflow parameter.
        """
        if not messages:
            messages = self.resources.collect_message_from_cli()

        messages = self.resources.format_new_messages(messages)

        # Handle one-time agent collaborations
        if agents:
            agent_messages = self._converse_with_agents(agents, messages)
            messages.extend(agent_messages)

        # Handle team agent consultations
        if self.config.agents:
            required_agents = self._determine_required_agents(messages)
            if required_agents:
                team_messages = self._get_team_agent_responses(messages, required_agents)
                messages.extend(team_messages)

        args = self._build_completion_request(
            messages=messages,
            agents=agents,
            model=model,
            base_url=base_url,
            api_key=api_key,
            organization=organization,
            tools=tools,
            instructor_mode=instructor_mode,
            response_model=response_model,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls
        )

        try:
            completed_workflow = self._execute_workflow(
                workflow=workflow,
                args=args
            )

            response = self.resources.build_response_type(
                response=ModelResponse(
                    choices=[{
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(completed_workflow.model_dump(), indent=2)
                        }
                    }]
                ),
                workflow=completed_workflow,
                instructor=True if response_model else False
            )

            # Add messages and response to state
            self.add_messages_to_state(messages)
            self.add_response_to_state(
                response=response,
                instructor=True if response_model else False
            )

            # Handle summarization if needed
            self.state.count += 1
            if self.state.count >= self.config.summarization_steps:
                self.build_summary(
                    model=model,
                    api_key=api_key,
                    base_url=base_url,
                    organization=organization
                )

            return response

        except Exception as e:
            raise XNANOException(
                message=f"Error executing workflow: {e}"
            )

    def _analyze_task(
        self,
        messages: CompletionMessagesParam,
    ) -> Dict:
        """Creates simple task definition"""
        class Task(BaseModel):
            task: str
            complete_when: str

        try:
            task = completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a task analyzer. Given the context, define:\n"
                            "1. The core task\n"
                            "2. A single clear condition for completion"
                        )
                    },
                    *messages
                ],
                model=self.config.model,
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                organization=self.config.organization,
                mode=self.config.instructor_mode,
                response_model=Task,
                verbose=self.verbose
            )

            if self.verbose:
                console.message(
                    f"Defined task: [bold sky_blue1]{task.task}[/bold sky_blue1]"
                )

            return task.model_dump()

        except Exception as e:
            raise XNANOException(
                message=f"Error analyzing task: {e}"
            )

    def _is_task_complete(
        self,
        messages: List[Dict],
        task: Dict,
    ) -> bool:
        """Simple completion check"""
        class Complete(BaseModel):
            complete: bool

        try:
            check = completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"Task: {task['task']}\n"
                            f"Complete when: {task['complete_when']}\n\n"
                            "Based on the conversation, is this task complete? "
                            "Return only true or false."
                        )
                    },
                    *messages
                ],
                model=self.config.model,
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                organization=self.config.organization,
                mode=self.config.instructor_mode,
                response_model=Complete,
                verbose=self.verbose
            )

            return check.complete

        except Exception as e:
            raise XNANOException(
                message=f"Error checking completion: {e}"
            )

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
        """
        if not messages:
            messages = self.resources.collect_message_from_cli()

        messages = self.resources.format_new_messages(messages)

        # Define task
        task = self._analyze_task(messages)
        
        # Add task context
        messages.append({
            "role": "system",
            "content": (
                f"Current task: {task['task']}\n"
                f"Task is complete when: {task['complete_when']}"
            )
        })

        steps = 0
        last_response = None

        while steps < max_steps:
            try:
                # Check completion after first step
                if steps > 0:
                    state_messages = self.get_messages_from_state()
                    if self._is_task_complete(state_messages, task):
                        break

                # Check if workflow is needed
                workflows = self.get_workflows(workflows)
                if workflows and self._determine_if_workflow_required(
                    args=self._build_completion_request(
                        messages=messages if steps == 0 else self.get_messages_from_state(),
                        agents=agents,
                        model=model,
                        base_url=base_url,
                        api_key=api_key,
                        organization=organization,
                        tools=tools,
                        instructor_mode=instructor_mode,
                        response_model=response_model,
                        tool_choice=tool_choice,
                        parallel_tool_calls=parallel_tool_calls
                    ),
                    workflows=workflows
                ):
                    # Select and execute workflow
                    workflow = self._select_workflow_to_run(
                        args=self._build_completion_request(
                            messages=messages if steps == 0 else self.get_messages_from_state(),
                            agents=agents,
                            model=model,
                            base_url=base_url,
                            api_key=api_key,
                            organization=organization,
                            tools=tools,
                            instructor_mode=instructor_mode,
                            response_model=response_model,
                            tool_choice=tool_choice,
                            parallel_tool_calls=parallel_tool_calls
                        ),
                        workflows=workflows
                    )
                    
                    response = self.workflow(
                        workflow=workflow,
                        messages=messages if steps == 0 else None,
                        agents=agents,
                        model=model,
                        base_url=base_url,
                        api_key=api_key,
                        organization=organization,
                        tools=tools,
                        instructor_mode=instructor_mode,
                        response_model=response_model,
                        tool_choice=tool_choice,
                        parallel_tool_calls=parallel_tool_calls,
                    )
                else:
                    # Run regular completion
                    response = self.completion(
                        messages=messages if steps == 0 else None,
                        agents=agents,
                        model=model,
                        base_url=base_url,
                        api_key=api_key,
                        organization=organization,
                        tools=tools,
                        instructor_mode=instructor_mode,
                        response_model=response_model,
                        tool_choice=tool_choice,
                        parallel_tool_calls=parallel_tool_calls,
                    )

                last_response = response
                steps += 1
                messages = []  # Clear initial messages after first step

            except Exception as e:
                raise XNANOException(
                    message=f"Error in conversation step {steps}: {e}"
                )

        # Build simple result
        class Result(BaseModel):
            steps: int
            complete: bool
            task: str

        try:
            result = Result(
                steps=steps,
                complete=steps < max_steps,  # True if broke early
                task=task['task']
            )

            # Format final response
            if response_model:
                return result
            else:
                return self.resources.build_response_type(
                    response=ModelResponse(
                        choices=[{
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(result.model_dump(), indent=2)
                            }
                        }]
                    ),
                    workflow=None
                )

        except Exception as e:
            raise XNANOException(
                message=f"Error building conversation result: {e}"
            )