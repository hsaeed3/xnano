from pydantic import BaseModel
from typing import Any, Optional, Union, Type, Dict, List


# context type
Context = Union[Type[BaseModel], BaseModel, Dict, List, str, Any]
