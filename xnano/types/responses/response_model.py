# completion response model

from pydantic import BaseModel
from typing import Any


# model
class ResponseModel(BaseModel):
    """Base completion response model."""

    response: Any

