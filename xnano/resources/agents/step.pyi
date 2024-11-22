from ...types.agents.step import StepState
from typing import Dict, List, Optional, Any, Callable, Type


Agent = Type["Agent"]


class Steps:

    """
    execution handler for strict step-by-step workflows in xnano agents
    """

    def __init__(
        self,
        agent: Optional[Agent] = None,
        verbose: bool = False
    ) -> None:
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
        condition: Optional[Callable[[StepState], bool]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Callable:
        """
        Step decorator that can be used both with and without an agent
        
        Example:
            ```python
            @steps.step("process_data", depends_on=["fetch_data"])
            def process_data(state: StepState, input_data: Dict[str, Any]) -> Any:
                # Process the data
                return processed_data
            ```

        Args:
            name (str): The name of the step
            depends_on (Optional[List[str]]): The names of the steps that must be executed before this step
            condition (Optional[Callable[[StepState], bool]]): A condition that must be met for the step to be executed
            metadata (Optional[Dict[str, Any]]): Metadata for the step

        Returns:
            Callable: The decorated function
        """
        ...

    def add_step(
        self,
        name: str,
        handler: Callable,
        depends_on: Optional[List[str]] = None,
        condition: Optional[Callable[[StepState], bool]] = None,
        metadata: Optional[Dict[str, Any]] = None
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

    def execute(self) -> Dict[str, Any]:
        """
        Execute all steps in the correct order

        Example:
            ```python
            @steps.step("process_data", depends_on=["fetch_data"])
            def process_data(state: StepState, input_data: Dict[str, Any]) -> Any:
                # Process the data
                return processed_data

            results = steps.execute()
            ```

        Returns:
            Dict[str, Any]: Results from all completed steps
        """
        ...

    def reset(self) -> None:
        """Reset all steps to their initial state"""
        ...
