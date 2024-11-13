# completion arguments

from pydantic import BaseModel
from typing import Any, Callable, Dict, List, Optional, Type, Union, Literal
import httpx


# completion arguments
class CompletionArguments(BaseModel):
    """Base Completion Arguments Model"""

    class Config:
        arbitrary_types_allowed = True

    # messages
    messages: Union[
        str, Dict[str, Any], List[Dict[str, Any]], List[List[Dict[str, Any]]]
    ]

    # model
    model: str

    # CONTEXT
    # new argument in zyx 1.1.x
    # context can be a pydantic model, dict, list, string etc.
    context: Optional[Union[Type[BaseModel], BaseModel, Dict, List, str]]

    # optional arguments
    # instructor mode
    mode: Optional[str] = None
    # structured output
    response_model: Optional[
        Union[
            BaseModel,
            Type[BaseModel],
            str,
            Dict[str, Any],
            Type[int],
            Type[float],
            Type[str],
            Type[bool],
            Type[list],
        ]
    ] = None
    # response format
    response_format: Optional[
        Union[
            BaseModel,
            Type[BaseModel],
            str,
            Dict[str, Any],
            Type[int],
            Type[float],
            Type[str],
            Type[bool],
            Type[list],
        ]
    ] = None

    # tool calling
    # tool execution
    run_tools: Optional[bool] = None
    # tool type
    tools: Optional[List[Union[str, Callable, Type[BaseModel], Dict[str, Any]]]] = None
    # tool arguments
    tool_choice: Optional[Literal["auto", "required", "none"]] = None
    parallel_tool_calls: Optional[bool] = None

    # base completion arguments
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    organization: Optional[str] = None
    n: Optional[int] = None
    timeout: Optional[Union[float, str, httpx.Timeout]] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stream_options: Optional[dict] = None
    stop: Optional[Any] = None
    max_completion_tokens: Optional[int] = None
    max_tokens: Optional[int] = None
    modalities: Optional[str] = None
    prediction: Optional[Dict[str, Any]] = None
    audio: Optional[Dict[str, Any]] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[dict] = None
    user: Optional[str] = None
    # openai v1.0+ new params
    seed: Optional[int] = None
    logprobs: Optional[bool] = None
    top_logprobs: Optional[int] = None
    deployment_id: Optional[str] = None
    extra_headers: Optional[dict] = None
    # soon to be deprecated params by OpenAI
    functions: Optional[List] = None
    function_call: Optional[str] = None
    # set api_base, api_version, api_key
    api_version: Optional[str] = None
    models_list: Optional[list] = None
    stream: Optional[bool] = None
