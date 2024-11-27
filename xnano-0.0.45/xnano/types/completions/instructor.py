from typing import Literal


# instructor generation mode
InstructorMode = Literal[
    "function_call",
    "parallel_tool_call",
    "tool_call",
    "mistral_tools",
    "json_mode",
    "json_o1",
    "markdown_json_mode",
    "json_schema_mode",
    "anthropic_tools",
    "anthropic_json",
    "cohere_tools",
    "vertexai_tools",
    "vertexai_json",
    "gemini_json",
    "gemini_tools",
    "json_object",
    "tools_strict",
]
