from pydantic import BaseModel
from typing import List, Optional


class State(BaseModel):

    messages : List
    summary_thread : Optional[List] = None
    count : int = 0

    
