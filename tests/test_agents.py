# Agent Tests

from xnano import Agent
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

    agent = Agent(name = "John")

    response = agent.completion(
        "What is your name?"
    )

    assert "john" in response.choices[0].message.content.lower()


def test_agents_completion_with_short_term_memory():

    agent = Agent(name = "John")

    response = agent.completion(
        "My name is Steve"
    )

    response = agent.completion(
        "What is my name?"
    )

    assert "steve" in response.choices[0].message.content.lower()
