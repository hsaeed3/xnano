# basemodel type

from pydantic import BaseModel as PydanticBaseModel
import httpx
from typing import TypeVar, Union, Optional, List, overload
from abc import abstractmethod, ABC

from .base_model_generation_process import BaseModelGenerationProcess
from ..embeddings.memory import Memory
from ..completions.params import (
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
from ..completions._openai import ChatCompletion


# typevar
BMM = TypeVar("BMM", bound="BaseModelMixin")


class BaseModelMixin(ABC):
    ...

    @abstractmethod
    def model_completion(
        cls_or_self,
        messages: CompletionMessagesParam,
        model: CompletionChatModelsParam = "gpt-4o-mini",
        context: Optional[CompletionContextParam] = None,
        memory: Optional[Union[Memory, List[Memory]]] = None,
        memory_limit: Optional[int] = None,
        mode: Optional[CompletionInstructorModeParam] = None,
        response_model: Optional[CompletionResponseModelParam] = None,
        response_format: Optional[CompletionResponseModelParam] = None,
        tools: Optional[CompletionToolsParam] = None,
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
    ) -> Union[
        BMM,
        List[BMM],
        ChatCompletion,
        List[ChatCompletion],
    ]:
        """
        Generates a chat completion for the model.

        Args:
            messages (MessageType): Messages to send to the LLM
            model (ChatModel): Model to use for generation
            context (Optional[Context]): Additional context to provide
            embeddings (Optional[Union[Embeddings, List[Embeddings]]]): Embeddings to use for generation
            embeddings_limit (Optional[int]): Maximum number of embeddings to use
            mode (Optional[InstructorMode]): Instructor mode to use for generation
            response_model (Optional[ResponseModelType]): Response model to use for generation
            response_format (Optional[ResponseModelType]): Response format to use for generation
            tools (Optional[List[ToolType]]): Tools to use for generation
            run_tools (Optional[bool]): Whether to run tools for generation
            tool_choice (Optional[ToolChoice]): Tool choice to use for generation
            parallel_tool_calls (Optional[bool]): Whether to allow parallel tool calls for generation
            api_key (Optional[str]): API key to use for generation
            base_url (Optional[str]): Base URL to use for generation
            organization (Optional[str]): Organization to use for generation
            n (Optional[int]): Number of generations to run
            timeout (Optional[Union[float, str, httpx.Timeout]]): Timeout to use for generation
            temperature (Optional[float]): Temperature to use for generation
            top_p (Optional[float]): Top P to use for generation
            stream_options (Optional[dict]): Stream options to use for generation
            stop (Optional[str]): Stop sequence to use for generation
            max_completion_tokens (Optional[int]): Maximum number of completion tokens to use for generation
            max_tokens (Optional[int]): Maximum number of tokens to use for generation
            modalities (Optional[List[ChatCompletionModality]]): Modalities to use for generation
            prediction (Optional[ChatCompletionPredictionContentParam]): Prediction content parameter to use for generation
            audio (Optional[ChatCompletionAudioParam]): Audio parameter to use for generation
            presence_penalty (Optional[float]): Presence penalty to use for generation
            frequency_penalty (Optional[float]): Frequency penalty to use for generation
            logit_bias (Optional[dict]): Logit bias to use for generation
            user (Optional[str]): User to use for generation
            seed (Optional[int]): Seed to use for generation
            logprobs (Optional[bool]): Logprobs to use for generation
            top_logprobs (Optional[int]): Top logprobs to use for generation
            deployment_id (Optional[str]): Deployment ID to use for generation
            extra_headers (Optional[dict]): Extra headers to use for generation
            functions (Optional[List]): Functions to use for generation
            function_call (Optional[str]): Function call to use for generation
            api_version (Optional[str]): API version to use for generation
            model_list (Optional[list]): Model list to use for generation
            stream (Optional[bool]): Whether to stream the generation
            loader (Optional[bool]): Whether to use a loader for generation
            verbose (Optional[bool]): Whether to use verbose logging for generation

        Returns:
            Union[BMM, List[BMM], Response, List[Response]]: Generated completion(s)
        """

    @abstractmethod
    async def model_acompletion(
        cls_or_self,
        messages: CompletionMessagesParam,
        model: CompletionChatModelsParam = "gpt-4o-mini",
        context: Optional[CompletionContextParam] = None,
        memory: Optional[Union[Memory, List[Memory]]] = None,
        memory_limit: Optional[int] = None,
        mode: Optional[CompletionInstructorModeParam] = None,
        response_model: Optional[CompletionResponseModelParam] = None,
        response_format: Optional[CompletionResponseModelParam] = None,
        tools: Optional[CompletionToolsParam] = None,
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
    ) -> Union[
        BMM,
        List[BMM],
        ChatCompletion,
        List[ChatCompletion],
    ]:
        """
        Asynchronously generates a chat completion for the model.

        Args:
            messages (MessageType): Messages to send to the LLM
            model (ChatModel): Model to use for generation
            context (Optional[Context]): Additional context to provide
            embeddings (Optional[Union[Embeddings, List[Embeddings]]]): Embeddings to use for generation
            embeddings_limit (Optional[int]): Maximum number of embeddings to use
            mode (Optional[InstructorMode]): Instructor mode to use for generation
            response_model (Optional[ResponseModelType]): Response model to use for generation
            response_format (Optional[ResponseModelType]): Response format to use for generation
            tools (Optional[List[ToolType]]): Tools to use for generation
            run_tools (Optional[bool]): Whether to run tools for generation
            tool_choice (Optional[ToolChoice]): Tool choice to use for generation
            parallel_tool_calls (Optional[bool]): Whether to allow parallel tool calls for generation
            api_key (Optional[str]): API key to use for generation
            base_url (Optional[str]): Base URL to use for generation
            organization (Optional[str]): Organization to use for generation
            n (Optional[int]): Number of generations to run
            timeout (Optional[Union[float, str, httpx.Timeout]]): Timeout to use for generation
            temperature (Optional[float]): Temperature to use for generation
            top_p (Optional[float]): Top P to use for generation
            stream_options (Optional[dict]): Stream options to use for generation
            stop (Optional[str]): Stop sequence to use for generation
            max_completion_tokens (Optional[int]): Maximum number of completion tokens to use for generation
            max_tokens (Optional[int]): Maximum number of tokens to use for generation
            modalities (Optional[List[ChatCompletionModality]]): Modalities to use for generation
            prediction (Optional[ChatCompletionPredictionContentParam]): Prediction content parameter to use for generation
            audio (Optional[ChatCompletionAudioParam]): Audio parameter to use for generation
            presence_penalty (Optional[float]): Presence penalty to use for generation
            frequency_penalty (Optional[float]): Frequency penalty to use for generation
            logit_bias (Optional[dict]): Logit bias to use for generation
            user (Optional[str]): User to use for generation
            seed (Optional[int]): Seed to use for generation
            logprobs (Optional[bool]): Logprobs to use for generation
            top_logprobs (Optional[int]): Top logprobs to use for generation
            deployment_id (Optional[str]): Deployment ID to use for generation
            extra_headers (Optional[dict]): Extra headers to use for generation
            functions (Optional[List]): Functions to use for generation
            function_call (Optional[str]): Function call to use for generation
            api_version (Optional[str]): API version to use for generation
            model_list (Optional[list]): Model list to use for generation
            stream (Optional[bool]): Whether to stream the generation
            loader (Optional[bool]): Whether to use a loader for generation
            verbose (Optional[bool]): Whether to use verbose logging for generation

        Returns:
            Union[T, List[T], ChatCompletion, List[ChatCompletion]]: Generated completion(s)
        """

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
    ) -> Union[BMM, List[BMM]]: ...

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
    ) -> Union[BMM, List[BMM]]: ...

    @abstractmethod
    @overload
    def model_generate(
        cls_or_self,
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
    ) -> Union[BMM, List[BMM]]:
        """Generates instance(s) of the model using LLM completion.

        Supports two generation processes:
        - batch: Generates all instances at once
        - sequential: Generates instances one at a time, field by field

        Args:
            messages (MessageType): Messages to send to the LLM
            model (ChatModel): Model to use for generation
            context (Optional[Context]): Additional context to provide
            process (BaseModelGenerationProcess): Generation process type ("batch" or "sequential")
            embeddings (Optional[Union[Embeddings, List[Embeddings]]]): Embeddings to use for generation
            embeddings_limit (Optional[int]): Maximum number of embeddings to use
            mode (Optional[InstructorMode]): Instructor mode to use for generation
            response_model (Optional[ResponseModelType]): Response model to use for generation
            response_format (Optional[ResponseModelType]): Response format to use for generation
            tools (Optional[List[ToolType]]): Tools to use for generation
            run_tools (Optional[bool]): Whether to run tools for generation
            tool_choice (Optional[ToolChoice]): Tool choice to use for generation
            parallel_tool_calls (Optional[bool]): Whether to allow parallel tool calls for generation
            api_key (Optional[str]): API key to use for generation
            base_url (Optional[str]): Base URL to use for generation
            organization (Optional[str]): Organization to use for generation
            n (Optional[int]): Number of generations to run
            timeout (Optional[Union[float, str, httpx.Timeout]]): Timeout to use for generation
            temperature (Optional[float]): Temperature to use for generation
            top_p (Optional[float]): Top P to use for generation
            stream_options (Optional[dict]): Stream options to use for generation
            stop (Optional[str]): Stop sequence to use for generation
            max_completion_tokens (Optional[int]): Maximum number of completion tokens to use for generation
            max_tokens (Optional[int]): Maximum number of tokens to use for generation
            modalities (Optional[List[ChatCompletionModality]]): Modalities to use for generation
            prediction (Optional[ChatCompletionPredictionContentParam]): Prediction content parameter to use for generation
            audio (Optional[ChatCompletionAudioParam]): Audio parameter to use for generation
            presence_penalty (Optional[float]): Presence penalty to use for generation
            frequency_penalty (Optional[float]): Frequency penalty to use for generation
            logit_bias (Optional[dict]): Logit bias to use for generation
            user (Optional[str]): User to use for generation
            seed (Optional[int]): Seed to use for generation
            logprobs (Optional[bool]): Logprobs to use for generation
            top_logprobs (Optional[int]): Top logprobs to use for generation
            deployment_id (Optional[str]): Deployment ID to use for generation
            extra_headers (Optional[dict]): Extra headers to use for generation
            functions (Optional[List]): Functions to use for generation
            function_call (Optional[str]): Function call to use for generation
            api_version (Optional[str]): API version to use for generation
            model_list (Optional[list]): Model list to use for generation
            stream (Optional[bool]): Whether to stream the generation
            loader (Optional[bool]): Whether to use a loader for generation
            verbose (Optional[bool]): Whether to use verbose logging for generation

        Returns:
            Union[T, List[T], ChatCompletion, List[ChatCompletion]]: Generated completion(s)
        """

    @abstractmethod
    async def model_agenerate(
        cls_or_self,
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
    ) -> Union[BMM, List[BMM]]:
        """Asynchronously generates instance(s) of the model using LLM completion.

        Args:
            messages (MessageType): Messages to send to the LLM
            model (ChatModel): Model to use for generation
            context (Optional[Context]): Additional context to provide
            process (BaseModelGenerationProcess): Generation process type ("batch" or "sequential")
            embeddings (Optional[Union[Embeddings, List[Embeddings]]]): Embeddings to use for generation
            embeddings_limit (Optional[int]): Maximum number of embeddings to use
            mode (Optional[InstructorMode]): Instructor mode to use for generation
            response_model (Optional[ResponseModelType]): Response model to use for generation
            response_format (Optional[ResponseModelType]): Response format to use for generation
            tools (Optional[List[ToolType]]): Tools to use for generation
            run_tools (Optional[bool]): Whether to run tools for generation
            tool_choice (Optional[ToolChoice]): Tool choice to use for generation
            parallel_tool_calls (Optional[bool]): Whether to allow parallel tool calls for generation
            api_key (Optional[str]): API key to use for generation
            base_url (Optional[str]): Base URL to use for generation
            organization (Optional[str]): Organization to use for generation
            n (Optional[int]): Number of generations to run
            timeout (Optional[Union[float, str, httpx.Timeout]]): Timeout to use for generation
            temperature (Optional[float]): Temperature to use for generation
            top_p (Optional[float]): Top P to use for generation
            stream_options (Optional[dict]): Stream options to use for generation
            stop (Optional[str]): Stop sequence to use for generation
            max_completion_tokens (Optional[int]): Maximum number of completion tokens to use for generation
            max_tokens (Optional[int]): Maximum number of tokens to use for generation
            modalities (Optional[List[ChatCompletionModality]]): Modalities to use for generation
            prediction (Optional[ChatCompletionPredictionContentParam]): Prediction content parameter to use for generation
            audio (Optional[ChatCompletionAudioParam]): Audio parameter to use for generation
            presence_penalty (Optional[float]): Presence penalty to use for generation
            frequency_penalty (Optional[float]): Frequency penalty to use for generation
            logit_bias (Optional[dict]): Logit bias to use for generation
            user (Optional[str]): User to use for generation
            seed (Optional[int]): Seed to use for generation
            logprobs (Optional[bool]): Logprobs to use for generation
            top_logprobs (Optional[int]): Top logprobs to use for generation
            deployment_id (Optional[str]): Deployment ID to use for generation
            extra_headers (Optional[dict]): Extra headers to use for generation
            functions (Optional[List]): Functions to use for generation
            function_call (Optional[str]): Function call to use for generation
            api_version (Optional[str]): API version to use for generation
            model_list (Optional[list]): Model list to use for generation
            stream (Optional[bool]): Whether to stream the generation
            loader (Optional[bool]): Whether to use a loader for generation
            verbose (Optional[bool]): Whether to use verbose logging for generation

        Returns:
            Union[T, List[T], ChatCompletion, List[ChatCompletion]]: Generated completion(s)
        """
