# document type

from pydantic import BaseModel
from typing import Dict, Any, Optional


class Document(BaseModel):
    content : str
    metadata : Optional[Dict[str, Any]] = None