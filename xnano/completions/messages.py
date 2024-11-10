# message utilities

import json
from ..lib.exceptions import XNANOException
from ..types.messages.message import Message
from typing import List, Union


# formatter
def format_messages(
        messages : Union[
            str,
            Message,
            List[Message],
            List[List[Message]]
        ],
) -> List[Message]:
    
    """
    Formats messages for use in completions.

    Args:
        messages (Union[str, CompletionMessage, List[CompletionMessage]]): Messages to format.

    Returns:
        List[CompletionMessage]: Formatted messages.
    """

    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]
    
    # Check if messages is a dictionary with the expected keys
    elif isinstance(messages, dict) and "role" in messages and "content" in messages:
        return [messages]
    
    elif isinstance(messages, list) and isinstance(messages[0], dict):
        return messages
    
    raise ValueError("Invalid message format")


def add_context_to_messages(
        messages: Union[List[Message], List[List[Message]]],
        additional_context: any
) -> Union[List[Message], List[List[Message]]]:
    """
    Adds content to the content string of the latest system message or creates a new system message if none exists.

    Args:
        messages (Union[List[Message], List[List[Message]]]): The messages to update.
        additional_context (str): The content to add to the latest system message.

    Returns:
        Union[List[Message], List[List[Message]]]: The updated messages.
    """

    additional_context = json.dumps(additional_context)

    additional_context_string = f"""
    Relevant context:
    {additional_context}
    """

    try:
        if isinstance(messages, list) and all(isinstance(msg, list) for msg in messages):
            # Handle list of lists of messages
            for sublist in messages:
                for msg in reversed(sublist):
                    if msg['role'] == 'system':
                        msg['content'] += additional_context_string
                        return messages
                # If no system message found, add one
                sublist.append({'role': 'system', 'content': additional_context_string})
                return messages
        else:
            # Handle list of messages
            for msg in reversed(messages):
                if msg['role'] == 'system':
                    msg['content'] += additional_context_string
                    return messages
            # If no system message found, add one
            messages.append({'role': 'system', 'content': additional_context_string})
            return messages

    except Exception as e:
        raise XNANOException(f"Failed to add content to latest system message: {e}")
