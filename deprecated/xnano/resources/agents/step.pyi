from ...types.agents.step import StepState
from typing import Dict, List, Optional, Any, Callable, Type, TypeVar, Generic
from pydantic import BaseModel

Agent = Type["Agent"]
T = TypeVar('T', bound=BaseModel)

class Steps:
    """
    execution handler for strict step-by-step workflows in xnano agents
    """

    def __init__(self, agent: Optional[Agent] = None, verbose: bool = False) -> None:
        """
        Initializes a steps workflow

        Args:
            agent (Optional[Agent]): The agent to use for the steps workflow
            verbose (bool): Whether to print verbose output
        """
        ...

    def step(
        self,
        name: str,
        depends_on: Optional[List[str]] = None,
        response_model: Optional[Type[BaseModel]] = None,
        condition: Optional[Callable[[StepState], bool]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Callable[[Callable[..., Dict[str, Any]]], Callable[..., T]]:
        """
        Step decorator with support for typed responses using Pydantic models

        Example:
            ```python
            class DataOutput(BaseModel):
                data: str
                metadata: Dict[str, Any]

            @steps.step("process_data", 
                       depends_on=["fetch_data"],
                       response_model=DataOutput)
            def process_data(agent: Agent, input_data: Dict[str, Any]) -> Dict[str, Any]:
                return {"data": "processed", "metadata": {}}
            ```

        Args:
            name (str): The name of the step
            depends_on (Optional[List[str]]): The names of the steps that must be executed before this step
            response_model (Optional[Type[BaseModel]]): Pydantic model for type-safe responses
            condition (Optional[Callable[[StepState], bool]]): A condition that must be met for the step to be executed
            metadata (Optional[Dict[str, Any]]): Metadata for the step

        Returns:
            Callable: The decorated function with typed response
        """
        ...

    def add_step(
        self,
        name: str,
        handler: Callable,
        depends_on: Optional[List[str]] = None,
        condition: Optional[Callable[[StepState], bool]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Programmatically add a step without using the decorator

        Example:
            ```python
            steps.add_step("process_data", process_data_func, depends_on=["fetch_data"])
            ```

        Args:
            name (str): The name of the step
            handler (Callable): The function to execute for the step
            depends_on (Optional[List[str]]): The names of the steps that must be executed before this step
            condition (Optional[Callable[[StepState], bool]]): A condition that must be met for the step to be executed
            metadata (Optional[Dict[str, Any]]): Metadata for the step

        Returns:
            None
        """
        ...

    def execute(self) -> BaseModel:
        """
        Execute all steps in the correct order

        Example:
            ```python
            class DataOutput(BaseModel):
                data: str

            @steps.step("process_data", response_model=DataOutput)
            def process_data(agent: Agent, input_data: Dict[str, Any]) -> Dict[str, Any]:
                return {"data": "processed"}

            results = steps.execute()
            print(results.process_data.data)  # Typed access
            ```

        Returns:
            BaseModel: Results from all completed steps in a typed model
        """
        ...

    def reset(self) -> None:
        """Reset all steps to their initial state"""
        ...
