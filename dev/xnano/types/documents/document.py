# document type

from pydantic import BaseModel
from typing import Dict, Any, Optional
from ...pydantic import patch


@patch
class Document(BaseModel):
    text : str
    metadata : Optional[Dict[str, Any]] = None