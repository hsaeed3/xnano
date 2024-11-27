from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Callable, Union, TypeVar
from enum import Enum

T = TypeVar('T')

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class StepModel(BaseModel):
    """Base model for step configuration"""
    name: str
    handler: Callable
    depends_on: Optional[List[str]] = None
    condition: Optional[Callable] = None
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('depends_on')
    def validate_dependencies(cls, v):
        if v is not None and not isinstance(v, list):
            raise ValueError("depends_on must be a list of step names")
        return v

class StepState(BaseModel):
    """State management for steps"""
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    results: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_result(self, step_name: str, result: Any):
        """Safely add a result to the state"""
        self.results[step_name] = result
        
    def get_result(self, step_name: str) -> Any:
        """Safely retrieve a result from the state"""
        return self.results.get(step_name)