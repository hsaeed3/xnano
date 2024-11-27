__all__ = [
    "Agent",
    "create_agent",
    "Steps"
]


from ...lib.router import router


class create_agent(router):
    pass


create_agent.init("xnano.resources.agents.initializer", "create_agent")


class Agent(router):
    pass


Agent.init("xnano.resources.agents.agent", "Agent")


class Steps(router):
    pass


Steps.init("xnano.resources.agents.step", "Steps")