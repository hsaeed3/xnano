# agent
# base singular agent

from ..completions import completion
from ..types._openai import ChatCompletionModality, ChatCompletionPredictionContentParam, ChatCompletionAudioParam
from ..types.completions.completions_arguments import CompletionsArguments
from ..types.context.context import Context
from ..types.chat_models.chat_model import ChatModel
from ..types.instructor.instructor_mode import InstructorMode
from ..types.messages.message_type import MessageType
from ..types.responses.response import Response
from ..types.responses.response_model_type import ResponseModelType
from ..types.tools.tool_choice import ToolChoice
from ..types.tools.tool_type import ToolType

import httpx
import json
from typing import Optional, List, Union


class Agent:

    def __init__(
            self,
            messages : Optional[MessageType] = [],
            model : Optional[ChatModel] = "gpt-4o-mini",
            tools : Optional[ToolType] = None,
            context : Optional[Context] = None,
    ):
        
        self.messages = messages
        self.model = model
        self.tools = tools
        self.context = context


    def completion(
            self,
            messages : Optional[MessageType] = None,
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
            stream : Optional[bool] = None,
            return_messages : Optional[bool] = None,
    ) -> Response:
        
        if self.context is not None:
            if context is not None:
                context = f"{json.loads(self.context)} \n\n {json.loads(context)}"
            else:
                context = self.context

        if self.tools is not None:
            if tools is not None:
                tools = self.tools.extend(tools)
            else:
                tools = self.tools
        

        if isinstance(messages, str):
            self.messages.append({"role": "user", "content": messages})
        elif isinstance(messages, list):
            self.messages.extend(messages)
        else:
            raise ValueError("messages must be a string or list")
        
        response = completion(
            messages=self.messages,
            model=model,
            response_model=response_model,
            mode=mode,
            tools = tools,
            run_tools = run_tools,
            tool_choice = tool_choice,
            parallel_tool_calls = parallel_tool_calls,
            api_key = api_key,
            base_url = base_url,
            organization = organization,
            n = n,
            timeout = timeout,
            temperature = temperature,
            top_p = top_p,
            stream_options = stream_options,
            stop = stop,
            max_completion_tokens = max_completion_tokens,
            max_tokens = max_tokens,
            modalities = modalities,
            prediction = prediction,
            audio = audio,
            presence_penalty = presence_penalty,
            frequency_penalty = frequency_penalty,
            logit_bias = logit_bias,
            user = user,
            seed = seed,
            logprobs = logprobs,
            top_logprobs = top_logprobs,
            deployment_id = deployment_id,
            extra_headers = extra_headers,
            functions = functions,
            function_call = function_call,
            api_version = api_version,
            model_list = model_list,
            return_messages = return_messages,
            stream = stream,
        )

        if response_model is not None and response_format is not None:
            self.messages.append({"role": "assistant", "content": str(response)})
        elif isinstance(response, list) and len(response) > 1:
            self.messages.extend(r.choices[0].message.model_dump for r in response)
        else:
            self.messages.append(response.choices[0].message.model_dump())

        return response