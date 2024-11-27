from pydantic import BaseModel as PydanticBaseModel, create_model, Field
import httpx
from textwrap import dedent
from copy import deepcopy
from typing import (
    Type,
    TypeVar,
    Union,
    Dict,
    Any,
    Optional,
    List,
    overload,
)
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
from ...types.models.base_model_generation_process import BaseModelGenerationProcess
from ...types.models.mixin import BaseModelMixin as BaseModelMixinType
from pydantic import BaseModel as PydanticBaseModel
from ...types.completions._openai import ChatCompletion

class GenerativeModel(BaseModelMixinType, PydanticBaseModel):
    ...

    @overload
    async def model_async_completion(
        cls,
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
        loader: Optional[bool] = True,
        verbose: Optional[bool] = None,
    ) -> Union[
        ChatCompletion,
        BaseModelMixinType,
        List[BaseModelMixinType],
        List[ChatCompletion],
    ]: ...
    @overload
    async def model_async_completion(
        self,
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
        loader: Optional[bool] = True,
        verbose: Optional[bool] = None,
    ) -> Union[
        ChatCompletion,
        BaseModelMixinType,
        List[BaseModelMixinType],
        List[ChatCompletion],
    ]: ...
    @overload
    def model_completion(
        cls,
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
        loader: Optional[bool] = True,
        verbose: Optional[bool] = None,
    ) -> Union[
        ChatCompletion,
        BaseModelMixinType,
        List[BaseModelMixinType],
        List[ChatCompletion],
    ]: ...
    @overload
    def model_completion(
        self,
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
        loader: Optional[bool] = True,
        verbose: Optional[bool] = None,
    ) -> Union[
        ChatCompletion,
        BaseModelMixinType,
        List[BaseModelMixinType],
        List[ChatCompletion],
    ]: ...
    @overload
    def model_generate(
        cls,
        messages: CompletionMessagesParam = "",
        model: CompletionChatModelsParam = "gpt-4o-mini",
        process: BaseModelGenerationProcess = "batch",
        n: Optional[int] = 1,
        fields: Optional[List[str]] = None,
        regenerate: Optional[bool] = None,
        context: Optional[CompletionContextParam] = None,
        memory: Optional[Union[Memory, List[Memory]]] = None,
        memory_limit: Optional[int] = None,
        mode: Optional[CompletionInstructorModeParam] = None,
        tools: Optional[CompletionToolsParam] = None,
        run_tools: Optional[bool] = None,
        tool_choice: Optional[CompletionToolChoiceParam] = None,
        parallel_tool_calls: Optional[bool] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        timeout: Optional[Union[float, str, httpx.Timeout]] = None,
        temperature: Optional[float] = 0.7,
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
        seed: Optional[int] = None,
        logprobs: Optional[bool] = None,
        top_logprobs: Optional[int] = None,
        deployment_id=None,
        extra_headers: Optional[dict] = None,
        functions: Optional[List] = None,
        function_call: Optional[str] = None,
        api_version: Optional[str] = None,
        model_list: Optional[list] = None,
        stream: Optional[bool] = None,
        loader: Optional[bool] = True,
        verbose: Optional[bool] = None,
    ) -> Union[BaseModelMixinType, List[BaseModelMixinType]]: ...
    @overload
    def model_generate(
        self,
        messages: CompletionMessagesParam = "",
        model: CompletionChatModelsParam = "gpt-4o-mini",
        process: BaseModelGenerationProcess = "batch",
        n: Optional[int] = 1,
        fields: Optional[List[str]] = None,
        regenerate: Optional[bool] = None,
        context: Optional[CompletionContextParam] = None,
        memory: Optional[Union[Memory, List[Memory]]] = None,
        memory_limit: Optional[int] = None,
        mode: Optional[CompletionInstructorModeParam] = None,
        tools: Optional[CompletionToolsParam] = None,
        run_tools: Optional[bool] = None,
        tool_choice: Optional[CompletionToolChoiceParam] = None,
        parallel_tool_calls: Optional[bool] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        timeout: Optional[Union[float, str, httpx.Timeout]] = None,
        temperature: Optional[float] = 0.7,
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
        seed: Optional[int] = None,
        logprobs: Optional[bool] = None,
        top_logprobs: Optional[int] = None,
        deployment_id=None,
        extra_headers: Optional[dict] = None,
        functions: Optional[List] = None,
        function_call: Optional[str] = None,
        api_version: Optional[str] = None,
        model_list: Optional[list] = None,
        stream: Optional[bool] = None,
        loader: Optional[bool] = True,
        verbose: Optional[bool] = None,
    ) -> Union[BaseModelMixinType, List[BaseModelMixinType]]:
        ...
        """
        Generate or regenerate a full model or instance(s) of the model using LLM completion.
        Supports batching, multiple generations, specific field generation, and more.

        ## Examples:

        ### Generating a full model

        ```python
        from xnano import BaseModel

        class MyModel(BaseModel):
            name: str

        print(MyModel.model_generate(n=3))
        ```

        ### Generating a specific field

        ```python
        print(MyModel.model_generate(fields=["name"]))
        ```

        ### Regenerating a field

        ```python
        print(MyModel.model_generate(regenerate=True, fields=["name"]))
        ```

        Args:
            messages (CompletionMessagesParam): The messages to generate a completion for.
            model (CompletionChatModelsParam): The model to use for the completion.
            process (BaseModelGenerationProcess): The generation process to use for the completion.
            n (int): The number of completions to generate.
            fields (List[str]): The fields to generate.
            regenerate (bool): Whether to regenerate the fields.
            context (CompletionContextParam): The context to use for the completion.
            memory (Union[Memory, List[Memory]]): The memory to use for the completion.
            memory_limit (int): The memory limit to use for the completion.
            mode (CompletionInstructorModeParam): The mode to use for the completion.
            tools (CompletionToolsParam): The tools to use for the completion.
            run_tools (bool): Whether to run the tools.
            tool_choice (CompletionToolChoiceParam): The tool choice to use for the completion.
            parallel_tool_calls (bool): Whether to use parallel tool calls.
            api_key (str): The API key to use for the completion.
            base_url (str): The base URL to use for the completion.
            organization (str): The organization to use for the completion.
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
            loader (bool): Whether to show a loader.
            verbose (bool): Whether to show verbose output.
        """

    @overload
    async def model_async_generate(
        cls,
        messages: CompletionMessagesParam = "",
        model: CompletionChatModelsParam = "gpt-4o-mini",
        process: BaseModelGenerationProcess = "batch",
        n: Optional[int] = 1,
        fields: Optional[List[str]] = None,
        regenerate: Optional[bool] = None,
        context: Optional[CompletionContextParam] = None,
        memory: Optional[Union[Memory, List[Memory]]] = None,
        memory_limit: Optional[int] = None,
        mode: Optional[CompletionInstructorModeParam] = None,
        tools: Optional[CompletionToolsParam] = None,
        run_tools: Optional[bool] = None,
        tool_choice: Optional[CompletionToolChoiceParam] = None,
        parallel_tool_calls: Optional[bool] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        timeout: Optional[Union[float, str, httpx.Timeout]] = None,
        temperature: Optional[float] = 0.7,
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
        seed: Optional[int] = None,
        logprobs: Optional[bool] = None,
        top_logprobs: Optional[int] = None,
        deployment_id=None,
        extra_headers: Optional[dict] = None,
        functions: Optional[List] = None,
        function_call: Optional[str] = None,
        api_version: Optional[str] = None,
        model_list: Optional[list] = None,
        stream: Optional[bool] = None,
        loader: Optional[bool] = True,
        verbose: Optional[bool] = None,
    ) -> Union[BaseModelMixinType, List[BaseModelMixinType]]:
        ...
        """
        Generate or regenerate a full model or instance(s) of the model using LLM completion.
        Supports batching, multiple generations, specific field generation, and more.

        ## Examples:

        ### Generating a full model

        ```python
        from xnano import BaseModel

        class MyModel(BaseModel):
            name: str

        print(MyModel.model_generate(n=3))
        ```

        ### Generating a specific field

        ```python
        print(MyModel.model_generate(fields=["name"]))
        ```

        ### Regenerating a field

        ```python
        print(MyModel.model_generate(regenerate=True, fields=["name"]))
        ```

        Args:
            messages (CompletionMessagesParam): The messages to generate a completion for.
            model (CompletionChatModelsParam): The model to use for the completion.
            process (BaseModelGenerationProcess): The generation process to use for the completion.
            n (int): The number of completions to generate.
            fields (List[str]): The fields to generate.
            regenerate (bool): Whether to regenerate the fields.
            context (CompletionContextParam): The context to use for the completion.
            memory (Union[Memory, List[Memory]]): The memory to use for the completion.
            memory_limit (int): The memory limit to use for the completion.
            mode (CompletionInstructorModeParam): The mode to use for the completion.
            tools (CompletionToolsParam): The tools to use for the completion.
            run_tools (bool): Whether to run the tools.
            tool_choice (CompletionToolChoiceParam): The tool choice to use for the completion.
            parallel_tool_calls (bool): Whether to use parallel tool calls.
            api_key (str): The API key to use for the completion.
            base_url (str): The base URL to use for the completion.
            organization (str): The organization to use for the completion.
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
            loader (bool): Whether to show a loader.
            verbose (bool): Whether to show verbose output.
        """

    @overload
    async def model_async_generate(
        self,
        messages: CompletionMessagesParam = "",
        model: CompletionChatModelsParam = "gpt-4o-mini",
        process: BaseModelGenerationProcess = "batch",
        n: Optional[int] = 1,
        fields: Optional[List[str]] = None,
        regenerate: Optional[bool] = None,
        context: Optional[CompletionContextParam] = None,
        memory: Optional[Union[Memory, List[Memory]]] = None,
        memory_limit: Optional[int] = None,
        mode: Optional[CompletionInstructorModeParam] = None,
        tools: Optional[CompletionToolsParam] = None,
        run_tools: Optional[bool] = None,
        tool_choice: Optional[CompletionToolChoiceParam] = None,
        parallel_tool_calls: Optional[bool] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        timeout: Optional[Union[float, str, httpx.Timeout]] = None,
        temperature: Optional[float] = 0.7,
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
        seed: Optional[int] = None,
        logprobs: Optional[bool] = None,
        top_logprobs: Optional[int] = None,
        deployment_id=None,
        extra_headers: Optional[dict] = None,
        functions: Optional[List] = None,
        function_call: Optional[str] = None,
        api_version: Optional[str] = None,
        model_list: Optional[list] = None,
        stream: Optional[bool] = None,
        loader: Optional[bool] = True,
        verbose: Optional[bool] = None,
    ) -> Union[BaseModelMixinType, List[BaseModelMixinType]]: ...

# -------------------------------------------------------------------------------------------------
# patch
# -------------------------------------------------------------------------------------------------

def patch(
    model: Union[Type[PydanticBaseModel], PydanticBaseModel],
) -> Union[Type[GenerativeModel], GenerativeModel]:
    """
    A function or decorator that patches a Pydantic BaseModel class or instance to build in xnano completions. Either
    run the function or decorate a class, or run the function on an instance.

    ### Examples:

    ```python
    from xnano import patch
    from pydantic import BaseModel

    @patch
    class MyModel(BaseModel):
        ...
    ```

    or

    ```python
    from xnano import patch
    from pydantic import BaseModel

    model = MyModel()
    patched_model = patch(model)
    ```

    Args:
        model: A Pydantic BaseModel class or instance.

    Returns:
        A patched Pydantic BaseModel class or instance.
    """
    ...

def unpatch(
    model: Union[Type[GenerativeModel], GenerativeModel, Type[PydanticBaseModel], PydanticBaseModel],
) -> Union[Type[PydanticBaseModel], PydanticBaseModel]:
    """
    A function that unpatches a patched Pydantic BaseModel class or instance.

    ### Examples:

    ```python
    from xnano import unpatch
    from pydantic import BaseModel

    @patch
    class MyModel(BaseModel):
        ...

    unpatched_model = unpatch(MyModel)
    ```

    Args:
        model: A patched Pydantic BaseModel class or instance.

    Returns:
        A Pydantic BaseModel class or instance.
    """
    ...
