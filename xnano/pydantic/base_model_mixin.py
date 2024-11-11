# basemodel
# llm extension for pydantic models

from pydantic import BaseModel as PydanticBaseModel, create_model, Field

from ..completions.main import completion, acompletion
from .._lib import console, XNANOException

import json
import httpx
from textwrap import dedent
from copy import deepcopy
from typing import Type, TypeVar, Union, Dict, Any, Optional, List, Tuple
from ..types.pydantic.base_model_mixin import BaseModelMixin as BaseModelMixinType
from ..types.pydantic.base_model_generation_process import BaseModelGenerationProcess
from ..types.openai import ChatCompletionModality, ChatCompletionPredictionContentParam, ChatCompletionAudioParam, ChatCompletion
from ..types.completions.context import Context
from ..types.completions.chat_models import ChatModel
from ..types.completions.instructor import InstructorMode
from ..types.completions.response_models import ResponseModelType
from ..types.completions.messages import MessageType
from ..types.completions.tools import ToolChoice, ToolType


# typevar
T = TypeVar('T', bound='BaseModelMixin')


# -------------------------------------------------------------------------------------------------
# helper class for class & instance funcs
# -------------------------------------------------------------------------------------------------

class function_handler:

    def __init__(self, func):
        self.func = func

    # helper for getting class or instance details
    def __get__(self, obj, cls):
        def wrapper(*args, **kwargs):
            return self.func(obj or cls, *args, **kwargs)
        return wrapper

# -------------------------------------------------------------------------------------------------
# MIXIN
# -------------------------------------------------------------------------------------------------

class BaseModelMixin:

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
            original_model = cls_or_self if isinstance(cls_or_self, type) else cls_or_self.__class__
            original_fields = original_model.__annotations__
            
            # Validate that all requested fields exist in the original model
            invalid_fields = set(fields) - set(original_fields.keys())
            if invalid_fields:
                raise ValueError(f"Fields {invalid_fields} do not exist in {original_model.__name__}")
                
            # Create field definitions for the new model - ONLY for requested fields
            field_definitions = {}
            for field in fields:  # Only iterate through requested fields
                field_type = original_fields[field]
                field_info = original_model.__fields__[field] if hasattr(original_model, '__fields__') else None
                default_value = getattr(field_info, 'default', ...) if field_info else ...
                field_definitions[field] = (field_type, default_value)
            
            # Create new model with ONLY the specified fields
            new_model = create_model(
                f"{original_model.__name__}Patch",
                **field_definitions 
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
    def _merge_patch_with_cls(cls_or_self, fields: List[str], response: PydanticBaseModel) -> PydanticBaseModel:
        """Merges only the new values from the patch with the original model"""
        try:
            response_data = response.model_dump()
            return cls_or_self.model_validate(response_data)
        except Exception as e:
            raise XNANOException(f"Failed to merge patch with class: {str(e)}")
        
        
    @function_handler
    def _get_model_by_none_fields(cls_or_self) -> Tuple[str, Union[Type[PydanticBaseModel], None]]:
        """Builds a model using the original model and only the fields with None values"""
        try:
            original_model = cls_or_self if isinstance(cls_or_self, type) else cls_or_self.__class__
            original_fields = original_model.__annotations__

            # Identify fields with None values
            none_fields = [field for field in original_fields if getattr(cls_or_self, field, None) is None]

            # If all fields have values, return the original model
            if not none_fields:
                return cls_or_self._get_context(), type(cls_or_self)

            # Use _get_patch_context to create context and model with only None fields
            return cls_or_self._get_patch_context(none_fields)
        
        except Exception as e:
            raise XNANOException(f"Failed to build model by none fields: {str(e)}")
        

    # builds context for patch
    @function_handler
    def _get_patch_context(cls_or_self, fields: List[str]) -> Tuple[str, Type[PydanticBaseModel]]:
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
                "fields": list(cls_or_self.__annotations__.keys()) if hasattr(cls_or_self, '__annotations__') else [],
                "annotations": cls_or_self.__annotations__ if hasattr(cls_or_self, '__annotations__') else {},
                "values": None
            }
        else:
            # Called on an instance
            details = {
                "type": "instance",
                "name": cls_or_self.__class__.__name__,
                "fields": list(cls_or_self.__class__.__annotations__.keys()) if hasattr(cls_or_self.__class__, '__annotations__') else [],
                "annotations": cls_or_self.__class__.__annotations__ if hasattr(cls_or_self.__class__, '__annotations__') else {},
                "values": cls_or_self.model_dump()
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
            "Items will always be in a JSON schema or format. DO NOT include this information in your responses."
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
        messages : MessageType,
        model : ChatModel = "gpt-4o-mini",
        context : Optional[Context] = None,
        mode : Optional[InstructorMode] = None,
        response_model : Optional[ResponseModelType] = None,
        response_format : Optional[ResponseModelType] = None,
        tools : Optional[List[ToolType]] = None,
        run_tools : Optional[bool] = None,
        tool_choice : Optional[ToolChoice] = None,
        parallel_tool_calls : Optional[bool] = None,
        api_key : Optional[str] = None,
        base_url : Optional[str] = None,
        organization : Optional[str] = None,
        n : Optional[int] = None,
        timeout: Optional[Union[float, str, httpx.Timeout]] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stream_options: Optional[dict] = None,
        stop=None,
        max_completion_tokens: Optional[int] = None,
        max_tokens: Optional[int] = None,
        modalities: Optional[List[ChatCompletionModality]] = None,
        prediction: Optional[ChatCompletionPredictionContentParam] = None,
        audio: Optional[ChatCompletionAudioParam] = None,
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
        stream : Optional[bool] = None,
        loader : Optional[bool] = True,
        verbose : Optional[bool] = None,
    ) -> Union[
        ChatCompletion,
        BaseModelMixinType,
        List[BaseModelMixinType],
        List[ChatCompletion],
    ]:
        
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
    async def model_acompletion(
        cls_or_self,
        messages : MessageType,
        model : ChatModel = "gpt-4o-mini",
        context : Optional[Context] = None,
        mode : Optional[InstructorMode] = None,
        response_model : Optional[ResponseModelType] = None,
        response_format : Optional[ResponseModelType] = None,
        tools : Optional[List[ToolType]] = None,
        run_tools : Optional[bool] = None,
        tool_choice : Optional[ToolChoice] = None,
        parallel_tool_calls : Optional[bool] = None,
        api_key : Optional[str] = None,
        base_url : Optional[str] = None,
        organization : Optional[str] = None,
        n : Optional[int] = None,
        timeout: Optional[Union[float, str, httpx.Timeout]] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stream_options: Optional[dict] = None,
        stop=None,
        max_completion_tokens: Optional[int] = None,
        max_tokens: Optional[int] = None,
        modalities: Optional[List[ChatCompletionModality]] = None,
        prediction: Optional[ChatCompletionPredictionContentParam] = None,
        audio: Optional[ChatCompletionAudioParam] = None,
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
        stream : Optional[bool] = None,
        loader : Optional[bool] = True,
        verbose : Optional[bool] = None,
    ) -> Union[
        ChatCompletion,
        BaseModelMixinType,
        List[BaseModelMixinType],
        List[ChatCompletion],
    ]:
        
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
            return await acompletion(**args)
        

    @function_handler
    def model_generate(
        cls_or_self,
        messages: MessageType = "",
        model: ChatModel = "gpt-4o-mini",
        process: BaseModelGenerationProcess = "batch",
        n: Optional[int] = 1,
        fields: Optional[List[str]] = None,
        regenerate: Optional[bool] = None,
        context: Optional[Context] = None,
        mode: Optional[InstructorMode] = None,
        tools: Optional[List[ToolType]] = None,
        run_tools: Optional[bool] = None,
        tool_choice: Optional[ToolChoice] = None,
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
        modalities: Optional[List[ChatCompletionModality]] = None,
        prediction: Optional[ChatCompletionPredictionContentParam] = None,
        audio: Optional[ChatCompletionAudioParam] = None,
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
            process (BaseModelGenerationProcess): Generation process type ("batch" or "sequential")
            n (Optional[int]): Number of instances to generate
            fields (Optional[List[str]]): Specific fields to generate/update
            regenerate (Optional[bool]): Whether to regenerate all fields
            context (Optional[Context]): Additional context to provide
            ... (other standard completion parameters)
            
        Returns:
            Union[BaseModel, List[BaseModel]]: Generated instance(s)
        """
        # Get model details
        details = cls_or_self._get_details()
        cls = cls_or_self if isinstance(cls_or_self, type) else type(cls_or_self)

        if not regenerate and not fields:

            if verbose:
                console.message(f"Regenerate is set to False, only generating empty fields...")

            empty_fields = [field_name for field_name, field in cls.model_fields.items() if field.default is None]
            fields = empty_fields
        
        # If specific fields are requested, get the field-specific model
        if fields:
            patch_context, field_model = cls_or_self._get_patch_context(fields)
            ResponseModel = field_model if n == 1 else create_model("ResponseModel", items=(List[field_model], ...))
            base_context = dedent((
                f"Generate {n} valid instance(s) of fields:\n\n"
                f"{patch_context}\n\n"
                "Requirements:\n"
                "- Generate realistic, contextually appropriate data\n"
                "- Include only required fields with direct values\n" 
                "- No placeholder or example values\n"
                "- Follow all field constraints"
            ))
        else:
            ResponseModel = cls if n == 1 else create_model("ResponseModel", items=(List[cls], ...))
            base_context = dedent((
                f"Generate {n} valid instance(s) of:\n\n"
                f"{cls.model_json_schema()}\n\n"
                "Requirements:\n"
                "- Generate realistic, contextually appropriate data\n" 
                "- Include only required fields with direct values\n"
                "- No placeholder or example values\n"
                "- Follow all schema constraints"
            ))

        # Add instance context if available
        if not isinstance(cls_or_self, type):
            base_context += f"\n\nUse this instance as reference:\n{cls_or_self.model_dump_json()}"

        if process == "batch":
            # Batch generation - all instances at once

            if verbose:
                console.message(f"Generating {n} instance(s) of {details['name']} using batch generation...")

            if loader:
                with console.progress(f"Generating [white bold]{n}[/white bold] instance(s) of [white bold]{details['name']}[/white bold] using [sky_blue2 bold]{process}[/sky_blue2 bold] generation...") as progress:
                    response = cls_or_self.model_completion(
                        context=context + "\n\n" + base_context if context else base_context,
                        messages = messages, model = model, 
                        mode = mode, response_model = ResponseModel, verbose = verbose,
                        tools = tools, run_tools = run_tools, tool_choice = tool_choice, parallel_tool_calls = parallel_tool_calls,
                        api_key = api_key, base_url = base_url, organization = organization, n = n, stream = stream,
                        timeout = timeout, temperature = temperature, top_p = top_p, stream_options = stream_options, stop = stop,
                        max_completion_tokens = max_completion_tokens, max_tokens = max_tokens, modalities = modalities,
                        prediction = prediction, audio = audio, presence_penalty = presence_penalty, frequency_penalty = frequency_penalty,
                        logit_bias = logit_bias, user = user, seed = seed, logprobs = logprobs, top_logprobs = top_logprobs,
                        deployment_id = deployment_id, extra_headers = extra_headers, functions = functions, function_call = function_call,
                        api_version = api_version, model_list = model_list, loader = False
                    )
            else:
                response = cls_or_self.model_completion(
                    context=context + "\n\n" + base_context if context else base_context,
                    messages = messages, model = model, 
                    mode = mode, response_model = ResponseModel, verbose = verbose,
                    tools = tools, run_tools = run_tools, tool_choice = tool_choice, parallel_tool_calls = parallel_tool_calls,
                    api_key = api_key, base_url = base_url, organization = organization, n = n, stream = stream,
                    timeout = timeout, temperature = temperature, top_p = top_p, stream_options = stream_options, stop = stop,
                    max_completion_tokens = max_completion_tokens, max_tokens = max_tokens, modalities = modalities,
                    prediction = prediction, audio = audio, presence_penalty = presence_penalty, frequency_penalty = frequency_penalty,
                    logit_bias = logit_bias, user = user, seed = seed, logprobs = logprobs, top_logprobs = top_logprobs,
                    deployment_id = deployment_id, extra_headers = extra_headers, functions = functions, function_call = function_call,
                    api_version = api_version, model_list = model_list, loader = False
                )
            
            # Return just the field model if specific fields requested
            if fields:

                # Update original model with any new generated values
                if not details['type'] == "instance":
                    if verbose:
                        console.log("Updating original model with generated values")

                        original_models = [deepcopy(cls_or_self) for _ in range(len(results))]  # Use results instead of response.items
                        
                        # Update each copy with corresponding generated values
                        for i, original_model in enumerate(original_models):
                            for field in fields:
                                setattr(original_model, field, getattr(results[i], field))  # Use results instead of response.items
                                if verbose:
                                    console.message(f"Setting {field} to {getattr(original_model, field)} for result {i+1}")
                        
                        # Return updated models
                        return original_models[0] if n == 1 else original_models
                    
                    return response if n == 1 else response.items

            return response if n == 1 else response.items
        
        else:  # Sequential generation
            results = []
            target_fields = fields if fields else [field_name for field_name in cls.model_fields]
            
            for i in range(n):
                instance = {}
                
                # Generate each requested field sequentially
                for field_name in target_fields:
                    field = cls.model_fields[field_name]

                    if verbose:
                        console.message(f"Generating field '{field_name}' for instance {i+1}/{n}...")

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
                                for j, prev_instance in enumerate(results[-min(3, i):], 1):
                                    field_context += f"{j}. {getattr(prev_instance, field_name)}\n"
                                field_context += "\nPlease generate a different value."
                            
                            # Create field-specific response model
                            FieldModel = create_model("FieldResponse", value=(field.annotation, ...))
                            
                            response = cls_or_self.model_completion(
                                context=context + "\n\n" + field_context if context else field_context,
                                messages = messages, model = model, 
                                mode = mode, response_model = FieldModel, verbose = verbose,
                                tools = tools, run_tools = run_tools, tool_choice = tool_choice, parallel_tool_calls = parallel_tool_calls,
                                api_key = api_key, base_url = base_url, organization = organization, n = n, stream = stream,
                                timeout = timeout, temperature = temperature, top_p = top_p, stream_options = stream_options, stop = stop,
                                max_completion_tokens = max_completion_tokens, max_tokens = max_tokens, modalities = modalities,
                                prediction = prediction, audio = audio, presence_penalty = presence_penalty, frequency_penalty = frequency_penalty,
                                logit_bias = logit_bias, user = user, seed = seed, logprobs = logprobs, top_logprobs = top_logprobs,
                                deployment_id = deployment_id, extra_headers = extra_headers, functions = functions, function_call = function_call,
                                api_version = api_version, model_list = model_list, loader = False
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
                            for j, prev_instance in enumerate(results[-min(3, i):], 1):
                                field_context += f"{j}. {getattr(prev_instance, field_name)}\n"
                            field_context += "\nPlease generate a different value."
                        
                        FieldModel = create_model("FieldResponse", value=(field.annotation, ...))
                        
                        response = cls_or_self.model_completion(
                            context=context + "\n\n" + field_context if context else field_context,
                            messages = messages, model = model, 
                            mode = mode, response_model = FieldModel, verbose = verbose,
                            tools = tools, run_tools = run_tools, tool_choice = tool_choice, parallel_tool_calls = parallel_tool_calls,
                            api_key = api_key, base_url = base_url, organization = organization, n = n, stream = stream,
                            timeout = timeout, temperature = temperature, top_p = top_p, stream_options = stream_options, stop = stop,
                            max_completion_tokens = max_completion_tokens, max_tokens = max_tokens, modalities = modalities,
                            prediction = prediction, audio = audio, presence_penalty = presence_penalty, frequency_penalty = frequency_penalty,
                            logit_bias = logit_bias, user = user, seed = seed, logprobs = logprobs, top_logprobs = top_logprobs,
                            deployment_id = deployment_id, extra_headers = extra_headers, functions = functions, function_call = function_call,
                            api_version = api_version, model_list = model_list, loader = False
                        )
                        
                        instance[field_name] = response.value
                
                # Create complete instance and add to results
                if fields:

                    # Create field-specific model instance using the model class
                    if verbose:
                        console.message(f"Creating field-specific model instance for {field_name} using the model class")

                    field_instance = field_model.model_validate(instance)  # Use model_validate instead of constructor
                    results.append(field_instance)
                else:
                    results.append(cls(**instance))
            
            # build final models
            if fields and not isinstance(cls_or_self, type):
                if verbose:
                    console.message("Updating original model with generated values")
                    
                    # Create copies of original model for each result
                    original_models = [deepcopy(cls_or_self) for _ in range(len(results))]  # Use results instead of response.items
                    
                    # Update each copy with corresponding generated values
                    for i, original_model in enumerate(original_models):
                        for field in fields:
                            setattr(original_model, field, getattr(results[i], field))  # Use results instead of response.items
                            if verbose:
                                console.message(f"Setting {field} to {getattr(original_model, field)} for result {i+1}")
                    
                    # Return updated models
                    return original_models[0] if n == 1 else original_models

            return results[0] if n == 1 else results
        
    @function_handler
    async def model_agenerate(
        cls_or_self,
        messages: MessageType = "",
        model: ChatModel = "gpt-4o-mini",
        process: BaseModelGenerationProcess = "batch",
        n: Optional[int] = 1,
        fields: Optional[List[str]] = None,
        regenerate: Optional[bool] = None,
        context: Optional[Context] = None,
        mode: Optional[InstructorMode] = None,
        tools: Optional[List[ToolType]] = None,
        run_tools: Optional[bool] = None,
        tool_choice: Optional[ToolChoice] = None,
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
        modalities: Optional[List[ChatCompletionModality]] = None,
        prediction: Optional[ChatCompletionPredictionContentParam] = None,
        audio: Optional[ChatCompletionAudioParam] = None,
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
            process (BaseModelGenerationProcess): Generation process type ("batch" or "sequential")
            n (Optional[int]): Number of instances to generate
            fields (Optional[List[str]]): Specific fields to generate/update
            regenerate (Optional[bool]): Whether to regenerate all fields
            context (Optional[Context]): Additional context to provide
            ... (other standard completion parameters)
            
        Returns:
            Union[BaseModel, List[BaseModel]]: Generated instance(s)
        """
        # Get model details
        details = cls_or_self._get_details()
        cls = cls_or_self if isinstance(cls_or_self, type) else type(cls_or_self)

        if not regenerate and not fields:

            if verbose:
                console.message(f"Regenerate is set to False, only generating empty fields...")

            empty_fields = [field_name for field_name, field in cls.model_fields.items() if field.default is None]
            fields = empty_fields
        
        # If specific fields are requested, get the field-specific model
        if fields:
            patch_context, field_model = cls_or_self._get_patch_context(fields)
            ResponseModel = field_model if n == 1 else create_model("ResponseModel", items=(List[field_model], ...))
            base_context = dedent((
                f"Generate {n} valid instance(s) of fields:\n\n"
                f"{patch_context}\n\n"
                "Requirements:\n"
                "- Generate realistic, contextually appropriate data\n"
                "- Include only required fields with direct values\n" 
                "- No placeholder or example values\n"
                "- Follow all field constraints"
            ))
        else:
            ResponseModel = cls if n == 1 else create_model("ResponseModel", items=(List[cls], ...))
            base_context = dedent((
                f"Generate {n} valid instance(s) of:\n\n"
                f"{cls.model_json_schema()}\n\n"
                "Requirements:\n"
                "- Generate realistic, contextually appropriate data\n" 
                "- Include only required fields with direct values\n"
                "- No placeholder or example values\n"
                "- Follow all schema constraints"
            ))

        # Add instance context if available
        if not isinstance(cls_or_self, type):
            base_context += f"\n\nUse this instance as reference:\n{cls_or_self.model_dump_json()}"

        if process == "batch":
            # Batch generation - all instances at once

            if verbose:
                console.message(f"Generating {n} instance(s) of {details['name']} using batch generation...")

            if loader:
                with console.progress(f"Generating {n} instance(s) of {details['name']}...") as progress:
                    response = await cls_or_self.model_acompletion(
                        context=context + "\n\n" + base_context if context else base_context,
                        messages = messages, model = model, 
                        mode = mode, response_model = ResponseModel, verbose = verbose,
                        tools = tools, run_tools = run_tools, tool_choice = tool_choice, parallel_tool_calls = parallel_tool_calls,
                        api_key = api_key, base_url = base_url, organization = organization, n = n, stream = stream,
                        timeout = timeout, temperature = temperature, top_p = top_p, stream_options = stream_options, stop = stop,
                        max_completion_tokens = max_completion_tokens, max_tokens = max_tokens, modalities = modalities,
                        prediction = prediction, audio = audio, presence_penalty = presence_penalty, frequency_penalty = frequency_penalty,
                        logit_bias = logit_bias, user = user, seed = seed, logprobs = logprobs, top_logprobs = top_logprobs,
                        deployment_id = deployment_id, extra_headers = extra_headers, functions = functions, function_call = function_call,
                        api_version = api_version, model_list = model_list, loader = False
                    )
            else:
                response = await cls_or_self.model_acompletion(
                    context=context + "\n\n" + base_context if context else base_context,
                    messages = messages, model = model, 
                    mode = mode, response_model = ResponseModel, verbose = verbose,
                    tools = tools, run_tools = run_tools, tool_choice = tool_choice, parallel_tool_calls = parallel_tool_calls,
                    api_key = api_key, base_url = base_url, organization = organization, n = n, stream = stream,
                    timeout = timeout, temperature = temperature, top_p = top_p, stream_options = stream_options, stop = stop,
                    max_completion_tokens = max_completion_tokens, max_tokens = max_tokens, modalities = modalities,
                    prediction = prediction, audio = audio, presence_penalty = presence_penalty, frequency_penalty = frequency_penalty,
                    logit_bias = logit_bias, user = user, seed = seed, logprobs = logprobs, top_logprobs = top_logprobs,
                    deployment_id = deployment_id, extra_headers = extra_headers, functions = functions, function_call = function_call,
                    api_version = api_version, model_list = model_list, loader = False
                )
            
            # Return just the field model if specific fields requested
            if fields:

                # Update original model with any new generated values
                if not details['type'] == "instance":
                    if verbose:
                        console.log("Updating original model with generated values")

                        original_models = [deepcopy(cls_or_self) for _ in range(len(results))]  # Use results instead of response.items
                        
                        # Update each copy with corresponding generated values
                        for i, original_model in enumerate(original_models):
                            for field in fields:
                                setattr(original_model, field, getattr(results[i], field))  # Use results instead of response.items
                                if verbose:
                                    console.message(f"Setting {field} to {getattr(original_model, field)} for result {i+1}")
                        
                        # Return updated models
                        return original_models[0] if n == 1 else original_models
                    
                    return response if n == 1 else response.items

            return response if n == 1 else response.items
        
        else:  # Sequential generation
            results = []
            target_fields = fields if fields else [field_name for field_name in cls.model_fields]
            
            for i in range(n):
                instance = {}
                
                # Generate each requested field sequentially
                for field_name in target_fields:
                    field = cls.model_fields[field_name]

                    if verbose:
                        console.message(f"Generating field '{field_name}' for instance {i+1}/{n}...")

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
                                for j, prev_instance in enumerate(results[-min(3, i):], 1):
                                    field_context += f"{j}. {getattr(prev_instance, field_name)}\n"
                                field_context += "\nPlease generate a different value."
                            
                            # Create field-specific response model
                            FieldModel = create_model("FieldResponse", value=(field.annotation, ...))
                            
                            response = await cls_or_self.model_acompletion(
                                context=context + "\n\n" + field_context if context else field_context,
                                messages = messages, model = model, 
                                mode = mode, response_model = FieldModel, verbose = verbose,
                                tools = tools, run_tools = run_tools, tool_choice = tool_choice, parallel_tool_calls = parallel_tool_calls,
                                api_key = api_key, base_url = base_url, organization = organization, n = n, stream = stream,
                                timeout = timeout, temperature = temperature, top_p = top_p, stream_options = stream_options, stop = stop,
                                max_completion_tokens = max_completion_tokens, max_tokens = max_tokens, modalities = modalities,
                                prediction = prediction, audio = audio, presence_penalty = presence_penalty, frequency_penalty = frequency_penalty,
                                logit_bias = logit_bias, user = user, seed = seed, logprobs = logprobs, top_logprobs = top_logprobs,
                                deployment_id = deployment_id, extra_headers = extra_headers, functions = functions, function_call = function_call,
                                api_version = api_version, model_list = model_list, loader = False
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
                            for j, prev_instance in enumerate(results[-min(3, i):], 1):
                                field_context += f"{j}. {getattr(prev_instance, field_name)}\n"
                            field_context += "\nPlease generate a different value."
                        
                        FieldModel = create_model("FieldResponse", value=(field.annotation, ...))
                        
                        response = await cls_or_self.model_acompletion(
                            context=context + "\n\n" + field_context if context else field_context,
                            messages = messages, model = model, 
                            mode = mode, response_model = FieldModel, verbose = verbose,
                            tools = tools, run_tools = run_tools, tool_choice = tool_choice, parallel_tool_calls = parallel_tool_calls,
                            api_key = api_key, base_url = base_url, organization = organization, n = n, stream = stream,
                            timeout = timeout, temperature = temperature, top_p = top_p, stream_options = stream_options, stop = stop,
                            max_completion_tokens = max_completion_tokens, max_tokens = max_tokens, modalities = modalities,
                            prediction = prediction, audio = audio, presence_penalty = presence_penalty, frequency_penalty = frequency_penalty,
                            logit_bias = logit_bias, user = user, seed = seed, logprobs = logprobs, top_logprobs = top_logprobs,
                            deployment_id = deployment_id, extra_headers = extra_headers, functions = functions, function_call = function_call,
                            api_version = api_version, model_list = model_list, loader = False
                        )
                        
                        instance[field_name] = response.value
                
                # Create complete instance and add to results
                if fields:

                    # Create field-specific model instance using the model class
                    if verbose:
                        console.message(f"Creating field-specific model instance for {field_name} using the model class")

                    field_instance = field_model.model_validate(instance)  # Use model_validate instead of constructor
                    results.append(field_instance)
                else:
                    results.append(cls(**instance))
            
            # build final models
            if fields and not isinstance(cls_or_self, type):
                if verbose:
                    console.message("Updating original model with generated values")
                    
                    # Create copies of original model for each result
                    original_models = [deepcopy(cls_or_self) for _ in range(len(results))]  # Use results instead of response.items
                    
                    # Update each copy with corresponding generated values
                    for i, original_model in enumerate(original_models):
                        for field in fields:
                            setattr(original_model, field, getattr(results[i], field))  # Use results instead of response.items
                            if verbose:
                                console.message(f"Setting {field} to {getattr(original_model, field)} for result {i+1}")
                    
                    # Return updated models
                    return original_models[0] if n == 1 else original_models

            return results[0] if n == 1 else results


# -------------------------------------------------------------------------------------------------
# PATCH
# -------------------------------------------------------------------------------------------------


def patch(model: Union[Type[PydanticBaseModel], PydanticBaseModel]) -> Union[Type[BaseModelMixinType], BaseModelMixinType]:
    if isinstance(model, type) and issubclass(model, PydanticBaseModel):
        # Create a dynamic subclass without renaming it to 'PatchedModel'
        PatchedModel = type(
            model.__name__,  # Use the original class name
            (model, BaseModelMixin),
            {"__annotations__": model.__annotations__}  # Preserve original annotations
        )
        return PatchedModel
    elif isinstance(model, PydanticBaseModel):
        # Dynamically extend the instance’s class with BaseModelMixin
        model.__class__ = type(
            model.__class__.__name__,  # Use the instance's original class name
            (model.__class__, BaseModelMixin),
            {"__annotations__": model.__class__.__annotations__}  # Preserve original annotations
        )
        return model
    else:
        raise TypeError("The patch function expects a Pydantic BaseModel class or instance.")
    

def unpatch(model: Union[Type[PydanticBaseModel], PydanticBaseModel]) -> Union[Type[BaseModelMixinType], BaseModelMixinType]:
    if isinstance(model, type) and issubclass(model, PydanticBaseModel):
        return model.__base__
    elif isinstance(model, PydanticBaseModel):
        return model.__class__.__base__
    

# -------------------------------------------------------------------------------------------------
# EXPORTS
# -------------------------------------------------------------------------------------------------

class BaseModel(PydanticBaseModel, BaseModelMixin):
    pass

# -------------------------------------------------------------------------------------------------
# TESTS
# -------------------------------------------------------------------------------------------------

    
# tests
if __name__ == "__main__":

    @patch
    class Test(PydanticBaseModel):
        name : str
        age : int

    patched = patch(Test)


    test2 = Test(name="John", age=30)

    test2 = patch(test2)

    # generate
    model = test2.model_generate(n=2, process="sequential", fields=["name"], verbose=True)

    print(model)