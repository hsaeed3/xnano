# Agent Tests

from xnano import Agent
from pydantic import BaseModel
import pytest


def test_agents_blank_init():
    agent = Agent()

    assert agent.config.name is not None
    assert agent.config.role is not None
    assert agent.config.model is not None


# -------------------------------------------------------------------------------------------------
# Single Agent Completions (Non Workflow / Chaining)
# -------------------------------------------------------------------------------------------------


def test_agents_single_completion_context():
    agent = Agent(name="John")

    response = agent.completion("What is your name?")

    assert "john" in response.choices[0].message.content.lower()


def test_agents_completion_with_short_term_memory():
    agent = Agent(name="John")

    response = agent.completion("My name is Steve")

    response = agent.completion("What is my name?")

    assert "steve" in response.choices[0].message.content.lower()


# workflow test
def test_agents_workflow():

    class Refinement(BaseModel):
        determine_errors : str
        plan_steps_to_fix : list[str]
        solution : str

    agent = Agent(workflows = [Refinement])

    code = """
    def calculate_sum(a, b)
        sum = a + b;
        print("The sum is: " sum)
        retrun sum
    """

    response = agent.completion(
        messages = f"I'm having trouble with this code: {code}, could you refine it?"
    )

    assert response.workflow is not None
    assert response.choices[0].message.content is not None

    assert "calculate_sum" in response.choices[0].message.content.lower()
    assert "calculate_sum" in response.workflow.solution.lower()


# step test
def test_agents_steps():

    agent = Agent()

    steps = agent.steps()

    @steps.step("collect_data")
    def collect_data(agent: Agent, state, input_data):
        response = agent.completion(
            messages="Collect relevant data for analysis"
        )
        return {"data": response.choices[0].message.content}

    @steps.step("analyze_data", depends_on=["collect_data"])
    def analyze_data(agent: Agent, state, input_data):
        data = input_data["collect_data"]["data"]
        response = agent.completion(
            messages=f"Analyze this data: {data}"
        )
        return {"analysis": response.choices[0].message.content}
    
    results = steps.execute()

    assert results is not None
    assert results["analyze_data"] is not None
    

if __name__ == "__main__":
    import pytest

    pytest.main([__file__])
