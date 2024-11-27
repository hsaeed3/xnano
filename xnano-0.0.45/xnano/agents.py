# xnano.agents

# the xnano multi agent framework !!!!
# can do many cool things

# workflow creation
# strict step-by-step execution
# multi agent collaboration
# tool execution
# & more :)

__all__ = [
    "Agent",
    "Steps",
    "create_agent",
]


from ._lib.router import router


class Agent(router):
    pass


Agent.init("xnano.resources.agents.agent", "Agent")


class Steps(router):
    pass

Steps.init("xnano.resources.agents.step", "Steps")


class create_agent(router):
    pass

create_agent.init("xnano.resources.agents.initializer", "create_agent")