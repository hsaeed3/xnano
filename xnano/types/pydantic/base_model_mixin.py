# basemodel type

from pydantic import BaseModel as PydanticBaseModel
import httpx
from typing import TypeVar, Union, Optional, List
from .base_model_generation_process import BaseModelGenerationProcess
from ..openai import ChatCompletionModality, ChatCompletionPredictionContentParam, ChatCompletionAudioParam, ChatCompletion
from ..completions.context import Context
from ..completions.chat_models import ChatModel
from ..completions.instructor import InstructorMode
from ..completions.messages import MessageType
from ..completions.response_models import ResponseModelType
from ..completions.tools import ToolChoice, ToolType


# typevar
T = TypeVar('T', bound='BaseModelMixin')


class BaseModelMixin(PydanticBaseModel):
    ...

    @classmethod
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
        T,
        List[T],
        ChatCompletion,
        List[ChatCompletion],
    ]:
        ...
    

    @classmethod
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
        T,
        List[T],
        ChatCompletion,
        List[ChatCompletion],
    ]:
        ...


    @classmethod
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
    ) -> Union[T, List[T]]:
        ...


    @classmethod
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
    ) -> Union[T, List[T]]:
        ...