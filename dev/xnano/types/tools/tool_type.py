# tool type

from pydantic import BaseModel
from typing import Callable, Type, Dict, Any, Union


# tool type
ToolType = Union[str, Callable, Type[BaseModel], Dict[str, Any]]
