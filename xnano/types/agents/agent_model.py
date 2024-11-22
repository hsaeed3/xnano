from pydantic import BaseModel
from typing import List, Optional


class AgentModel(BaseModel):

    class Config:

        arbitrary_types_allowed = True

    
    # agent definition params
    name : Optional[str] = None
    role : str
    instructions : Optional[str] = None

    agents : Optional[List] = None

    # agent specialization params
    tools : Optional[List] = None
    workflows : Optional[List] = None
    memory : Optional[List] = None

    # agent llm params
    model : str = "gpt-4o-mini"
    base_url : Optional[str] = None
    api_key : Optional[str] = None
    organization : Optional[str] = None
    instructor_mode : Optional[str] = None

    # agent summary params
    summarization_steps : Optional[int] = 5

    # workflow / planning params
    planning : bool = False