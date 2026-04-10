# message parameter type


import sys

if sys.version_info >= (3, 11):
    from typing import (
        Any,
        Literal,
        Mapping,
        NotRequired,
        Sequence,
        TypedDict,
        Union,
        List,
    )
else:
    from typing import Any, Literal, Mapping, Sequence
    from typing_extensions import NotRequired, TypedDict, Union, List


# tool call function
class ToolCallFunction(TypedDict):
    """
    Tool call function.
    """

    name: str
    "Name of the function."

    arguments: NotRequired[Mapping[str, Any]]
    "Arguments of the function."


# tool call
class ToolCall(TypedDict):
    """
    Model tool calls.
    """

    function: ToolCallFunction
    "Function to be called."


# message
class Message(TypedDict):
    """
    Chat message.
    """

    role: Literal["user", "assistant", "system", "tool"]
    "Assumed role of the message. Response messages always has role 'assistant' or 'tool'."

    content: NotRequired[str]
    "Content of the message. Response messages contains message fragments when streaming."

    images: NotRequired[Sequence[Any]]
    """
  Optional list of image data for multimodal models.

  Valid input types are:

  - `str` or path-like object: path to image file
  - `bytes` or bytes-like object: raw image data

  Valid image formats depend on the model. See the model card for more information.
  """

    tool_calls: NotRequired[Sequence[ToolCall]]
    """
  Tools calls to be made by the model.
  """
