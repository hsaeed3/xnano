# basemodel
# llm extension for pydantic models

from pydantic import BaseModel as PydanticBaseModel, create_model, Field

from ...lib import console, XNANOException

import json
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
    Tuple,
    Callable,
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
from ...types.completions._openai import ChatCompletion


# -------------------------------------------------------------------------------------------------
# helper class for class & instance funcs
# -------------------------------------------------------------------------------------------------


class function_handler:
    def __init__(self, func):
        self.func = func

    # helper for getting class or instance details
    def __get__(
        self, obj: Optional[Type] = None, cls: Optional[Type] = None
    ) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.func(obj or cls, *args, **kwargs)

        return wrapper


# -------------------------------------------------------------------------------------------------
# MIXIN
# -------------------------------------------------------------------------------------------------


class BaseModelMixin:
    ...

    @function_handler
    def _get_model_by_fields(cls_or_self, fields: List[str]) -> Type[PydanticBaseModel]:
        """
        Builds a model using the original model and only the specified fields.

        Args:
            fields (List[str]): List of field names to include in the new model

        Returns:
            Type[BaseModel]: A new Pydantic model containing only the specified fields

        Raises:
            XNANOException: If field validation fails or model creation fails
            ValueError: If specified fields don't exist in the original model
        """
        try:
            # Get the original model (handle both class and instance cases)
            original_model = (
                cls_or_self if isinstance(cls_or_self, type) else cls_or_self.__class__
            )
            original_fields = original_model.model_fields  # Adjusted for Pydantic v2

            # Validate that all requested fields exist in the original model
            invalid_fields = set(fields) - set(original_fields.keys())
            if invalid_fields:
                raise ValueError(
                    f"Fields {invalid_fields} do not exist in {original_model.__name__}"
                )

            # Create field definitions for the new model - ONLY for requested fields
            field_definitions = {}
            for field in fields:  # Only iterate through requested fields
                field_info = original_fields[field]
                field_type = field_info.annotation
                default_value = (
                    field_info.default if field_info.default is not None else ...
                )
                field_definitions[field] = (field_type, default_value)

            # Create new model with ONLY the specified fields
            new_model = create_model(
                f"{original_model.__name__}Patch",
                __base__=PydanticBaseModel,
                **field_definitions,
            )

            # Initialize the new model with existing field values if it's an instance
            if not isinstance(cls_or_self, type):
                init_values = {field: getattr(cls_or_self, field) for field in fields}
                return new_model(**init_values)

            return new_model

        except ValueError as ve:
            raise ve
        except Exception as e:
            raise XNANOException(f"Failed to build model by fields: {str(e)}")

    @function_handler
    def _merge_patch_with_cls(
        cls_or_self, fields: List[str], response: PydanticBaseModel
    ) -> PydanticBaseModel:
        """Merges only the new values from the patch with the original model"""
        try:
            response_data = response.model_dump()
            return cls_or_self.model_validate(response_data)
        except Exception as e:
            raise XNANOException(f"Failed to merge patch with class: {str(e)}")

    @function_handler
    def _get_model_by_none_fields(
        cls_or_self,
    ) -> Tuple[str, Union[Type[PydanticBaseModel], None]]:
        """Builds a model using the original model and only the fields with None values"""
        try:
            original_model = (
                cls_or_self if isinstance(cls_or_self, type) else cls_or_self.__class__
            )
            original_fields = original_model.__annotations__

            # Identify fields with None values
            none_fields = [
                field
                for field in original_fields
                if getattr(cls_or_self, field, None) is None
            ]

            # If all fields have values, return the original model
            if not none_fields:
                return cls_or_self._get_context(), type(cls_or_self)

            # Use _get_patch_context to create context and model with only None fields
            return cls_or_self._get_patch_context(none_fields)

        except Exception as e:
            raise XNANOException(f"Failed to build model by none fields: {str(e)}")

    # builds context for patch
    @function_handler
    def _get_patch_context(
        cls_or_self, fields: List[str]
    ) -> Tuple[str, Type[PydanticBaseModel]]:
        """Builds a message to describe the patch if model_generate() or model_agenerate() is given specific fields"""

        try:
            new_model = cls_or_self._get_model_by_fields(fields)
            details = cls_or_self._get_details()

            if details["type"] == "instance":
                context = f"""
                You are building a patch for the following values:
                {json.dumps({field: getattr(new_model, field) for field in fields})}
                """
            else:
                context = f"""
                You are building a patch for the following class:
                {details["name"]}
                ---
                {json.dumps(fields)}
                {json.dumps({field: str(details["annotations"][field]) for field in fields})}
                """

            return context, new_model

        except Exception as e:
            raise XNANOException(f"Failed to build patch context: {str(e)}")

    # helper
    @function_handler
    def _get_details(cls_or_self):
        if isinstance(cls_or_self, type):
            # Called on the class itself
            details = {
                "type": "class",
                "name": cls_or_self.__name__,
                "fields": list(cls_or_self.model_fields.keys()),
                "annotations": {
                    k: v.annotation for k, v in cls_or_self.model_fields.items()
                },
                "values": None,
            }
        else:
            # Called on an instance
            details = {
                "type": "instance",
                "name": cls_or_self.__class__.__name__,
                "fields": list(cls_or_self.__class__.model_fields.keys()),
                "annotations": {
                    k: v.annotation
                    for k, v in cls_or_self.__class__.model_fields.items()
                },
                "values": cls_or_self.model_dump(),
            }
        return details

    # ---------------------------------------------------------------------------------------------
    # context builder
    # ---------------------------------------------------------------------------------------------
    @function_handler
    def _get_context(cls_or_self):
        details = cls_or_self._get_details()

        # determine if instance or class
        context_header = "You may be asked about, queried, or instructed to augment or use the following information:"
        context_footer = (
            "Assume the context is relevant to the current conversation. Do not use broad information to answer queries; always try to tailor your response to the specific context."
            "Directly answer or respond to queries using context; there is no need to explain what the context/schema is or how it works.",
            "Items will always be in a JSON schema or format. DO NOT include this information in your responses.",
        )

        if details["type"] == "instance":
            context_body = dedent(f"""
            Context/Instance: {details["name"]}
            ---
            {json.dumps(details["fields"])}
            {json.dumps({k: str(v) for k, v in details["annotations"].items()})}
            ---
            {json.dumps(details["values"])}
            """)
        else:
            context_body = dedent(f"""
            Context/Instance: {details["name"]}
            ---
            {json.dumps(details["fields"])}
            {json.dumps({k: str(v) for k, v in details["annotations"].items()})}
            """)

        return dedent(f"{context_header}\n{context_body}\n{context_footer}")

    # completion methods
    # uses pydantic model as 'RAG' or context
    @function_handler
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
    ]:
        """Generates a chat completion for the model.

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
            modalities (Optional[List[ResponseModality]]): Modalities to use for generation
            prediction (Optional[ResponsePredictionContentParam]): Prediction content parameter to use for generation
            audio (Optional[ResponseAudioParam]): Audio parameter to use for generation
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
            Union[T, List[T], Response, List[Response]]: Generated completion(s)
        """

        from ..completions.main import completion

        details = cls_or_self._get_details()
        model_context = cls_or_self._get_context()

        # build context if context
        if context is None:
            context = model_context
        else:
            context = context + "\n\n" + model_context

        args = {
            "messages": messages,
            "model": model,
            "context": context,
            "memory": memory,
            "memory_limit": memory_limit,
            "mode": mode,
            "response_model": response_model,
            "response_format": response_format,
            "tools": tools,
            "run_tools": run_tools,
            "tool_choice": tool_choice,
            "parallel_tool_calls": parallel_tool_calls,
            "api_key": api_key,
            "base_url": base_url,
            "organization": organization,
            "n": n,
            "timeout": timeout,
            "temperature": temperature,
            "top_p": top_p,
            "stream_options": stream_options,
            "stop": stop,
            "max_completion_tokens": max_completion_tokens,
            "max_tokens": max_tokens,
            "modalities": modalities,
            "prediction": prediction,
            "audio": audio,
            "presence_penalty": presence_penalty,
            "frequency_penalty": frequency_penalty,
            "logit_bias": logit_bias,
            "user": user,
            "seed": seed,
            "logprobs": logprobs,
            "top_logprobs": top_logprobs,
            "deployment_id": deployment_id,
            "extra_headers": extra_headers,
            "functions": functions,
            "function_call": function_call,
            "api_version": api_version,
            "model_list": model_list,
            "stream": stream,
            "verbose": verbose,
        }

        if loader:
            with console.progress(
                f"Generating completion for {str(details['name'])}..."
            ) as progress:
                response = completion(**args)
                return response

        else:
            return completion(**args)

    # async completion
    @function_handler
    async def model_async_completion(
        cls_or_self,
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
            modalities (Optional[List[ResponseModality]]): Modalities to use for generation
            prediction (Optional[ResponsePredictionContentParam]): Prediction content parameter to use for generation
            audio (Optional[ResponseAudioParam]): Audio parameter to use for generation
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
            Union[T, List[T], Response, List[Response]]: Generated completion(s)
        """

        from ..completions.main import async_completion, completion

        details = cls_or_self._get_details()
        model_context = cls_or_self._get_context()

        # build context if context
        if context is None:
            context = model_context
        else:
            context = context + "\n\n" + model_context

        args = {
            "messages": messages,
            "model": model,
            "context": context,
            "memory": memory,
            "memory_limit": memory_limit,
            "mode": mode,
            "response_model": response_model,
            "response_format": response_format,
            "tools": tools,
            "run_tools": run_tools,
            "tool_choice": tool_choice,
            "parallel_tool_calls": parallel_tool_calls,
            "api_key": api_key,
            "base_url": base_url,
            "organization": organization,
            "n": n,
            "timeout": timeout,
            "temperature": temperature,
            "top_p": top_p,
            "stream_options": stream_options,
            "stop": stop,
            "max_completion_tokens": max_completion_tokens,
            "max_tokens": max_tokens,
            "modalities": modalities,
            "prediction": prediction,
            "audio": audio,
            "presence_penalty": presence_penalty,
            "frequency_penalty": frequency_penalty,
            "logit_bias": logit_bias,
            "user": user,
            "seed": seed,
            "logprobs": logprobs,
            "top_logprobs": top_logprobs,
            "deployment_id": deployment_id,
            "extra_headers": extra_headers,
            "functions": functions,
            "function_call": function_call,
            "api_version": api_version,
            "model_list": model_list,
            "stream": stream,
            "verbose": verbose,
        }

        if loader:
            with console.progress(
                f"Generating completion for {str(details['name'])}..."
            ) as progress:
                response = completion(**args)
                return response

        else:
            return await async_completion(**args)

    @function_handler
    def model_generate(
        cls_or_self,
        messages: Optional[CompletionMessagesParam] = "",
        model: CompletionChatModelsParam = "gpt-4o-mini",
        n: int = 1,
        loader: Optional[bool] = True,
        process: Optional[BaseModelGenerationProcess] = "batch",
        regenerate: Optional[bool] = False,
        fields: Optional[List[str]] = None,
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
    ) -> Union[
        BaseModelMixinType,
        List[BaseModelMixinType],
    ]:
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
            modalities (Optional[List[ResponseModality]]): Modalities to use for generation
            prediction (Optional[ResponsePredictionContentParam]): Prediction content parameter to use for generation
            audio (Optional[ResponseAudioParam]): Audio parameter to use for generation
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
            Union[T, List[T], Response, List[Response]]: Generated completion(s)
        """

        # Get model details
        details = cls_or_self._get_details()
        cls = cls_or_self if isinstance(cls_or_self, type) else type(cls_or_self)

        if not regenerate and not fields:
            if verbose:
                console.message(
                    f"Regenerate is set to False, only generating empty fields..."
                )

            empty_fields = [
                field_name
                for field_name, field in cls.model_fields.items()
                if field.default is None
            ]
            fields = empty_fields

        # If specific fields are requested, get the field-specific model
        if fields:
            patch_context, field_model = cls_or_self._get_patch_context(fields)
            ResponseModel = (
                field_model
                if n == 1
                else create_model("ResponseModel", items=(List[field_model], ...))
            )
            base_context = dedent(
                (
                    f"Generate {n} valid instance(s) of fields:\n\n"
                    f"{patch_context}\n\n"
                    "Requirements:\n"
                    "- Generate realistic, contextually appropriate data\n"
                    "- Include only required fields with direct values\n"
                    "- No placeholder or example values\n"
                    "- Follow all field constraints"
                )
            )
        else:
            ResponseModel = (
                cls if n == 1 else create_model("ResponseModel", items=(List[cls], ...))
            )
            base_context = dedent(
                (
                    f"Generate {n} valid instance(s) of:\n\n"
                    f"{cls.model_json_schema()}\n\n"
                    "Requirements:\n"
                    "- Generate realistic, contextually appropriate data\n"
                    "- Include only required fields with direct values\n"
                    "- No placeholder or example values\n"
                    "- Follow all schema constraints"
                )
            )

        # Add instance context if available
        if not isinstance(cls_or_self, type):
            base_context += (
                f"\n\nUse this instance as reference:\n{cls_or_self.model_dump_json()}"
            )

        if process == "batch":
            # Batch generation - all instances at once

            if verbose:
                console.message(
                    f"Generating {n} instance(s) of {details['name']} using batch generation..."
                )

            if loader:
                with console.progress(
                    f"Generating [white bold]{n}[/white bold] instance(s) of [white bold]{details['name']}[/white bold] using [sky_blue2 bold]{process}[/sky_blue2 bold] generation..."
                ) as progress:
                    response = cls_or_self.model_completion(
                        context=context + "\n\n" + base_context
                        if context
                        else base_context,
                        messages=messages,
                        model=model,
                        mode=mode,
                        response_model=ResponseModel,
                        verbose=verbose,
                        memory=memory,
                        memory_limit=memory_limit,
                        tools=tools,
                        run_tools=run_tools,
                        tool_choice=tool_choice,
                        parallel_tool_calls=parallel_tool_calls,
                        api_key=api_key,
                        base_url=base_url,
                        organization=organization,
                        n=n,
                        stream=stream,
                        timeout=timeout,
                        temperature=temperature,
                        top_p=top_p,
                        stream_options=stream_options,
                        stop=stop,
                        max_completion_tokens=max_completion_tokens,
                        max_tokens=max_tokens,
                        modalities=modalities,
                        prediction=prediction,
                        audio=audio,
                        presence_penalty=presence_penalty,
                        frequency_penalty=frequency_penalty,
                        logit_bias=logit_bias,
                        user=user,
                        seed=seed,
                        logprobs=logprobs,
                        top_logprobs=top_logprobs,
                        deployment_id=deployment_id,
                        extra_headers=extra_headers,
                        functions=functions,
                        function_call=function_call,
                        api_version=api_version,
                        model_list=model_list,
                        loader=False,
                    )
            else:
                response = cls_or_self.model_completion(
                    context=context + "\n\n" + base_context
                    if context
                    else base_context,
                    messages=messages,
                    model=model,
                    mode=mode,
                    response_model=ResponseModel,
                    verbose=verbose,
                    memory=memory,
                    memory_limit=memory_limit,
                    tools=tools,
                    run_tools=run_tools,
                    tool_choice=tool_choice,
                    parallel_tool_calls=parallel_tool_calls,
                    api_key=api_key,
                    base_url=base_url,
                    organization=organization,
                    n=n,
                    stream=stream,
                    timeout=timeout,
                    temperature=temperature,
                    top_p=top_p,
                    stream_options=stream_options,
                    stop=stop,
                    max_completion_tokens=max_completion_tokens,
                    max_tokens=max_tokens,
                    modalities=modalities,
                    prediction=prediction,
                    audio=audio,
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                    logit_bias=logit_bias,
                    user=user,
                    seed=seed,
                    logprobs=logprobs,
                    top_logprobs=top_logprobs,
                    deployment_id=deployment_id,
                    extra_headers=extra_headers,
                    functions=functions,
                    function_call=function_call,
                    api_version=api_version,
                    model_list=model_list,
                    loader=False,
                )

            # Return just the field model if specific fields requested
            if fields:
                # Update original model with any new generated values
                if not details["type"] == "instance":
                    if verbose:
                        console.log("Updating original model with generated values")

                        original_models = [
                            deepcopy(cls_or_self) for _ in range(len(results))
                        ]  # Use results instead of response.items

                        # Update each copy with corresponding generated values
                        for i, original_model in enumerate(original_models):
                            for field in fields:
                                setattr(
                                    original_model, field, getattr(results[i], field)
                                )  # Use results instead of response.items
                                if verbose:
                                    console.message(
                                        f"Setting {field} to {getattr(original_model, field)} for result {i+1}"
                                    )

                        # Return updated models
                        return original_models[0] if n == 1 else original_models

                    return response if n == 1 else response.items

            return response if n == 1 else response.items

        else:  # Sequential generation
            results = []
            target_fields = (
                fields if fields else [field_name for field_name in cls.model_fields]
            )

            for i in range(n):
                instance = {}

                # Generate each requested field sequentially
                for field_name in target_fields:
                    field = cls.model_fields[field_name]

                    if verbose:
                        console.message(
                            f"Generating field '{field_name}' for instance {i+1}/{n}..."
                        )

                    if loader:
                        with console.progress(
                            f"Generating field '[white bold]{field_name}[/white bold]' for instance {i+1}/{n} using [sky_blue2 bold]{process}[/sky_blue2 bold] generation..."
                        ) as progress:
                            # Build field-specific context with full model context
                            field_context = (
                                f"{base_context}\n\n"  # Add base context first
                                f"Now, generate a value for field '{field_name}' with type {field.annotation}.\n"
                                f"Current partial instance: {json.dumps(instance)}\n"
                            )

                            # Add previous generations for variety
                            if i > 0:
                                field_context += "\nPrevious values for this field:\n"
                                for j, prev_instance in enumerate(
                                    results[-min(3, i) :], 1
                                ):
                                    field_context += (
                                        f"{j}. {getattr(prev_instance, field_name)}\n"
                                    )
                                field_context += "\nPlease generate a different value."

                            # Create field-specific response model
                            FieldModel = create_model(
                                "FieldResponse", value=(field.annotation, ...)
                            )

                            response = cls_or_self.model_completion(
                                context=context + "\n\n" + field_context
                                if context
                                else field_context,
                                messages=messages,
                                model=model,
                                mode=mode,
                                response_model=FieldModel,
                                verbose=verbose,
                                memory=memory,
                                memory_limit=memory_limit,
                                tools=tools,
                                run_tools=run_tools,
                                tool_choice=tool_choice,
                                parallel_tool_calls=parallel_tool_calls,
                                api_key=api_key,
                                base_url=base_url,
                                organization=organization,
                                n=n,
                                stream=stream,
                                timeout=timeout,
                                temperature=temperature,
                                top_p=top_p,
                                stream_options=stream_options,
                                stop=stop,
                                max_completion_tokens=max_completion_tokens,
                                max_tokens=max_tokens,
                                modalities=modalities,
                                prediction=prediction,
                                audio=audio,
                                presence_penalty=presence_penalty,
                                frequency_penalty=frequency_penalty,
                                logit_bias=logit_bias,
                                user=user,
                                seed=seed,
                                logprobs=logprobs,
                                top_logprobs=top_logprobs,
                                deployment_id=deployment_id,
                                extra_headers=extra_headers,
                                functions=functions,
                                function_call=function_call,
                                api_version=api_version,
                                model_list=model_list,
                                loader=False,
                            )

                            instance[field_name] = response.value
                    else:
                        field_context = (
                            f"{base_context}\n\n"
                            f"Now, generate a value for field '{field_name}' with type {field.annotation}.\n"
                            f"Current partial instance: {json.dumps(instance)}\n"
                        )

                        if i > 0:
                            field_context += "\nPrevious values for this field:\n"
                            for j, prev_instance in enumerate(results[-min(3, i) :], 1):
                                field_context += (
                                    f"{j}. {getattr(prev_instance, field_name)}\n"
                                )
                            field_context += "\nPlease generate a different value."

                        FieldModel = create_model(
                            "FieldResponse", value=(field.annotation, ...)
                        )

                        response = cls_or_self.model_completion(
                            context=context + "\n\n" + field_context
                            if context
                            else field_context,
                            messages=messages,
                            model=model,
                            mode=mode,
                            response_model=FieldModel,
                            verbose=verbose,
                            memory=memory,
                            memory_limit=memory_limit,
                            tools=tools,
                            run_tools=run_tools,
                            tool_choice=tool_choice,
                            parallel_tool_calls=parallel_tool_calls,
                            api_key=api_key,
                            base_url=base_url,
                            organization=organization,
                            n=n,
                            stream=stream,
                            timeout=timeout,
                            temperature=temperature,
                            top_p=top_p,
                            stream_options=stream_options,
                            stop=stop,
                            max_completion_tokens=max_completion_tokens,
                            max_tokens=max_tokens,
                            modalities=modalities,
                            prediction=prediction,
                            audio=audio,
                            presence_penalty=presence_penalty,
                            frequency_penalty=frequency_penalty,
                            logit_bias=logit_bias,
                            user=user,
                            seed=seed,
                            logprobs=logprobs,
                            top_logprobs=top_logprobs,
                            deployment_id=deployment_id,
                            extra_headers=extra_headers,
                            functions=functions,
                            function_call=function_call,
                            api_version=api_version,
                            model_list=model_list,
                            loader=False,
                        )

                        instance[field_name] = response.value

                # Create complete instance and add to results
                if fields:
                    # Create field-specific model instance using the model class
                    if verbose:
                        console.message(
                            f"Creating field-specific model instance for {field_name} using the model class"
                        )

                    field_instance = field_model.model_validate(
                        instance
                    )  # Use model_validate instead of constructor
                    results.append(field_instance)
                else:
                    results.append(cls(**instance))

            # build final models
            if fields and not isinstance(cls_or_self, type):
                if verbose:
                    console.message("Updating original model with generated values")

                    # Create copies of original model for each result
                    original_models = [
                        deepcopy(cls_or_self) for _ in range(len(results))
                    ]  # Use results instead of response.items

                    # Update each copy with corresponding generated values
                    for i, original_model in enumerate(original_models):
                        for field in fields:
                            setattr(
                                original_model, field, getattr(results[i], field)
                            )  # Use results instead of response.items
                            if verbose:
                                console.message(
                                    f"Setting {field} to {getattr(original_model, field)} for result {i+1}"
                                )

                    # Return updated models
                    return original_models[0] if n == 1 else original_models

            return results[0] if n == 1 else results

    @function_handler
    async def model_async_generate(
        cls_or_self,
        messages: Optional[CompletionMessagesParam] = "",
        model: CompletionChatModelsParam = "gpt-4o-mini",
        loader: Optional[bool] = True,
        n: int = 1,
        context: Optional[CompletionContextParam] = None,
        process: Optional[BaseModelGenerationProcess] = "batch",
        regenerate: Optional[bool] = False,
        fields: Optional[List[str]] = None,
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
    ) -> Union[
        BaseModelMixinType,
        List[BaseModelMixinType],
    ]:
        """Asynchronously generates instance(s) of the model using LLM completion.

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
            modalities (Optional[List[ResponseModality]]): Modalities to use for generation
            prediction (Optional[ResponsePredictionContentParam]): Prediction content parameter to use for generation
            audio (Optional[ResponseAudioParam]): Audio parameter to use for generation
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
            Union[T, List[T], Response, List[Response]]: Generated completion(s)
        """
        # Get model details
        details = cls_or_self._get_details()
        cls = cls_or_self if isinstance(cls_or_self, type) else type(cls_or_self)

        if not regenerate and not fields:
            if verbose:
                console.message(
                    f"Regenerate is set to False, only generating empty fields..."
                )

            empty_fields = [
                field_name
                for field_name, field in cls.model_fields.items()
                if field.default is None
            ]
            fields = empty_fields

        # If specific fields are requested, get the field-specific model
        if fields:
            patch_context, field_model = cls_or_self._get_patch_context(fields)
            ResponseModel = (
                field_model
                if n == 1
                else create_model("ResponseModel", items=(List[field_model], ...))
            )
            base_context = dedent(
                (
                    f"Generate {n} valid instance(s) of fields:\n\n"
                    f"{patch_context}\n\n"
                    "Requirements:\n"
                    "- Generate realistic, contextually appropriate data\n"
                    "- Include only required fields with direct values\n"
                    "- No placeholder or example values\n"
                    "- Follow all field constraints"
                )
            )
        else:
            ResponseModel = (
                cls if n == 1 else create_model("ResponseModel", items=(List[cls], ...))
            )
            base_context = dedent(
                (
                    f"Generate {n} valid instance(s) of:\n\n"
                    f"{cls.model_json_schema()}\n\n"
                    "Requirements:\n"
                    "- Generate realistic, contextually appropriate data\n"
                    "- Include only required fields with direct values\n"
                    "- No placeholder or example values\n"
                    "- Follow all schema constraints"
                )
            )

        # Add instance context if available
        if not isinstance(cls_or_self, type):
            base_context += (
                f"\n\nUse this instance as reference:\n{cls_or_self.model_dump_json()}"
            )

        if process == "batch":
            # Batch generation - all instances at once

            if verbose:
                console.message(
                    f"Generating {n} instance(s) of {details['name']} using batch generation..."
                )

            if loader:
                with console.progress(
                    f"Generating {n} instance(s) of {details['name']}..."
                ) as progress:
                    response = await cls_or_self.model_async_completion(
                        context=context + "\n\n" + base_context
                        if context
                        else base_context,
                        messages=messages,
                        model=model,
                        mode=mode,
                        response_model=ResponseModel,
                        verbose=verbose,
                        memory=memory,
                        memory_limit=memory_limit,
                        tools=tools,
                        run_tools=run_tools,
                        tool_choice=tool_choice,
                        parallel_tool_calls=parallel_tool_calls,
                        api_key=api_key,
                        base_url=base_url,
                        organization=organization,
                        n=n,
                        stream=stream,
                        timeout=timeout,
                        temperature=temperature,
                        top_p=top_p,
                        stream_options=stream_options,
                        stop=stop,
                        max_completion_tokens=max_completion_tokens,
                        max_tokens=max_tokens,
                        modalities=modalities,
                        prediction=prediction,
                        audio=audio,
                        presence_penalty=presence_penalty,
                        frequency_penalty=frequency_penalty,
                        logit_bias=logit_bias,
                        user=user,
                        seed=seed,
                        logprobs=logprobs,
                        top_logprobs=top_logprobs,
                        deployment_id=deployment_id,
                        extra_headers=extra_headers,
                        functions=functions,
                        function_call=function_call,
                        api_version=api_version,
                        model_list=model_list,
                        loader=False,
                    )
            else:
                response = await cls_or_self.model_async_completion(
                    context=context + "\n\n" + base_context
                    if context
                    else base_context,
                    messages=messages,
                    model=model,
                    mode=mode,
                    response_model=ResponseModel,
                    verbose=verbose,
                    memory=memory,
                    memory_limit=memory_limit,
                    tools=tools,
                    run_tools=run_tools,
                    tool_choice=tool_choice,
                    parallel_tool_calls=parallel_tool_calls,
                    api_key=api_key,
                    base_url=base_url,
                    organization=organization,
                    n=n,
                    stream=stream,
                    timeout=timeout,
                    temperature=temperature,
                    top_p=top_p,
                    stream_options=stream_options,
                    stop=stop,
                    max_completion_tokens=max_completion_tokens,
                    max_tokens=max_tokens,
                    modalities=modalities,
                    prediction=prediction,
                    audio=audio,
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                    logit_bias=logit_bias,
                    user=user,
                    seed=seed,
                    logprobs=logprobs,
                    top_logprobs=top_logprobs,
                    deployment_id=deployment_id,
                    extra_headers=extra_headers,
                    functions=functions,
                    function_call=function_call,
                    api_version=api_version,
                    model_list=model_list,
                    loader=False,
                )

            # Return just the field model if specific fields requested
            if fields:
                # Update original model with any new generated values
                if not details["type"] == "instance":
                    if verbose:
                        console.log("Updating original model with generated values")

                        original_models = [
                            deepcopy(cls_or_self) for _ in range(len(results))
                        ]  # Use results instead of response.items

                        # Update each copy with corresponding generated values
                        for i, original_model in enumerate(original_models):
                            for field in fields:
                                setattr(
                                    original_model, field, getattr(results[i], field)
                                )  # Use results instead of response.items
                                if verbose:
                                    console.message(
                                        f"Setting {field} to {getattr(original_model, field)} for result {i+1}"
                                    )

                        # Return updated models
                        return original_models[0] if n == 1 else original_models

                    return response if n == 1 else response.items

            return response if n == 1 else response.items

        else:  # Sequential generation
            results = []
            target_fields = (
                fields if fields else [field_name for field_name in cls.model_fields]
            )

            for i in range(n):
                instance = {}

                # Generate each requested field sequentially
                for field_name in target_fields:
                    field = cls.model_fields[field_name]

                    if verbose:
                        console.message(
                            f"Generating field '{field_name}' for instance {i+1}/{n}..."
                        )

                    if loader:
                        with console.progress(
                            f"Generating field '{field_name}' for instance {i+1}/{n}..."
                        ) as progress:
                            # Build field-specific context with full model context
                            field_context = (
                                f"{base_context}\n\n"  # Add base context first
                                f"Now, generate a value for field '{field_name}' with type {field.annotation}.\n"
                                f"Current partial instance: {json.dumps(instance)}\n"
                            )

                            # Add previous generations for variety
                            if i > 0:
                                field_context += "\nPrevious values for this field:\n"
                                for j, prev_instance in enumerate(
                                    results[-min(3, i) :], 1
                                ):
                                    field_context += (
                                        f"{j}. {getattr(prev_instance, field_name)}\n"
                                    )
                                field_context += "\nPlease generate a different value."

                            # Create field-specific response model
                            FieldModel = create_model(
                                "FieldResponse", value=(field.annotation, ...)
                            )

                            response = await cls_or_self.model_async_completion(
                                context=context + "\n\n" + field_context
                                if context
                                else field_context,
                                messages=messages,
                                model=model,
                                mode=mode,
                                response_model=FieldModel,
                                verbose=verbose,
                                memory=memory,
                                memory_limit=memory_limit,
                                tools=tools,
                                run_tools=run_tools,
                                tool_choice=tool_choice,
                                parallel_tool_calls=parallel_tool_calls,
                                api_key=api_key,
                                base_url=base_url,
                                organization=organization,
                                n=n,
                                stream=stream,
                                timeout=timeout,
                                temperature=temperature,
                                top_p=top_p,
                                stream_options=stream_options,
                                stop=stop,
                                max_completion_tokens=max_completion_tokens,
                                max_tokens=max_tokens,
                                modalities=modalities,
                                prediction=prediction,
                                audio=audio,
                                presence_penalty=presence_penalty,
                                frequency_penalty=frequency_penalty,
                                logit_bias=logit_bias,
                                user=user,
                                seed=seed,
                                logprobs=logprobs,
                                top_logprobs=top_logprobs,
                                deployment_id=deployment_id,
                                extra_headers=extra_headers,
                                functions=functions,
                                function_call=function_call,
                                api_version=api_version,
                                model_list=model_list,
                                loader=False,
                            )

                            instance[field_name] = response.value
                    else:
                        field_context = (
                            f"{base_context}\n\n"
                            f"Now, generate a value for field '{field_name}' with type {field.annotation}.\n"
                            f"Current partial instance: {json.dumps(instance)}\n"
                        )

                        if i > 0:
                            field_context += "\nPrevious values for this field:\n"
                            for j, prev_instance in enumerate(results[-min(3, i) :], 1):
                                field_context += (
                                    f"{j}. {getattr(prev_instance, field_name)}\n"
                                )
                            field_context += "\nPlease generate a different value."

                        FieldModel = create_model(
                            "FieldResponse", value=(field.annotation, ...)
                        )

                        response = await cls_or_self.model_async_completion(
                            context=context + "\n\n" + field_context
                            if context
                            else field_context,
                            messages=messages,
                            model=model,
                            mode=mode,
                            response_model=FieldModel,
                            verbose=verbose,
                            memory=memory,
                            memory_limit=memory_limit,
                            tools=tools,
                            run_tools=run_tools,
                            tool_choice=tool_choice,
                            parallel_tool_calls=parallel_tool_calls,
                            api_key=api_key,
                            base_url=base_url,
                            organization=organization,
                            n=n,
                            stream=stream,
                            timeout=timeout,
                            temperature=temperature,
                            top_p=top_p,
                            stream_options=stream_options,
                            stop=stop,
                            max_completion_tokens=max_completion_tokens,
                            max_tokens=max_tokens,
                            modalities=modalities,
                            prediction=prediction,
                            audio=audio,
                            presence_penalty=presence_penalty,
                            frequency_penalty=frequency_penalty,
                            logit_bias=logit_bias,
                            user=user,
                            seed=seed,
                            logprobs=logprobs,
                            top_logprobs=top_logprobs,
                            deployment_id=deployment_id,
                            extra_headers=extra_headers,
                            functions=functions,
                            function_call=function_call,
                            api_version=api_version,
                            model_list=model_list,
                            loader=False,
                        )

                        instance[field_name] = response.value

                # Create complete instance and add to results
                if fields:
                    # Create field-specific model instance using the model class
                    if verbose:
                        console.message(
                            f"Creating field-specific model instance for {field_name} using the model class"
                        )

                    field_instance = field_model.model_validate(
                        instance
                    )  # Use model_validate instead of constructor
                    results.append(field_instance)
                else:
                    results.append(cls(**instance))

            # build final models
            if fields and not isinstance(cls_or_self, type):
                if verbose:
                    console.message("Updating original model with generated values")

                    # Create copies of original model for each result
                    original_models = [
                        deepcopy(cls_or_self) for _ in range(len(results))
                    ]  # Use results instead of response.items

                    # Update each copy with corresponding generated values
                    for i, original_model in enumerate(original_models):
                        for field in fields:
                            setattr(
                                original_model, field, getattr(results[i], field)
                            )  # Use results instead of response.items
                            if verbose:
                                console.message(
                                    f"Setting {field} to {getattr(original_model, field)} for result {i+1}"
                                )

                    # Return updated models
                    return original_models[0] if n == 1 else original_models

            return results[0] if n == 1 else results


# -------------------------------------------------------------------------------------------------
# EXPORTS
# -------------------------------------------------------------------------------------------------


class GenerativeModel(PydanticBaseModel, BaseModelMixin): ...


# -------------------------------------------------------------------------------------------------
# PATCH
# -------------------------------------------------------------------------------------------------


def patch(
    model: Union[Type[PydanticBaseModel], PydanticBaseModel],
) -> Union[Type[GenerativeModel], GenerativeModel, Type[PydanticBaseModel], PydanticBaseModel]:
    if isinstance(model, type) and issubclass(model, PydanticBaseModel):
        PatchedModel = type(model.__name__, (model, BaseModelMixin), {})
        return PatchedModel
    elif isinstance(model, PydanticBaseModel):
        model.__class__ = type(
            model.__class__.__name__, (model.__class__, BaseModelMixin), {}
        )
        return model
    else:
        raise TypeError(
            "The patch function expects a Pydantic BaseModel class or instance."
        )


def unpatch(
    model: Union[Type[GenerativeModel], GenerativeModel, Type[PydanticBaseModel], PydanticBaseModel],
) -> Union[Type[PydanticBaseModel], PydanticBaseModel]:
    if isinstance(model, type) and issubclass(model, PydanticBaseModel):
        return model.__base__
    elif isinstance(model, PydanticBaseModel):
        return model.__class__.__base__


# -------------------------------------------------------------------------------------------------
# TESTS
# -------------------------------------------------------------------------------------------------


# tests
if __name__ == "__main__":

    class Test(PydanticBaseModel):
        name: str
        age: int

    test = Test(name="John", age=30)

    test = patch(test)
    Test = patch(Test)

    print(Test.model_generate())

    print(test.model_generate())
