# message utilities

import json
from typing import List, Union, Literal, Dict, Any, Optional
from pydantic import BaseModel

from ...lib import XNANOException
from ...types.completions.messages import Message


# formatter
def format_messages(
    messages: Union[str, Message, List[Message], List[List[Message]]],
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


def swap_system_prompt(
    messages: Union[List[Message], List[List[Message]]],
    system_prompt: Union[Message, str],
) -> Union[List[Message], List[List[Message]]]:
    """
    Replaces the content of the latest system message with new content and removes any other system messages.

    Args:
        messages (Union[List[Message], List[List[Message]]]): The messages to update.
        new_system_prompt (str): The new system prompt content.

    Returns:
        Union[List[Message], List[List[Message]]]: The updated messages with single system prompt.
    """

    if isinstance(system_prompt, str):
        system_prompt = {"role": "system", "content": system_prompt}

    try:
        if isinstance(messages, list) and all(
            isinstance(msg, list) for msg in messages
        ):
            # Handle list of lists of messages
            for sublist in messages:
                # Remove all system messages
                sublist[:] = [msg for msg in sublist if msg["role"] != "system"]
                # Add new system message at start
                sublist.insert(0, system_prompt)
            return messages
        else:
            # Handle list of messages
            # Remove all system messages
            messages[:] = [msg for msg in messages if msg["role"] != "system"]
            # Add new system message at start
            messages.insert(0, system_prompt)
            return messages

    except Exception as e:
        raise XNANOException(f"Failed to swap system prompt: {e}")


def add_context_to_messages(
    messages: Union[List[Message], List[List[Message]]], additional_context: any
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
        if isinstance(messages, list) and all(
            isinstance(msg, list) for msg in messages
        ):
            # Handle list of lists of messages
            for sublist in messages:
                for msg in reversed(sublist):
                    if msg["role"] == "system":
                        msg["content"] += additional_context_string
                        return messages
                # If no system message found, add one
                sublist.append({"role": "system", "content": additional_context_string})
                return messages
        else:
            # Handle list of messages
            for msg in reversed(messages):
                if msg["role"] == "system":
                    msg["content"] += additional_context_string
                    return messages
            # If no system message found, add one
            messages.append({"role": "system", "content": additional_context_string})
            return messages

    except Exception as e:
        raise XNANOException(f"Failed to add content to latest system message: {e}")


def add_message(
    input: Union[Message, str, Dict[str, Any]],
    messages: List[Message],
    role: Literal["user", "assistant", "system", "tool"] = "user",
) -> List[Message]:
    """
    Adds a message to the list of messages.
    """

    if issubclass(type(input), BaseModel):
        
        messages.append(
            input.choices[0].message.model_dump()
        )

    elif isinstance(input, Dict):

        messages.append(
            input["choices"][0]["message"]
        )

    elif isinstance(input, str):

        messages.append(
            {"role": role, "content": input}
        )

    else:
        raise ValueError(f"Invalid input type: {type(input)}")

    return messages


def verify_messages_integrity(messages: Union[List[Message], Message]) -> List[Message]:
    """
    Verifies the integrity of the messages by checking that:
    1. Input is a list of dictionaries
    2. Each message contains required 'role' and 'content' keys
    
    Will attempt to repair nested lists before raising validation errors.
    
    Args:
        messages (List[Message]): Messages to verify
        
    Returns:
        List[Message]: Verified (and potentially repaired) messages
        
    Raises:
        ValueError: If messages fail validation after repair attempt
    """
    if isinstance(messages, Dict):

        # ensure "role" and "content" keys are present
        if "role" not in messages:
            raise ValueError(f"Message missing required 'role' key: {messages}")
        if "content" not in messages:
            raise ValueError(f"Message missing required 'content' key: {messages}")
        
        return [messages]

    try:
        messages = repair_messages(messages)
    except ValueError:
        pass
        
    if not isinstance(messages, list):
        raise ValueError("Messages must be a list")
        
    for msg in messages:
        if not isinstance(msg, dict):
            raise ValueError(f"Each message must be a dictionary, got {type(msg)}")
            
        if "role" not in msg:
            raise ValueError(f"Message missing required 'role' key: {msg}")
            
        if "content" not in msg:
            raise ValueError(f"Message missing required 'content' key: {msg}")
        
    return messages


def repair_messages(messages: Union[List[Message], List[List[Message]]]) -> List[Message]:
    """
    Flattens the list of messages to ensure there are no hidden nested lists.

    Args:
        messages (Union[List[Message], List[List[Message]]]): The messages to repair.

    Returns:
        List[Message]: A flattened list of messages.
    """
    repaired_messages = []

    if isinstance(messages, list):
        for msg in messages:
            if isinstance(msg, list):
                repaired_messages.extend(repair_messages(msg)) 
            else:
                repaired_messages.append(msg)
    else:
        raise ValueError("Invalid message format: Expected a list.")

    return repaired_messages


class Messages:

    def __init__(self, messages: Optional[List[Message]] = None):
        if messages is None:
            self.messages = []
        else:
            self.messages = messages

    def get_messages(self) -> List[Message]:
        """
        Retrieves the current list of messages.

        Returns:
            List[Message]: The current messages.
        """
        return self.messages

    def clear_messages(self) -> None:
        """
        Clears all messages from the list.
        """
        self.messages.clear()

    def add_message(self, input: Union[Message, str, Dict[str, Any]], role: Literal["user", "assistant", "system", "tool"] = "user") -> None:
        """
        Adds a message to the list of messages.
        """
        self.messages = add_message(input, self.messages, role)

    def format(self) -> List[Message]:
        """
        Formats the current messages using the format_messages utility.
        
        Returns:
            List[Message]: Formatted messages.
        """
        return format_messages(self.messages)

    def repair(self) -> None:
        """
        Repairs the messages to ensure there are no hidden nested lists.
        """
        self.messages = repair_messages(self.messages)


