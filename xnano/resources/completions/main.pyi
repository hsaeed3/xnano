from ...types.embeddings.memory import Memory
from ...types.completions.params import (
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
from ...types.completions.responses import Response
import httpx
from typing import List, Optional, Union

async def async_completion(
    messages: CompletionMessagesParam,
    model: CompletionChatModelsParam = "gpt-4o-mini",
    context: Optional[CompletionContextParam] = None,
    memory: Optional[Union[Memory, List[Memory]]] = None,
    memory_limit: Optional[int] = None,
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
) -> Response:
    """
    ### Generate a completion using any LiteLLM supported model, with incredibly easy to access features.

    ---

    - Pass messages as a string or list of messages.
    - Structured outputs with Pydantic.
      - Pass strings or lists to `response_model` for easy dynamic pydantic model creation.
    - Generate tools by passing a string as a tool!
      - Using something like `tools=["run_cli_command"]` will safely generate a tool that can be used to run arbitrary CLI commands.
    - Built in code execution and tool calling.
      - Use `run_tools=True` to execute code or call tools.
    - Pass context easily using `context` or `memory`.
    - Supports the xnano memory client with the `memory` argument.
    - Streaming

    ---

    ## Examples:

    ### Generic completion

    ```python
    completion(messages="Hello, how are you?")
    ```

    ### Passing messages as a list

    ```python
    completion(messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "What is the capital of France?"}])
    ```

    ### Using a Pydantic model as a response model

    ```python
    completion(messages="What is the capital of France?", response_model=MyModel)
    ```

    ### Using strings and lists as response models

    ```python
    completion(messages="What is the capital of France?", response_model="capital : str") # or just `response_model="capital"`
    ```

    ### Using tools

    ```python
    def some_tool():
        ...

    class MyModel(BaseModel):
        ...

    completion(..., tools=[some_tool, MyModel])
    ```

    ### Executing tools

    ```python
    completion(..., tools = [...],run_tools=True)
    ```

    ### Generating tools

    ```python
    completion(..., tools = ["run_cli_command"], run_tools=True)
    ```

    ### Using context or memory

    ```python
    completion(..., memory = [...], context = "some context")
    ```

    ---

    Args:

        messages (CompletionMessagesParam): The messages to generate a completion for. (string, list, or list of lists)
        model (CompletionChatModelsParam): The model to use for the completion.
        context (CompletionContextParam): The context to use for the completion.
        memory (Union[Memory, List[Memory]]): The memory to use for the completion.
        memory_limit (int): The memory limit to use for the completion.
        mode (CompletionInstructorModeParam): The mode to use for the completion.
        response_model (CompletionResponseModelParam): The response model to use for the completion.
        response_format (CompletionResponseModelParam): The response format to use for the completion.
        tools (List[CompletionToolsParam]): The tools to use for the completion.
        run_tools (bool): Whether to run the tools.
        tool_choice (CompletionToolChoiceParam): The tool choice to use for the completion.
        parallel_tool_calls (bool): Whether to use parallel tool calls.
        api_key (str): The API key to use for the completion.
        base_url (str): The base URL to use for the completion.
        organization (str): The organization to use for the completion.
        n (int): The number of completions to generate.
        timeout (Union[float, str, httpx.Timeout]): The timeout to use for the completion.
        temperature (float): The temperature to use for the completion.
        top_p (float): The top P to use for the completion.
        stream_options (dict): The stream options to use for the completion.
        stop (str): The stop sequence to use for the completion.
        max_completion_tokens (int): The maximum number of completion tokens to use for the completion.
        max_tokens (int): The maximum number of tokens to use for the completion.
        modalities (List[CompletionModalityParam]): The modalities to use for the completion.
        prediction (CompletionPredictionContentParam): The prediction content to use for the completion.
        audio (CompletionAudioParam): The audio to use for the completion.
        presence_penalty (float): The presence penalty to use for the completion.
        frequency_penalty (float): The frequency penalty to use for the completion.
        logit_bias (dict): The logit bias to use for the completion.
        user (str): The user to use for the completion.
        seed (int): The seed to use for the completion.
        logprobs (bool): Whether to return the log probabilities.
        top_logprobs (int): The top log probabilities to use for the completion.
        deployment_id (str): The deployment ID to use for the completion.
        extra_headers (dict): The extra headers to use for the completion.
        functions (List): The functions to use for the completion.
        function_call (str): The function call to use for the completion.
        api_version (str): The API version to use for the completion.
        model_list (list): The model list to use for the completion.
        stream (bool): Whether to stream the completion.
        return_messages (bool): Whether to return the messages.
        verbose (bool): Whether to show verbose output.
    """
    ...

def completion(
    messages: CompletionMessagesParam,
    model: CompletionChatModelsParam = "gpt-4o-mini",
    context: Optional[CompletionContextParam] = None,
    memory: Optional[Union[Memory, List[Memory]]] = None,
    memory_limit: Optional[int] = None,
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
) -> Response:
    """
    ### Generate a completion using any LiteLLM supported model, with incredibly easy to access features.

    ---

    - Pass messages as a string or list of messages.
    - Structured outputs with Pydantic.
      - Pass strings or lists to `response_model` for easy dynamic pydantic model creation.
    - Generate tools by passing a string as a tool!
      - Using something like `tools=["run_cli_command"]` will safely generate a tool that can be used to run arbitrary CLI commands.
    - Built in code execution and tool calling.
      - Use `run_tools=True` to execute code or call tools.
    - Pass context easily using `context` or `memory`.
    - Supports the xnano memory client with the `memory` argument.
    - Streaming

    ---

    ## Examples:

    ### Generic completion

    ```python
    completion(messages="Hello, how are you?")
    ```

    ### Passing messages as a list

    ```python
    completion(messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "What is the capital of France?"}])
    ```

    ### Using a Pydantic model as a response model

    ```python
    completion(messages="What is the capital of France?", response_model=MyModel)
    ```

    ### Using strings and lists as response models

    ```python
    completion(messages="What is the capital of France?", response_model="capital : str") # or just `response_model="capital"`
    ```

    ### Using tools

    ```python
    def some_tool():
        ...

    class MyModel(BaseModel):
        ...

    completion(..., tools=[some_tool, MyModel])
    ```

    ### Executing tools

    ```python
    completion(..., tools = [...],run_tools=True)
    ```

    ### Generating tools

    ```python
    completion(..., tools = ["run_cli_command"], run_tools=True)
    ```

    ### Using context or memory

    ```python
    completion(..., memory = [...], context = "some context")
    ```

    ---

    Args:

        messages (CompletionMessagesParam): The messages to generate a completion for. (string, list, or list of lists)
        model (CompletionChatModelsParam): The model to use for the completion.
        context (CompletionContextParam): The context to use for the completion.
        memory (Union[Memory, List[Memory]]): The memory to use for the completion.
        memory_limit (int): The memory limit to use for the completion.
        mode (CompletionInstructorModeParam): The mode to use for the completion.
        response_model (CompletionResponseModelParam): The response model to use for the completion.
        response_format (CompletionResponseModelParam): The response format to use for the completion.
        tools (List[CompletionToolsParam]): The tools to use for the completion.
        run_tools (bool): Whether to run the tools.
        tool_choice (CompletionToolChoiceParam): The tool choice to use for the completion.
        parallel_tool_calls (bool): Whether to use parallel tool calls.
        api_key (str): The API key to use for the completion.
        base_url (str): The base URL to use for the completion.
        organization (str): The organization to use for the completion.
        n (int): The number of completions to generate.
        timeout (Union[float, str, httpx.Timeout]): The timeout to use for the completion.
        temperature (float): The temperature to use for the completion.
        top_p (float): The top P to use for the completion.
        stream_options (dict): The stream options to use for the completion.
        stop (str): The stop sequence to use for the completion.
        max_completion_tokens (int): The maximum number of completion tokens to use for the completion.
        max_tokens (int): The maximum number of tokens to use for the completion.
        modalities (List[CompletionModalityParam]): The modalities to use for the completion.
        prediction (CompletionPredictionContentParam): The prediction content to use for the completion.
        audio (CompletionAudioParam): The audio to use for the completion.
        presence_penalty (float): The presence penalty to use for the completion.
        frequency_penalty (float): The frequency penalty to use for the completion.
        logit_bias (dict): The logit bias to use for the completion.
        user (str): The user to use for the completion.
        seed (int): The seed to use for the completion.
        logprobs (bool): Whether to return the log probabilities.
        top_logprobs (int): The top log probabilities to use for the completion.
        deployment_id (str): The deployment ID to use for the completion.
        extra_headers (dict): The extra headers to use for the completion.
        functions (List): The functions to use for the completion.
        function_call (str): The function call to use for the completion.
        api_version (str): The API version to use for the completion.
        model_list (list): The model list to use for the completion.
        stream (bool): Whether to stream the completion.
        return_messages (bool): Whether to return the messages.
        verbose (bool): Whether to show verbose output.
    """
    ...
