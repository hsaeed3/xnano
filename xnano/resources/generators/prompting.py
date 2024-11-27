from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field, create_model
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..completions.main import completion
from ...lib import console
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
from ..completions.resources.messages import swap_system_prompt
from ...types.completions.messages import Message


PROMPT_TYPES = Literal["costar", "tidd-ec", "instruction", "reasoning"]


class Prompts:
    costar = """
## CONTEXT ##

You are a world class COSTAR prompt creator & engineer.
The COSTAR is a framework that offers a structured approach to prompt creation. This method ensures all key aspects influencing an LLM’s response are considered, resulting in more tailored and impactful output responses.

The COSTAR Framework Explained:
- Context : Providing background information helps the LLM understand the specific scenario.
- Objective (O): Clearly defining the task directs the LLM’s focus.
- Style (S): Specifying the desired writing style aligns the LLM response.
- Tone (T): Setting the tone ensures the response resonates with the required sentiment.
- Audience (A): Identifying the intended audience tailors the LLM’s response to be targeted to an audience.
- Response_Format (R): Providing the response format, like text or json, ensures the LLM outputs, and help build pipelines.

## INSTRUCTIONS ##

- Identify what the user is trying to achieve according to their latest message(s).
- Identify the context of the user's message(s).
- Generate the apprpriate block of text for the COSTAR system prompt, creating a character or persona, that will aid the LLM in achieving the user's objective.

Your response does not always have to include every component of the COSTAR framework, but your prompt should be well-writen, and easy for the LLM to understand.
    """
    tidd_ec = """
## CONTEXT ##

You are a world class Tidd-EC prompt creator & engineer.
The Tidd-EC is a framework that offers a structured approach to prompt creation. This method ensures all key aspects influencing an LLM’s response are considered, resulting in more tailored and impactful output responses.

The Tidd-EC Framework Explained:
- Task : Providing background information helps the LLM understand the specific scenario.
- Instructions : Clearly defining the task directs the LLM’s focus.
- Do : Specifying the desired writing style aligns the LLM response.
- Donts : Setting the tone ensures the response resonates with the required sentiment.

## INSTRUCTIONS ##

- Identify what the user is trying to achieve according to their latest message(s).
- Identify the context of the user's message(s).
- Generate the apprpriate block of text for the COSTAR system prompt, creating a character or persona, that will aid the LLM in achieving the user's objective.

Your response does not always have to include every component of the COSTAR framework, but your prompt should be well-writen, and easy for the LLM to understand.
"""
    instruction = """
## CONTEXT ##

You are a world-class instruction generator, specializing in creating clear, concise, and actionable bullet-point instructions.

## INSTRUCTIONS ##

- Analyze the user's request or task description.
- Generate a comprehensive set of bullet-point instructions that address the user's needs.
- Ensure each instruction is clear, specific, and actionable.
- Organize instructions in a logical sequence.
- Use concise language while maintaining clarity.
- Include any necessary warnings or precautions as separate bullet points.

Your response should be a well-structured list of instructions that guide the user through the task or process effectively.
    """
    reasoning = """
## CONTEXT ##

You are an expert in creating step-by-step reasoning processes, designed to break down complex problems or tasks into logical, sequential steps.

## INSTRUCTIONS ##

- Carefully analyze the user's problem or task.
- Create a structured list of reasoning steps or phases that address the problem.
- Ensure each step builds logically on the previous ones.
- Include explanatory notes for each step if necessary.
- Consider potential branching paths in the reasoning process.
- Conclude with a step that synthesizes the reasoning or reaches a conclusion.

Your response should be a clear, logical sequence of reasoning steps that guide through the problem-solving or decision-making process.
    """


class CostarSystemPrompt(BaseModel):
    context: Optional[str] = Field(
        ...,
        description="Provide background information to help the LLM understand the specific scenario. If given, must be minimum 4 sentences.",
    )
    objective: Optional[str] = Field(
        ...,
        description="The objective of the user defined task that the LLM is supposed to complete. If given, must be minimum 4 sentences.",
    )
    style: Optional[str] = Field(
        ...,
        description="The user-intended writing style of the response, intended to be produced by the LLM. If given, must be minimum 2 sentences.",
    )
    tone: Optional[str] = Field(
        ...,
        description="The tone of the response, something to help the response resonate with the required sentiment. If given, must be minimum 2 sentences.",
    )
    audience: Optional[str] = Field(
        ...,
        description="The intended audience of the response. If given, must be minimum 2 sentences.",
    )
    response_format: Optional[str] = Field(
        ...,
        description="Examples and desired outcome of the response. If given, must be minimum 2 sentences.",
    )


class TiddECSystemPrompt(BaseModel):
    task: Optional[str] = Field(
        ...,
        description="The description of the character the LLM is supposed to play, as well as the context of the scenario. If given, must be minimum 200 tokens.",
    )
    instructions: Optional[list[str]] = Field(
        ...,
        description="The instructions for the LLM to follow. Must be clear and consise. If given, must be minimum 200 tokens.",
    )
    do: Optional[list[str]] = Field(
        ...,
        description="Specifies actions the LLM should take to successfully complete the prompt. This includes the use of certain language, structures, or information that should be included in the response. Each item must be minimum 20 tokens.",
    )
    donts: Optional[list[str]] = Field(
        ...,
        description="Highlights actions or elements the LLM should avoid in its response. This is essential for preventing common errors or misinterpretations that could lead to inaccurate or irrelevant outputs. Each item must be minimum 20 tokens.",
    )
    examples: Optional[list[str]] = Field(
        ...,
        description="Provides concrete examples of desired outcomes or responses. This component is invaluable for guiding the LLM towards the expected format, style, or content of the response. Each item must be minimum 20 tokens.",
    )


class InstructionSystemPrompt(BaseModel):
    instructions: List[str] = Field(
        ...,
        description="A list of clear, concise, and actionable bullet-point instructions. Each instruction must be minimum 10 tokens.",
    )
    warnings: Optional[List[str]] = Field(
        None,
        description="Optional list of warnings or precautions related to the instructions. Each warning must be minimum 10 tokens.",
    )


class ReasoningSystemPrompt(BaseModel):
    steps: List[str] = Field(
        ...,
        description="A list of sequential reasoning steps or phases. Each step must be minimum 20 tokens.",
    )
    explanations: Optional[List[str]] = Field(
        None,
        description="Optional list of explanations for each step. Each explanation must be minimum 20 tokens.",
    )
    conclusion: str = Field(
        ...,
        description="A concluding statement or final step that synthesizes the reasoning process. Must be minimum 30 tokens.",
    )


PROMPT_TYPES_MAPPING = {
    "costar": CostarSystemPrompt,
    "tidd-ec": TiddECSystemPrompt,
    "instruction": InstructionSystemPrompt,
    "reasoning": ReasoningSystemPrompt,
}


def get_system_prompt(type: PROMPT_TYPES = "costar") -> dict[str, str]:
    prompt_content = getattr(Prompts, type.replace("-", "_"), None)
    if prompt_content is None:
        raise ValueError(f"Invalid prompt type: {type}")
    return {"role": "system", "content": prompt_content}


def get_response_model(type: PROMPT_TYPES = "costar") -> BaseModel:
    return PROMPT_TYPES_MAPPING[type]


def generate_system_prompt(
    instructions: Union[str, List[str]],
    type: PROMPT_TYPES = "costar",
    messages: Optional[List[Message]] = None,
    optimize: bool = False,
    process: Literal["sequential", "batch"] = "sequential",
    n: int = 1,
    batch_size: int = 3,
    model: Union[str, CompletionChatModelsParam] = "gpt-4o-mini",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    organization: Optional[str] = None,
    temperature: Optional[float] = None,
    mode: CompletionInstructorModeParam = "tool_call",
    max_retries: int = 3,
    max_tokens: Optional[int] = None,
    max_completion_tokens: Optional[int] = None,
    response_format: Union[Literal["pydantic"], Literal["dict"], None] = None,
    progress_bar: Optional[bool] = True,
    verbose: bool = False,
) -> Union[BaseModel, str, dict, List[Union[BaseModel, str, dict]], List[Message]]:
    if verbose:
        console.message(f"Generating system prompt for {type}")
        console.message(f"Optimize: {optimize}")
        console.message(f"Process: {process}")
        console.message(f"Number of prompts: {n}")
        console.message(f"Batch size: {batch_size}")

    response_model = get_response_model(type=type)
    system_prompt = get_system_prompt(type=type)

    if isinstance(instructions, str):
        instructions = [instructions]

    if optimize:
        instructions = [
            f"Optimize the following system prompt:\n\n{instr}"
            for instr in instructions
        ]

    results = []

    if progress_bar:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task_id = progress.add_task("Building Prompt...", total=len(instructions))

            if process == "sequential":
                for instr in instructions:
                    messages = [
                        system_prompt,
                        {
                            "role": "user",
                            "content": f"Generate a system prompt for the following instructions:\n\nINSTRUCTIONS:\n{instr}",
                        },
                    ]
                    if results:
                        messages.append(
                            {
                                "role": "assistant",
                                "content": f"Previously generated prompts:\n{results[-1]}",
                            }
                        )

                    result = completion(
                        messages=messages,
                        model=model,
                        response_model=response_model,
                        mode=mode,
                        max_retries=max_retries,
                        max_tokens=max_tokens,
                        max_completion_tokens=max_completion_tokens,
                        temperature=temperature,
                        api_key=api_key,
                        base_url=base_url,
                        organization=organization,
                        verbose=verbose,
                    )
                    results.append(result)
                    progress.update(task_id, advance=1)
            else:  # batch process
                for i in range(0, len(instructions), batch_size):
                    batch = instructions[i : i + batch_size]
                    batch_message = (
                        "Generate system prompts for the following instructions:\n\n"
                    )
                    for idx, instr in enumerate(batch, 1):
                        batch_message += f"{idx}. {instr}\n\n"

                    response_model_batch = create_model(
                        "ResponseModel", items=(List[response_model], ...)
                    )

                    result = completion(
                        messages=[
                            system_prompt,
                            {"role": "user", "content": batch_message},
                        ],
                        model=model,
                        response_model=response_model_batch,
                        mode=mode,
                        max_retries=max_retries,
                        max_tokens=max_tokens,
                        max_completion_tokens=max_completion_tokens,
                        temperature=temperature,
                        api_key=api_key,
                        base_url=base_url,
                        organization=organization,
                        verbose=verbose,
                    )

                    results.extend(result.items)
                    progress.update(task_id, advance=len(batch))
    else:
        if process == "sequential":
            for instr in instructions:
                messages = [
                    system_prompt,
                    {
                        "role": "user",
                        "content": f"Generate a system prompt for the following instructions:\n\nINSTRUCTIONS:\n{instr}",
                    },
                ]
                if results:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"Previously generated prompts:\n{results[-1]}",
                        }
                    )

                result = completion(
                    messages=messages,
                    model=model,
                    response_model=response_model,
                    mode=mode,
                    max_retries=max_retries,
                    max_tokens=max_tokens,
                    max_completion_tokens=max_completion_tokens,
                    temperature=temperature,
                    api_key=api_key,
                    base_url=base_url,
                    organization=organization,
                    verbose=verbose,
                )
                results.append(result)
        else:  # batch process
            for i in range(0, len(instructions), batch_size):
                batch = instructions[i : i + batch_size]
                batch_message = (
                    "Generate system prompts for the following instructions:\n\n"
                )
                for idx, instr in enumerate(batch, 1):
                    batch_message += f"{idx}. {instr}\n\n"

                response_model_batch = create_model(
                    "ResponseModel", items=(List[response_model], ...)
                )

                result = completion(
                    messages=[
                        system_prompt,
                        {"role": "user", "content": batch_message},
                    ],
                    model=model,
                    response_model=response_model_batch,
                    mode=mode,
                    max_retries=max_retries,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    api_key=api_key,
                    base_url=base_url,
                    organization=organization,
                    verbose=verbose,
                )

                results.extend(result.items)

    # Helper function to convert BaseModel to string
    def model_to_string(model_instance: BaseModel) -> str:
        response_string = []
        for field in model_instance.model_fields:
            value = getattr(model_instance, field, None)
            if isinstance(value, list):
                formatted_value = "\n".join(f"- {item}" for item in value)
            else:
                formatted_value = value
            response_string.append(f"## {field.capitalize()} ##\n{formatted_value}\n\n")
        return "\n".join(response_string)

    # Regenerate prompts to ensure second-person perspective
    regenerated_results = []
    for prompt in results:
        prompt_str = model_to_string(prompt)
        messages = [
            {
                "role": "system",
                "content": "Regenerate the following prompt to ensure it refers to the character in the second person (using 'you', 'your', etc.):\n\n"
                + prompt_str,
            }
        ]
        regenerated_prompt = completion(
            messages=messages,
            model=model,
            response_model=response_model,
            mode=mode,
            max_retries=max_retries,
            max_tokens=max_tokens,
            max_completion_tokens=max_completion_tokens,
            temperature=temperature,
            api_key=api_key,
            base_url=base_url,
            organization=organization,
            verbose=verbose,
        )
        regenerated_results.append(regenerated_prompt)

    # Format the regenerated results
    formatted_results = []
    for prompt in regenerated_results:
        formatted_results.append(model_to_string(prompt))

    # If messages were provided, swap the system prompt and return updated messages
    if messages is not None:
        result = (
            formatted_results[0] if len(formatted_results) == 1 else formatted_results
        )
        return swap_system_prompt(messages=messages, system_prompt=result)

    # Otherwise return the formatted results as before
    return formatted_results if len(formatted_results) > 1 else formatted_results[0]


if __name__ == "__main__":
    # Example usage
    instructions = [
        "Create a system prompt for a chatbot that helps users with programming questions.",
        "Generate a system prompt for an AI assistant that provides travel recommendations.",
    ]

    result = generate_system_prompt(
        instructions=instructions,
        type="costar",
        optimize=False,
        process="sequential",
        n=2,
        batch_size=2,
        verbose=True,
    )

    print("Generated System Prompts:")
    for idx, prompt in enumerate(result, 1):
        print(f"\nPrompt {idx}:")
        print(prompt)
