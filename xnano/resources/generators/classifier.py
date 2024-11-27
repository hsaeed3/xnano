from ...lib import console, XNANOException

from pydantic import BaseModel, create_model
from ..completions.main import completion, async_completion
from ...types.completions.params import (
    CompletionChatModelsParam,
    CompletionInstructorModeParam,
)
from typing import List, Literal, Optional, Union
from rich.progress import Progress, SpinnerColumn, TextColumn


class ClassificationResult(BaseModel):
    text: str
    label: str
    confidence: Optional[float] = None

class MultiClassificationResult(BaseModel):
    text: str
    labels: List[str]
    confidences: Optional[List[float]] = None


def generate_classification(
    inputs: Union[str, List[str]],
    labels: List[str],
    classification: Literal["single", "multi"] = "single",
    n: int = 1,
    batch_size: int = 3,
    model: Union[str, CompletionChatModelsParam] = "gpt-4o-mini",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    organization: Optional[str] = None,
    mode: CompletionInstructorModeParam = "tool_call",
    temperature: Optional[float] = None,
    progress_bar: Optional[bool] = True,
    verbose: bool = False,
) -> Union[ClassificationResult, List[ClassificationResult],
           MultiClassificationResult, List[MultiClassificationResult]]:
    """
    Classifies given input(s) into one or more of the provided labels.

    Examples:
        >>> classify(["I love programming in Python", "I like french fries", "I love programming in Julia"], ["code", "food"], classification = "single", batch_size = 2, verbose = True)
        [
            ClassificationResult(text="I love programming in Python", label="code"),
            ClassificationResult(text="I like french fries", label="food")
        ]

    Returns a ClassificationResult or List[ClassificationResult] depending on the classification type and batch size.

    ClassificationResult:
        text: The original input text.
        label: The single label that the input text was classified into.
        confidence: The confidence score of the classification.

    Args:
        inputs (Union[str, List[str]]): The input text to classify.
        labels (List[str]): The list of labels to classify the input text into.
        classification (Literal["single", "multi"]): The type of classification to perform. Defaults to "single".
        n (int): The number of classifications to generate. Defaults to 1.
        batch_size (int): The number of inputs to classify at a time. Defaults to 3.
        model (str): The model to use for classification. Defaults to "gpt-4o-mini".
        api_key (Optional[str]): The API key to use for OpenAI. Defaults to None.
        base_url (Optional[str]): The base URL for the OpenAI API. Defaults to None.
        organization (Optional[str]): The organization to use for OpenAI. Defaults to None.
        mode (InstructorMode): The mode to use for classification. Defaults to "tool_call".
        temperature (Optional[float]): The temperature to use for classification. Defaults to None.
        provider (Optional[Literal["openai", "litellm"]]): The provider to use for classification. Defaults to "openai".
        verbose (bool): Whether to print verbose output. Defaults to False.
        progress_bar (Optional[bool]): Whether to print a progress bar. Defaults to True.

    Returns:
        List[Union[ClassificationResult, MultiClassificationResult]]: The classifications generated.
    """

    if verbose:
        console.message(f"Classifying {len(inputs)} inputs into {len(labels)} labels.")
        console.message(f"Using model: {model}")
        console.message(f"Batch size: {batch_size}")
        console.message(f"Classification Mode: {classification}")

    if classification == "single":
        system_message = f"""
You are a world class text classifier. Your task is to classify given text into exactly one of these categories:
{', '.join(labels)}

Critical Instructions:
- You must assign exactly ONE label per text
- Choose the most relevant/dominant category
- The label must be from the provided list
- Return both the original text and your classification
- Format: Each response must include the text and single chosen label

Example format:
{{
    "text": "input text here",
    "label": "chosen_label"
}}
"""
        if batch_size == 1:
            response_model = ClassificationResult
        elif batch_size > 1:
            response_model = create_model(
                "ClassificationResult", items=(List[ClassificationResult], ...)
            )
        else:
            raise ValueError("Batch size must be a positive integer.")
    else:
        system_message = f"""
You are a world class text classifier. Your task is to classify given text into ANY applicable categories from:
{', '.join(labels)}

Critical Instructions:
- Assign ALL relevant labels that apply to each text
- A text can have multiple labels (minimum 1, maximum {len(labels)})
- Only use labels from the provided list
- Return both the original text and all applicable labels
- Format: Each response must include the text and array of chosen labels

Example format:
{{
    "text": "input text here",
    "labels": ["label1", "label2"]  # All applicable labels
}}
"""
        if batch_size == 1:
            response_model = MultiClassificationResult
        elif batch_size > 1:
            response_model = create_model(
                "ClassificationResult", items=(List[MultiClassificationResult], ...)
            )
        else:
            raise ValueError("Batch size must be a positive integer.")

    def create_user_message(batch):
        msg = f"Please perform {classification}-label classification on the following text(s):\n\n"
        for idx, text in enumerate(batch, 1):
            msg += f"{idx}. {text}\n\n"
        if classification == "single":
            msg += "\nRemember: Assign exactly ONE label per text."
        else:
            msg += "\nRemember: Assign ALL applicable labels per text."
        return msg

    if isinstance(inputs, str):
        inputs = [inputs]

    results = []

    if progress_bar:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task_id = progress.add_task("Classifying...", total=len(inputs))

            for i in range(0, len(inputs), batch_size):
                batch = inputs[i : i + batch_size]
                user_message = create_user_message(batch)

                result = completion(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message},
                    ],
                    model=model,
                    response_model=response_model,
                    mode=mode,
                    temperature=temperature,
                    n=n,
                    api_key=api_key,
                    base_url=base_url,
                    organization=organization,
                )

                if batch_size == 1:
                    results.append(result)
                else:
                    results.extend(result.items)

                progress.update(task_id, advance=len(batch))
    else:
        for i in range(0, len(inputs), batch_size):
            batch = inputs[i : i + batch_size]
            user_message = create_user_message(batch)

            result = completion(
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
                model=model,
                response_model=response_model,
                mode=mode,
                temperature=temperature,
                n=n,
                api_key=api_key,
                base_url=base_url,
                organization=organization,
            )

            if batch_size == 1:
                results.append(result)
            else:
                results.extend(result.items)

    return results if len(results) > 1 else results[0]


# -------------------------------------------------------------------------------------------------
# async
# -------------------------------------------------------------------------------------------------
async def async_generate_classification(
    inputs: Union[str, List[str]],
    labels: List[str],
    classification: Literal["single", "multi"] = "single",
    n: int = 1,
    batch_size: int = 3,
    model: Union[str, CompletionChatModelsParam] = "gpt-4o-mini",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    organization: Optional[str] = None,
    mode: CompletionInstructorModeParam = "tool_call",
    temperature: Optional[float] = None,
    progress_bar: Optional[bool] = True,
    verbose: bool = False,
) -> List:
    """
    Classifies given input(s) into one or more of the provided labels.

    Examples:
        >>> classify(["I love programming in Python", "I like french fries", "I love programming in Julia"], ["code", "food"], classification = "single", batch_size = 2, verbose = True)
        [
            ClassificationResult(text="I love programming in Python", label="code"),
            ClassificationResult(text="I like french fries", label="food")
        ]

    Args:
        inputs (Union[str, List[str]]): The input text to classify.
        labels (List[str]): The list of labels to classify the input text into.
        classification (Literal["single", "multi"]): The type of classification to perform. Defaults to "single".
        n (int): The number of classifications to generate. Defaults to 1.
        batch_size (int): The number of inputs to classify at a time. Defaults to 3.
        model (str): The model to use for classification. Defaults to "gpt-4o-mini".
        api_key (Optional[str]): The API key to use for OpenAI. Defaults to None.
        base_url (Optional[str]): The base URL for the OpenAI API. Defaults to None.
        organization (Optional[str]): The organization to use for OpenAI. Defaults to None.
        mode (InstructorMode): The mode to use for classification. Defaults to "tool_call".
        temperature (Optional[float]): The temperature to use for classification. Defaults to None.
        provider (Optional[Literal["openai", "litellm"]]): The provider to use for classification. Defaults to "openai".
        verbose (bool): Whether to print verbose output. Defaults to False.
        progress_bar (Optional[bool]): Whether to print a progress bar. Defaults to True.

    Returns:
        List[Union[ClassificationResult, MultiClassificationResult]]: The classifications generated.
    """

    if verbose:
        console.message(f"Classifying {len(inputs)} inputs into {len(labels)} labels.")
        console.message(f"Using model: {model}")
        console.message(f"Batch size: {batch_size}")
        console.message(f"Classification Mode: {classification}")

    class ClassificationResult(BaseModel):
        text: str
        label: str
        confidence: Optional[float] = None

    class MultiClassificationResult(BaseModel):
        text: str
        labels: List[str]
        confidences: Optional[List[float]] = None

    if classification == "single":
        system_message = f"""
You are a world class text classifier. Your task is to classify given text into exactly one of these categories:
{', '.join(labels)}

Critical Instructions:
- You must assign exactly ONE label per text
- Choose the most relevant/dominant category
- The label must be from the provided list
- Return both the original text and your classification
- Format: Each response must include the text and single chosen label

Example format:
{{
    "text": "input text here",
    "label": "chosen_label"
}}
"""
        if batch_size == 1:
            response_model = ClassificationResult
        elif batch_size > 1:
            response_model = create_model(
                "ClassificationResult", items=(List[ClassificationResult], ...)
            )
        else:
            raise ValueError("Batch size must be a positive integer.")
    else:
        system_message = f"""
You are a world class text classifier. Your task is to classify given text into ANY applicable categories from:
{', '.join(labels)}

Critical Instructions:
- Assign ALL relevant labels that apply to each text
- A text can have multiple labels (minimum 1, maximum {len(labels)})
- Only use labels from the provided list
- Return both the original text and all applicable labels
- Format: Each response must include the text and array of chosen labels

Example format:
{{
    "text": "input text here",
    "labels": ["label1", "label2"]  # All applicable labels
}}
"""
        if batch_size == 1:
            response_model = MultiClassificationResult
        elif batch_size > 1:
            response_model = create_model(
                "ClassificationResult", items=(List[MultiClassificationResult], ...)
            )
        else:
            raise ValueError("Batch size must be a positive integer.")

    def create_user_message(batch):
        msg = f"Please perform {classification}-label classification on the following text(s):\n\n"
        for idx, text in enumerate(batch, 1):
            msg += f"{idx}. {text}\n\n"
        if classification == "single":
            msg += "\nRemember: Assign exactly ONE label per text."
        else:
            msg += "\nRemember: Assign ALL applicable labels per text."
        return msg

    if isinstance(inputs, str):
        inputs = [inputs]

    results = []

    if progress_bar:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task_id = progress.add_task("Classifying...", total=len(inputs))

            for i in range(0, len(inputs), batch_size):
                batch = inputs[i : i + batch_size]
                user_message = create_user_message(batch)

                result = await async_completion(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message},
                    ],
                    model=model,
                    response_model=response_model,
                    mode=mode,
                    temperature=temperature,
                    api_key=api_key,
                    base_url=base_url,
                    organization=organization,
                )

                if batch_size == 1:
                    results.append(result)
                else:
                    results.extend(result.items)

                progress.update(task_id, advance=len(batch))
    else:
        for i in range(0, len(inputs), batch_size):
            batch = inputs[i : i + batch_size]
            user_message = create_user_message(batch)

            result = await async_completion(
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
                model=model,
                response_model=response_model,
                mode=mode,
                temperature=temperature,
                progress_bar=progress_bar,
            )

            if batch_size == 1:
                results.append(result)
            else:
                results.extend(result.items)

    return results if len(results) > 1 else results[0]


if __name__ == "__main__":
    items = [
        "I love programming in Python",
        "I like french fries",
        "I love programming in Julia",
    ]

    labels = ["code", "food"]

    print(generate_classification(items, labels, classification="single", batch_size=2, verbose=True))
