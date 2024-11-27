# Agent State

from pydantic import BaseModel
from typing import List, Dict, Any


class AgentState(BaseModel):

    """The state of an agent"""

    new_messages : List[Dict[str, Any]] = []

    current_messages : List[Dict[str, Any]] = []

    summary_messages : List[Dict[str, Any]] = []

    current_message_count : int = 0