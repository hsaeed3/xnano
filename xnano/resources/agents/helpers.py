import random
from typing import Optional


def get_random_name():
    names = [
        "John", "Alice", "Bob", "Grace", "David", "Eve", "Frank", "Hannah", "Hank", "Ivy", "Jack", "Jasmine", "Larry", "Katherine", "Noah", "Mabel", "Ryan", "Nina", "Victor", "Olivia", "Xavier", "Pam", "Zach", "Queenie",
        "Charlie", "Abigail", "Trent", "Beatrice", "Sasha", "Charlotte", "Quinn", "Diana", "Yvonne", "Eleanor", "Wendy", "Fiona", "Ursula", "Giselle", "Sasha", "Iris", "Tamsin", "Ophelia", "Vera", "Petunia", "Roxanne", "Selene"
    ]
    return random.choice(names)


# -----------------------------------------------------------------
# INSTRUCTION HELPER FUNCTIONS
# -----------------------------------------------------------------

def build_instruction(
        name : str,
        role : str,
        tool_names : Optional[list] = None,
        instructions : Optional[str] = None
) -> dict:
    
    tool_string = ""
    intro_string = (
        f"You are {name}, a world class {role}."
        "As a genius expert, you are able to solve complex problems and provide insightful answers to any question, with a specialization using your role.\n\n"
    )

    if tool_names:
        tool_string = (
            f"You have access to the following tools:\n{tool_names}\n"
            "Use your given tools to assist you in completing your various tasks.\n\n"
        )

    return {
        "role" : "system",
        "content" : intro_string + (tool_string if tool_string else "") + (instructions if instructions else "")
    }