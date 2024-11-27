# Batch Completions Resource
from ....types.completions.arguments import CompletionArguments
from ....types.embeddings.memory import Memory
from ....types.completions.params import (
    CompletionMessagesParam,
    CompletionAudioParam,
    CompletionChatModelsParam,
    CompletionContextParam,
    CompletionInstructorModeParam,
    CompletionResponseModelParam,
    CompletionModalityParam,
    CompletionPredictionContentParam,
    CompletionToolChoiceParam,
    CompletionToolsParam,
)
from ....types.completions.responses import Response

from ....lib import console, XNANOException

from .messages import add_context_to_messages, format_messages
from .structured_outputs import create_dynamic_response_model

import json
import httpx
from typing import Optional, Union, List
from pydantic import BaseModel


class BatchDetermination(BaseModel):
    multi_message_batch_job: bool = False
    multi_model_batch_job: bool = False


def determine_batch_needed(
    messages: CompletionMessagesParam,
    model: CompletionChatModelsParam = "gpt-4o-mini",
) -> BatchDetermination:
    """Determines if a batch job is needed for the given parameters."""

    determination = BatchDetermination()

    if isinstance(model, list):
        determination.multi_model_batch_job = True

    if isinstance(messages, list) and isinstance(messages[0], list):
        determination.multi_message_batch_job = True

    if determination.multi_message_batch_job and determination.multi_model_batch_job:
        raise XNANOException(
            "Batch jobs both using multiple message threads & multiple models are not supported."
        )

    return determination


def warn_unsupported_batch_params(
    tools: Optional[List[CompletionToolsParam]] = None,
    run_tools: Optional[bool] = None,
    memory: Optional[Memory] = None,
    stream: Optional[bool] = None,
    response_format: Optional[CompletionResponseModelParam] = None,
) -> List:
    """Warns about unsupported batch parameters."""

    if not tools:
        return None

    if tools:
        for tool in tools:
            if isinstance(tool, str):
                console.warning(
                    f"Batch completions do not support generated tools. Ignoring {tool}..."
                )
                tools.remove(tool)

    if tools and run_tools:
        console.warning("Batch completions do not support tool execution. Ignoring...")

    if stream and response_format:
        console.warning(
            "Batch completions do not support streaming when using structured outputs. Ignoring..."
        )

    if memory:
        console.warning(
            "Batch completions do not support using Vector Stores for context. Ignoring..."
        )

    return tools


def build_pydantic_model_from_string_dictionary(
    response: str | dict, response_format: BaseModel
) -> BaseModel:
    """Builds a pydantic model from a string or dictionary."""

    try:
        response = json.loads(response.choices[0].message.content)
    except Exception as e:
        raise XNANOException(f"Failed to convert response to dictionary: {e}")

    # build pydantic model
    try:
        return response_format.model_validate(response)
    except Exception as e:
        raise XNANOException(f"Failed to validate response as pydantic model: {e}")


def create_batch_completion_job(
    messages: CompletionMessagesParam,
    model: CompletionChatModelsParam = "gpt-4o-mini",
    context: Optional[CompletionContextParam] = None,
    memory: Optional[Union[Memory, List[Memory]]] = None,
    memory_limit: Optional[int] = None,
    instructor_mode: Optional[CompletionInstructorModeParam] = None,
    mode: Optional[CompletionInstructorModeParam] = None,
    response_model: Optional[CompletionResponseModelParam] = None,
    response_format: Optional[CompletionResponseModelParam] = None,
    tools: Optional[List[CompletionToolsParam]] = None,
    run_tools: Optional[bool] = None,
    tool_choice: Optional[CompletionToolChoiceParam] = None,
    parallel_tool_calls: Optional[bool] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    organization: Optional[str] = None,
    n: Optional[int] = None,
    timeout: Optional[Union[float, str, httpx.Timeout]] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    stream_options: Optional[dict] = None,
    stop=None,
    max_completion_tokens: Optional[int] = None,
    max_tokens: Optional[int] = None,
    modalities: Optional[List[CompletionModalityParam]] = None,
    prediction: Optional[CompletionPredictionContentParam] = None,
    audio: Optional[CompletionAudioParam] = None,
    presence_penalty: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
    logit_bias: Optional[dict] = None,
    user: Optional[str] = None,
    # openai v1.0+ new params
    seed: Optional[int] = None,
    logprobs: Optional[bool] = None,
    top_logprobs: Optional[int] = None,
    deployment_id=None,
    extra_headers: Optional[dict] = None,
    # soon to be deprecated params by OpenAI
    functions: Optional[List] = None,
    function_call: Optional[str] = None,
    # set api_base, api_version, api_key
    api_version: Optional[str] = None,
    model_list: Optional[list] = None,
    stream: Optional[bool] = None,
    return_messages: Optional[bool] = None,
    verbose: Optional[bool] = None,
) -> List[Response]:
    """Creates a batch completion using the LiteLLM `batch_completion` endpoint."""

    from litellm import batch_completion

    if response_model:
        print(
            "[bold]Notice[/bold] - Batch completions default to using LiteLLM `response_format` parameter. Instructor will not be used..."
        )

        response_format = response_model

        if isinstance(response_format, dict):
            response_format = create_dynamic_response_model(response_format)
        elif isinstance(response_format, str):
            response_format = create_dynamic_response_model(response_format)
        elif isinstance(response_format, list):
            response_format = create_dynamic_response_model(response_format)

    # ensure supported batch params are used
    new_tools = warn_unsupported_batch_params(tools, run_tools, stream, response_format)

    if response_format:
        stream = False

    # format messages

    formatted_messages = []

    try:
        for message in messages:
            message = format_messages(message)
            formatted_messages.append(message)

            if context:
                message = add_context_to_messages(message, context)
    except Exception as e:
        raise XNANOException(f"Failed to format messages for batch completion: {e}")

    if verbose:
        console.message(
            f"✅ [green]Successfully formatted {len(formatted_messages)} sets of messages.[/green]"
        )

    if new_tools:
        tools = new_tools

    response = batch_completion(
        model=model,
        messages=formatted_messages,
        functions=functions,
        function_call=function_call,
        response_format=response_format,
        tools=tools,
        tool_choice=tool_choice,
        parallel_tool_calls=parallel_tool_calls,
        api_key=api_key,
        base_url=base_url,
        organization=organization,
        n=n,
        timeout=timeout,
        temperature=temperature,
        top_p=top_p,
        presence_penalty=presence_penalty,
        frequency_penalty=frequency_penalty,
        logit_bias=logit_bias,
        user=user,
        seed=seed,
        logprobs=logprobs,
        top_logprobs=top_logprobs,
        deployment_id=deployment_id,
        extra_headers=extra_headers,
        max_completion_tokens=max_completion_tokens,
        max_tokens=max_tokens,
        modalities=modalities,
        prediction=prediction,
        audio=audio,
        stream=stream,
    )

    if verbose:
        console.message(
            f"✅ [green]Successfully created batch completion job with {len(messages)} sets of messages.[/green]"
        )

    # build structured responses
    if response_format:
        formatted_responses = []

        for response in response:
            formatted_responses.append(
                build_pydantic_model_from_string_dictionary(response, response_format)
            )

        return formatted_responses

    return response


def create_batch_completion_job_with_multiple_models(
    messages: CompletionMessagesParam,
    model: CompletionChatModelsParam = "gpt-4o-mini",
    context: Optional[CompletionContextParam] = None,
    memory: Optional[Union[Memory, List[Memory]]] = None,
    memory_limit: Optional[int] = None,
    instructor_mode: Optional[CompletionInstructorModeParam] = None,
    mode: Optional[CompletionInstructorModeParam] = None,
    response_model: Optional[CompletionResponseModelParam] = None,
    response_format: Optional[CompletionResponseModelParam] = None,
    tools: Optional[List[CompletionToolsParam]] = None,
    run_tools: Optional[bool] = None,
    tool_choice: Optional[CompletionToolChoiceParam] = None,
    parallel_tool_calls: Optional[bool] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    organization: Optional[str] = None,
    n: Optional[int] = None,
    timeout: Optional[Union[float, str, httpx.Timeout]] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    stream_options: Optional[dict] = None,
    stop=None,
    max_completion_tokens: Optional[int] = None,
    max_tokens: Optional[int] = None,
    modalities: Optional[List[CompletionModalityParam]] = None,
    prediction: Optional[CompletionPredictionContentParam] = None,
    audio: Optional[CompletionAudioParam] = None,
    presence_penalty: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
    logit_bias: Optional[dict] = None,
    user: Optional[str] = None,
    # openai v1.0+ new params
    seed: Optional[int] = None,
    logprobs: Optional[bool] = None,
    top_logprobs: Optional[int] = None,
    deployment_id=None,
    extra_headers: Optional[dict] = None,
    # soon to be deprecated params by OpenAI
    functions: Optional[List] = None,
    function_call: Optional[str] = None,
    # set api_base, api_version, api_key
    api_version: Optional[str] = None,
    model_list: Optional[list] = None,
    stream: Optional[bool] = None,
    return_messages: Optional[bool] = None,
    verbose: Optional[bool] = None,
) -> List[Response]:
    """Creates a batch completion using the LiteLLM `batch_completion_models_all_responses` endpoint with multiple models."""

    from litellm import batch_completion_models_all_responses

    if not isinstance(model, list):
        raise XNANOException(
            "Batch completions with multiple models requires a list of models."
        )

    if response_model:
        print(
            "[bold]Notice[/bold] - Batch completions default to using LiteLLM `response_format` parameter. Instructor will not be used..."
        )

        response_format = response_model

        if isinstance(response_format, dict):
            response_format = create_dynamic_response_model(response_format)
        elif isinstance(response_format, str):
            response_format = create_dynamic_response_model(response_format)
        elif isinstance(response_format, list):
            response_format = create_dynamic_response_model(response_format)

    new_tools = warn_unsupported_batch_params(tools, run_tools, stream, response_format)

    if new_tools:
        tools = new_tools

    if response_format:
        stream = False

    # format messages
    try:
        messages = format_messages(messages)

        if context:
            messages = add_context_to_messages(messages, context)
    except Exception as e:
        raise XNANOException(
            f"Failed to format messages for multiple model batch completion: {e}"
        )

    if verbose:
        console.message(
            f"✅ [green]Successfully formatted {len(messages)} messages.[/green]"
        )

    response = batch_completion_models_all_responses(
        models=model,
        messages=messages,
        functions=functions,
        function_call=function_call,
        response_format=response_format,
        tools=tools,
        tool_choice=tool_choice,
        parallel_tool_calls=parallel_tool_calls,
        api_key=api_key,
        base_url=base_url,
        organization=organization,
        n=n,
        timeout=timeout,
        temperature=temperature,
        top_p=top_p,
        presence_penalty=presence_penalty,
        frequency_penalty=frequency_penalty,
        logit_bias=logit_bias,
        user=user,
        seed=seed,
        logprobs=logprobs,
        top_logprobs=top_logprobs,
        deployment_id=deployment_id,
        extra_headers=extra_headers,
        max_completion_tokens=max_completion_tokens,
        max_tokens=max_tokens,
        modalities=modalities,
        prediction=prediction,
        audio=audio,
        stream=stream,
    )

    if verbose:
        console.message(
            f"✅ [green]Successfully created batch completion job with {len(messages)} sets of messages and {len(model)} models.[/green]"
        )

    # build structured responses
    if response_format:
        formatted_responses = []

        for response in response:
            formatted_responses.append(
                build_pydantic_model_from_string_dictionary(response, response_format)
            )

        return formatted_responses

    return response
