__all__ = [
    "convert_yaml_to_pydantic",
    "format_messages",
    "repair_messages",
    "verify_messages_integrity",
    "swap_system_prompt",
    "convert_to_openai_tool",
    "MessageUtils",
    "tools"
]


from ...lib.router import router


class convert_yaml_to_pydantic(router):
    pass


convert_yaml_to_pydantic.init("xnano.resources.utils.convert_yaml_to_pydantic", "convert_yaml_to_pydantic")


class format_messages(router):
    pass


format_messages.init("xnano.resources.utils.messages", "format_messages")


class repair_messages(router):
    pass


repair_messages.init("xnano.resources.utils.messages", "repair_messages")


class verify_messages_integrity(router):
    pass 


class swap_system_prompt(router):
    pass


swap_system_prompt.init("xnano.resources.utils.messages", "swap_system_prompt")


class convert_to_openai_tool(router):
    pass


convert_to_openai_tool.init("xnano.resources.completions.resources.tool_calling", "convert_to_openai_tool")


class MessageUtils(router):
    pass


MessageUtils.init("xnano.resources.utils.messages", "Messages")


class tools(router):
    pass


tools.init("xnano.resources.utils.tools", "tools")
