# Instruction Base Model
# Sectioned System Prompt

from pydantic import BaseModel
from typing import Optional


class Instruction(BaseModel):

    intro_string : str = (
        "You are {name}, a world class {role}."
        "As a genius expert, you are able to solve complex problems and provide insightful answers to any question, with a specialization using your role.\n\n"
    )

    tool_string : Optional[str] = (
        "You have access to the following tools:\n{tools}\n"
        "You can use these tools to solve complex problems and provide insightful answers to any question.\n\n"
    )

    def build_intro_string(
            self,
            name : str,
            role : str
    ):
        return self.intro_string.format(name = name, role = role)
    
    
    