# llm based structured extraction

from ...lib import console, XNANOException

from pydantic import BaseModel, create_model
from ..completions.main import completion, async_completion
from ...types.completions.params import (
    CompletionChatModelsParam,
    CompletionInstructorModeParam,
)
from typing import List, Literal, Optional, Type, Union
from rich.progress import Progress, SpinnerColumn, TextColumn


def generate_extraction(
    target: Type[BaseModel],
    text: Union[str, List[str]],
    model: Union[str, CompletionChatModelsParam] = "gpt-4o-mini",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    organization: Optional[str] = None,
    max_tokens: Optional[int] = None,
    max_completion_tokens: Optional[int] = None,
    max_retries: int = 3,
    temperature: float = 0,
    mode: CompletionInstructorModeParam = "tool_call",
    process: Literal["single", "batch"] = "single",
    batch_size: int = 3,
    verbose: bool = False,
    progress_bar: Optional[bool] = True,
) -> Union[BaseModel, List[BaseModel]]:
    """An LLM abstraction for extracting structured information from text.

    Example:
        ```python
        import zyx

        class User(BaseModel):
            name: str
            age: int

        zyx.extract(User, "John is 20 years old")
        ```

    Args:
        target (Type[BaseModel]): The Pydantic model to extract information into.
        text (Union[str, List[str]]): The text to extract information from.
        client (Literal["litellm", "openai"]): The client to use for extraction. Defaults to "openai".
        model (str): The model to use for extraction. Defaults to "gpt-4o-mini".
        api_key (Optional[str]): The API key to use for OpenAI. Defaults to None.
        base_url (Optional[str]): The base URL for the OpenAI API. Defaults to None.
        organization (Optional[str]): The organization to use for OpenAI. Defaults to None.
        max_tokens (Optional[int]): The maximum number of tokens to use for extraction. Defaults to None.
        max_retries (int): The maximum number of retries to attempt. Defaults to 3.
        temperature (float): The temperature to use for extraction. Defaults to 0.
        mode (InstructorMode): The mode to use for extraction. Defaults to "markdown_json_mode".
        process (Literal["single", "batch"]): The process to use for extraction. Defaults to "single".
        batch_size (int): The number of texts to extract information from at a time. Defaults to 3.
        verbose (bool): Whether to print verbose output. Defaults to False.

    Returns:
        Union[BaseModel, List[BaseModel]]: The extracted information.
    """

    if isinstance(text, str):
        text = [text]

    if verbose:
        console.message(
            f"Extracting information from {len(text)} text(s) into {target.__name__} model."
        )
        console.message(f"Using model: {model}")
        console.message(f"Batch size: {batch_size}")
        console.message(f"Process: {process}")

    system_message = f"""
    You are an information extractor. Your task is to extract relevant information from the given text
    and fit it into the following Pydantic model:

    {target.model_json_schema()}

    Instructions:
    - Only Extract information from the text and fit it into the given model.
    - Do not infer or generate any information that is not present in the input text.
    - If a required field cannot be filled with information from the text, leave it as None or an empty string as appropriate.
    """

    results = []

    if progress_bar:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task_id = progress.add_task("Extracting...", total=len(text))

            if process == "single":
                response_model = target

                for i in range(0, len(text), batch_size):
                    batch = text[i : i + batch_size]
                    user_message = "Extract information from the following text(s) and fit it into the given model:\n\n"
                    for idx, t in enumerate(batch, 1):
                        user_message += f"{idx}. {t}\n\n"

                    result = completion(
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": user_message},
                        ],
                        model=model,
                        response_model=response_model,
                        max_completion_tokens=max_completion_tokens,
                        mode=mode,
                        temperature=temperature,
                        api_key=api_key,
                        base_url=base_url,
                        organization=organization,
                    )

                    results.append(result)
                    progress.update(task_id, advance=len(batch))

                return results if len(results) > 1 else results[0]
            else:  # batch process
                for i in range(0, len(text), batch_size):
                    batch = text[i : i + batch_size]
                    batch_message = "Extract information from the following texts and fit it into the given model:\n\n"
                    for idx, t in enumerate(batch, 1):
                        batch_message += f"{idx}. {t}\n\n"

                    response_model = create_model(
                        "ResponseModel", items=(List[target], ...)
                    )

                    result = completion(
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": batch_message},
                        ],
                        model=model,
                        response_model=response_model,
                        max_completion_tokens=max_completion_tokens,
                        mode=mode,
                        temperature=temperature,
                        api_key=api_key,
                        base_url=base_url,
                        organization=organization,
                    )

                    results.extend(result.items)
                    progress.update(task_id, advance=len(batch))

                return results
    else:
        if process == "single":
            response_model = target

            for i in range(0, len(text), batch_size):
                batch = text[i : i + batch_size]
                user_message = "Extract information from the following text(s) and fit it into the given model:\n\n"
                for idx, t in enumerate(batch, 1):
                    user_message += f"{idx}. {t}\n\n"

                result = completion(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message},
                    ],
                    model=model,
                    response_model=response_model,
                    max_completion_tokens=max_completion_tokens,
                    mode=mode,
                    temperature=temperature,
                    api_key=api_key,
                    base_url=base_url,
                    organization=organization,
                )

                results.append(result)

            return results if len(results) > 1 else results[0]
        else:  # batch process
            for i in range(0, len(text), batch_size):
                batch = text[i : i + batch_size]
                batch_message = "Extract information from the following texts and fit it into the given model:\n\n"
                for idx, t in enumerate(batch, 1):
                    batch_message += f"{idx}. {t}\n\n"

                response_model = create_model(
                    "ResponseModel", items=(List[target], ...)
                )

                result = completion(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": batch_message},
                    ],
                    model=model,
                    response_model=response_model,
                    max_completion_tokens=max_completion_tokens,
                    mode=mode,
                    temperature=temperature,
                    api_key=api_key,
                    base_url=base_url,
                    organization=organization,
                )

                results.extend(result.items)

            return results


async def async_generate_extraction(
    target: Type[BaseModel],
    text: Union[str, List[str]],
    model: Union[str, CompletionChatModelsParam] = "gpt-4o-mini",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    organization: Optional[str] = None,
    max_tokens: Optional[int] = None,
    max_completion_tokens: Optional[int] = None,
    max_retries: int = 3,
    temperature: float = 0,
    mode: CompletionInstructorModeParam = "tool_call",
    process: Literal["single", "batch"] = "single",
    batch_size: int = 3,
    verbose: bool = False,
    progress_bar: Optional[bool] = True,
) -> Union[BaseModel, List[BaseModel]]:
    """An LLM abstraction for extracting structured information from text.

    Example:
        ```python
        import zyx

        class User(BaseModel):
            name: str
            age: int

        zyx.extract(User, "John is 20 years old")
        ```

    Args:
        target (Type[BaseModel]): The Pydantic model to extract information into.
        text (Union[str, List[str]]): The text to extract information from.
        client (Literal["litellm", "openai"]): The client to use for extraction. Defaults to "openai".
        model (str): The model to use for extraction. Defaults to "gpt-4o-mini".
        api_key (Optional[str]): The API key to use for OpenAI. Defaults to None.
        base_url (Optional[str]): The base URL for the OpenAI API. Defaults to None.
        organization (Optional[str]): The organization to use for OpenAI. Defaults to None.
        max_tokens (Optional[int]): The maximum number of tokens to use for extraction. Defaults to None.
        max_retries (int): The maximum number of retries to attempt. Defaults to 3.
        temperature (float): The temperature to use for extraction. Defaults to 0.
        mode (InstructorMode): The mode to use for extraction. Defaults to "markdown_json_mode".
        process (Literal["single", "batch"]): The process to use for extraction. Defaults to "single".
        batch_size (int): The number of texts to extract information from at a time. Defaults to 3.
        verbose (bool): Whether to print verbose output. Defaults to False.

    Returns:
        Union[BaseModel, List[BaseModel]]: The extracted information.
    """

    if isinstance(text, str):
        text = [text]

    if verbose:
        console.message(
            f"Extracting information from {len(text)} text(s) into {target.__name__} model."
        )
        console.message(f"Using model: {model}")
        console.message(f"Batch size: {batch_size}")
        console.message(f"Process: {process}")

    system_message = f"""
    You are an information extractor. Your task is to extract relevant information from the given text
    and fit it into the following Pydantic model:

    {target.model_json_schema()}

    Instructions:
    - Only Extract information from the text and fit it into the given model.
    - Do not infer or generate any information that is not present in the input text.
    - If a required field cannot be filled with information from the text, leave it as None or an empty string as appropriate.
    """

    results = []

    if progress_bar:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task_id = progress.add_task("Extracting...", total=len(text))

            if process == "single":
                response_model = target

                for i in range(0, len(text), batch_size):
                    batch = text[i : i + batch_size]
                    user_message = "Extract information from the following text(s) and fit it into the given model:\n\n"
                    for idx, t in enumerate(batch, 1):
                        user_message += f"{idx}. {t}\n\n"

                    result = await async_completion(
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": user_message},
                        ],
                        model=model,
                        response_model=response_model,
                        max_completion_tokens=max_completion_tokens,
                        mode=mode,
                        temperature=temperature,
                        api_key=api_key,
                        base_url=base_url,
                        organization=organization,
                    )

                    results.append(result)
                    progress.update(task_id, advance=len(batch))

                return results if len(results) > 1 else results[0]
            else:  # batch process
                for i in range(0, len(text), batch_size):
                    batch = text[i : i + batch_size]
                    batch_message = "Extract information from the following texts and fit it into the given model:\n\n"
                    for idx, t in enumerate(batch, 1):
                        batch_message += f"{idx}. {t}\n\n"

                    response_model = create_model(
                        "ResponseModel", items=(List[target], ...)
                    )

                    result = await async_completion(
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": batch_message},
                        ],
                        model=model,
                        response_model=response_model,
                        max_completion_tokens=max_completion_tokens,
                        mode=mode,
                        temperature=temperature,
                        api_key=api_key,
                        base_url=base_url,
                        organization=organization,
                    )

                    results.extend(result.items)
                    progress.update(task_id, advance=len(batch))

                return results
    else:
        if process == "single":
            response_model = target

            for i in range(0, len(text), batch_size):
                batch = text[i : i + batch_size]
                user_message = "Extract information from the following text(s) and fit it into the given model:\n\n"
                for idx, t in enumerate(batch, 1):
                    user_message += f"{idx}. {t}\n\n"

                result = await async_completion(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message},
                    ],
                    model=model,
                    response_model=response_model,
                    max_completion_tokens=max_completion_tokens,
                    mode=mode,
                    temperature=temperature,
                    api_key=api_key,
                    base_url=base_url,
                    organization=organization,
                )

                results.append(result)

            return results if len(results) > 1 else results[0]
        else:  # batch process
            for i in range(0, len(text), batch_size):
                batch = text[i : i + batch_size]
                batch_message = "Extract information from the following texts and fit it into the given model:\n\n"
                for idx, t in enumerate(batch, 1):
                    batch_message += f"{idx}. {t}\n\n"

                response_model = create_model(
                    "ResponseModel", items=(List[target], ...)
                )

                result = await async_completion(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": batch_message},
                    ],
                    model=model,
                    response_model=response_model,
                    max_completion_tokens=max_completion_tokens,
                    mode=mode,
                    temperature=temperature,
                    api_key=api_key,
                    base_url=base_url,
                    organization=organization,
                )

                results.extend(result.items)

            return results


if __name__ == "__main__":

    class User(BaseModel):
        name: str
        age: int

    text = ["John is 20 years old", "Alice is 30 years old", "Bob is 25 years old"]

    results = generate_extraction(User, text, process="batch", batch_size=2, verbose=True)
    for result in results:
        print(result)
