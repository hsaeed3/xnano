from ...types.agents.step import StepModel, StepState, StepStatus
from ...lib import console, XNANOException
from typing import Dict, List, Optional, Any, Callable, Type, Union
from functools import wraps
from pydantic import BaseModel, create_model
from typing_extensions import Annotated

Agent = Type["Agent"]


class Steps:
    """
    Step execution handler for agents
    """

    def __init__(self, agent: Optional[Agent] = None, verbose: bool = False):
        self.agent = agent
        self.verbose = verbose
        self.steps: Dict[str, StepModel] = {}
        self.state = StepState()
        self._current_step: Optional[str] = None
        self._executed_steps: List[str] = []
        self._response_models: Dict[str, Type[BaseModel]] = {}

    def step(
        self,
        name: str,
        depends_on: Optional[List[str]] = None,
        response_model: Optional[Type[BaseModel]] = None,
        condition: Optional[Callable[[StepState], bool]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        """
        Step decorator with simplified interface and structured outputs

        Example:
            class DataOutput(BaseModel):
                data: str
                metadata: Dict[str, Any]

            @steps.step("process_data", 
                       depends_on=["fetch_data"],
                       response_model=DataOutput)
            def process_data(agent: Agent, input_data: Dict[str, Any]) -> Dict[str, Any]:
                # Process the data
                return {"data": "processed", "metadata": {}}
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                result = func(
                    agent=self.agent,
                    input_data=kwargs.get("input_data", {})
                )
                
                if response_model:
                    self._response_models[name] = response_model
                    return response_model(**result)
                return result

            self.steps[name] = StepModel(
                name=name,
                handler=wrapper,
                depends_on=depends_on,
                condition=condition,
                metadata=metadata or {},
            )

            if self.verbose:
                agent_name = self.agent.config.name if self.agent else "standalone"
                console.message(
                    f"Added step [bold gold1]{name}[/bold gold1] to [bold red]{agent_name}[/bold red]"
                )

            return wrapper

        return decorator

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
            steps.add_step("process_data", process_data_func, depends_on=["fetch_data"])
        """
        if name in self.steps:
            raise XNANOException(f"Step {name} already exists")

        @wraps(handler)
        def wrapped_handler(*args, **kwargs):
            if self.agent:
                return handler(
                    agent=self.agent,
                    state=self.state,
                    input_data=kwargs.get("input_data", {}),
                )
            return handler(state=self.state, input_data=kwargs.get("input_data", {}))

        self.steps[name] = StepModel(
            name=name,
            handler=wrapped_handler,
            depends_on=depends_on,
            condition=condition,
            metadata=metadata or {},
        )

    def _validate_dependencies(self) -> None:
        """Validate all step dependencies exist and there are no cycles"""
        for step in self.steps.values():
            if step.depends_on:
                for dep in step.depends_on:
                    if dep not in self.steps:
                        raise XNANOException(
                            f"Step {step.name} depends on non-existent step {dep}"
                        )

        # Check for cycles
        visited = set()
        temp = set()

        def has_cycle(step_name: str) -> bool:
            if step_name in temp:
                return True
            if step_name in visited:
                return False

            temp.add(step_name)
            step = self.steps[step_name]
            if step.depends_on:
                for dep in step.depends_on:
                    if has_cycle(dep):
                        return True
            temp.remove(step_name)
            visited.add(step_name)
            return False

        for step_name in self.steps:
            if has_cycle(step_name):
                raise XNANOException("Circular dependency detected in steps")

    def _can_run_step(self, step: StepModel) -> bool:
        """Check if a step can be executed"""
        if not step.depends_on:
            return True
        return all(
            self.steps[dep].status == StepStatus.COMPLETED for dep in step.depends_on
        )

    def _execute_step(self, step: StepModel) -> Any:
        """Execute a single step with proper error handling and state management"""
        try:
            if step.name in self._executed_steps:
                return step.result

            step.status = StepStatus.RUNNING
            self._current_step = step.name

            # Check condition
            if step.condition and not step.condition(self.state):
                step.status = StepStatus.SKIPPED
                return None

            # Get input data from dependencies
            input_data = {
                dep: self.steps[dep].result
                for dep in (step.depends_on or [])
                if self.steps[dep].status == StepStatus.COMPLETED
            }

            # Execute handler
            result = step.handler(input_data=input_data)

            step.result = result
            step.status = StepStatus.COMPLETED
            self.state.add_result(step.name, result)
            self._executed_steps.append(step.name)

            if self.verbose:
                agent_name = self.agent.config.name if self.agent else "standalone"
                console.message(
                    f"Completed step [bold gold1]{step.name}[/bold gold1] for [bold red]{agent_name}[/bold red]"
                )

            return result

        except Exception as e:
            step.status = StepStatus.FAILED
            raise XNANOException(message=f"Error executing step {step.name}: {str(e)}")
        finally:
            self._current_step = None

    def execute(self) -> BaseModel:
        """
        Execute all steps in the correct order

        Returns:
            BaseModel: Results from all completed steps in a typed model
        """
        # Validate dependencies before execution
        self._validate_dependencies()
        
        # Execute steps in order based on dependencies
        results = {}
        pending_steps = set(self.steps.keys())
        
        while pending_steps:
            for step_name in list(pending_steps):
                step = self.steps[step_name]
                if self._can_run_step(step):
                    results[step_name] = self._execute_step(step)
                    pending_steps.remove(step_name)
        
        # Dynamically create a result model based on registered response models
        fields = {
            name: (model, ...) 
            for name, model in self._response_models.items()
        }
        ResultModel = create_model('ResultModel', **fields)
        
        return ResultModel(**results)

    def reset(self) -> None:
        """Reset all steps to their initial state"""
        for step in self.steps.values():
            step.status = StepStatus.PENDING
            step.result = None
        self.state = StepState()
        self._executed_steps = []
        self._current_step = None
