from typing import List, Optional, Union, Any, Literal
from pydantic import BaseModel, Field

from ..completions.main import completion, async_completion
from ...types.completions.params import (
    CompletionChatModelsParam,
    CompletionInstructorModeParam,
)
from ...lib import console, XNANOException


class AccuracyCheck(BaseModel):
    accurate: bool


class AccuracyScore(BaseModel):
    accuracy: float


class ExplanationCheck(BaseModel):
    explanation: str


class GuardrailsCheck(BaseModel):
    guardrails: float


class ValidationResult(BaseModel):
    accurate: Optional[bool] = None
    explanation: Optional[str] = None
    content: str
    accuracy: Optional[float] = None
    context: Optional[Any] = None
    violates_guardrails: bool = False


def generate_validation(
    inputs: Union[str, List[str]],
    context: Optional[Any] = None,
    guardrails: Optional[Union[str, List[str]]] = None,
    model: Union[str, CompletionChatModelsParam] = "gpt-4o-mini",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.7,
    mode: CompletionInstructorModeParam = "tool_call",
    max_retries: int = 3,
    organization: Optional[str] = None,
    loader: Optional[bool] = True,
    verbose: bool = False,
) -> Union[ValidationResult, List[ValidationResult]]:
    """
    Validates input(s) for accuracy, contextual relevance, and guardrail compliance.

    Args:
        inputs (Union[str, List[str]]): Input(s) to validate
        context (Optional[Any]): Reference context for validation
        guardrails (Optional[Union[str, List[str]]]): Content moderation rules
        model (Union[str, PredefinedModel]): Model to use for validation
        api_key (Optional[str]): API key for the LLM service
        base_url (Optional[str]): Base URL for the LLM service
        temperature (float): Temperature for response generation
        mode (InstructorMode): Mode for the instructor
        max_retries (int): Maximum number of retries for API calls
        organization (Optional[str]): Organization for the LLM service
        client (Optional[Literal["openai", "litellm"]]): Client to use for API calls
        verbose (bool): Whether to log verbose output

    Returns:
        Union[ValidationResult, List[ValidationResult]]: Validation results
    """

    # Convert single input to list for consistent processing
    if isinstance(inputs, str):
        inputs = [inputs]
        single_input = True
    else:
        single_input = False

    results = []

    if loader:
        with console.progress(
            "Validating inputs...",
        ) as progress:
            task_id = progress.add_task("Validating inputs...", total=len(inputs))

            for input_text in inputs:
                # Check guardrails first if provided
                if guardrails:
                    progress.update(
                        task_id,
                        description=f"Checking guardrails for: {input_text[:30]}...",
                    ) if loader else None

                    guardrails_list = (
                        [guardrails] if isinstance(guardrails, str) else guardrails
                    )
                    guardrails_prompt = "\n".join(guardrails_list)

                    system_message = (
                        "You are a content moderator. Rate how well the input adheres to the specified "
                        "guardrails from 0.0 to 1.0, where 1.0 means perfect compliance and 0.0 means "
                        "complete violation."
                    )

                    try:
                        guardrails_result = completion(
                            messages=[
                                {"role": "system", "content": system_message},
                                {
                                    "role": "user",
                                    "content": f"Input: {input_text}\n\nGuardrails:\n{guardrails_prompt}",
                                },
                            ],
                            model=model,
                            response_model=GuardrailsCheck,
                            mode=mode,
                            temperature=temperature,
                            api_key=api_key,
                            base_url=base_url,
                            organization=organization,
                            verbose=verbose,
                        )
                    except Exception as e:
                        raise XNANOException(f"Failed to check guardrails: {e}")

                    if (
                        guardrails_result.guardrails < 0.5
                    ):  # Threshold for guardrails violation
                        results.append(
                            ValidationResult(
                                content=input_text, violates_guardrails=True
                            )
                        )
                        continue

                # Basic accuracy check
                progress.update(
                    task_id, description=f"Checking accuracy for: {input_text[:30]}..."
                )

                system_message = (
                    "You are a validation expert. Determine if the given input is accurate, "
                    "well-formed, and logically sound. Return true only if the input meets "
                    "all these criteria."
                )

                try:
                    accuracy_result = completion(
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": f"Input: {input_text}"},
                        ],
                        model=model,
                        response_model=AccuracyCheck,
                        mode=mode,
                        temperature=temperature,
                        api_key=api_key,
                        base_url=base_url,
                        organization=organization,
                        verbose=verbose,
                    )
                except Exception as e:
                    raise XNANOException(f"Failed to check accuracy: {e}")

                # Context-aware validation if context is provided
                accuracy_score = None
                if context:
                    progress.update(
                        task_id,
                        description=f"Checking contextual accuracy for: {input_text[:30]}...",
                    )

                    system_message = (
                        "You are a validation expert. Rate how accurately the input aligns with "
                        "the provided reference context from 0.0 to 1.0, where 1.0 means perfect "
                        "alignment and 0.0 means complete misalignment."
                    )

                    try:
                        accuracy_score_result = completion(
                            messages=[
                                {"role": "system", "content": system_message},
                                {
                                    "role": "user",
                                    "content": f"Input: {input_text}\n\nReference Context: {context}",
                                },
                            ],
                            model=model,
                            response_model=AccuracyScore,
                            mode=mode,
                            max_retries=max_retries,
                            temperature=temperature,
                            api_key=api_key,
                            base_url=base_url,
                            organization=organization,
                            verbose=verbose,
                        )
                        accuracy_score = accuracy_score_result.accuracy
                    except Exception as e:
                        raise XNANOException(
                            f"Failed to check contextual accuracy: {e}"
                        )

                # Skip explanation and accurate generation if only guardrails are provided
                if guardrails and not context:
                    results.append(
                        ValidationResult(
                            explanation=None,  # No explanation generated
                            content=input_text,
                            accuracy=None,  # No accuracy generated
                            context=context if context else None,
                            violates_guardrails=False,
                        )
                    )
                    continue  # Skip to the next input

                # Get explanation
                progress.update(
                    task_id,
                    description=f"Generating explanation for: {input_text[:30]}...",
                ) if loader else None

                system_message = (
                    "You are a validation expert. Provide a clear, concise explanation for why "
                    "the input is or isn't accurate, focusing on key factors that influenced "
                    "your assessment."
                )

                try:
                    explanation_result = completion(
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": f"Input: {input_text}"},
                        ],
                        model=model,
                        response_model=ExplanationCheck,
                        mode=mode,
                        temperature=temperature,
                        api_key=api_key,
                        base_url=base_url,
                        organization=organization,
                        verbose=verbose,
                    )
                except Exception as e:
                    raise XNANOException(f"Failed to generate explanation: {e}")

                # Compile results
                results.append(
                    ValidationResult(
                        accurate=accuracy_result.accurate,
                        explanation=explanation_result.explanation,
                        content=input_text,
                        accuracy=accuracy_score,
                        context=context if context else None,
                        violates_guardrails=False,
                    )
                )

                progress.advance(task_id)

    else:
        for input_text in inputs:
            # Check guardrails first if provided
            if guardrails:
                guardrails_list = (
                    [guardrails] if isinstance(guardrails, str) else guardrails
                )
                guardrails_prompt = "\n".join(guardrails_list)

                system_message = (
                    "You are a content moderator. Rate how well the input adheres to the specified "
                    "guardrails from 0.0 to 1.0, where 1.0 means perfect compliance and 0.0 means "
                    "complete violation."
                )

                try:
                    guardrails_result = completion(
                        messages=[
                            {"role": "system", "content": system_message},
                            {
                                "role": "user",
                                "content": f"Input: {input_text}\n\nGuardrails:\n{guardrails_prompt}",
                            },
                        ],
                        model=model,
                        response_model=GuardrailsCheck,
                        mode=mode,
                        temperature=temperature,
                        api_key=api_key,
                        base_url=base_url,
                        organization=organization,
                        verbose=verbose,
                    )
                except Exception as e:
                    raise XNANOException(f"Failed to check guardrails: {e}")

                if (
                    guardrails_result.guardrails < 0.5
                ):  # Threshold for guardrails violation
                    results.append(
                        ValidationResult(content=input_text, violates_guardrails=True)
                    )
                    continue

            system_message = (
                "You are a validation expert. Determine if the given input is accurate, "
                "well-formed, and logically sound. Return true only if the input meets "
                "all these criteria."
            )

            try:
                accuracy_result = completion(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Input: {input_text}"},
                    ],
                    model=model,
                    response_model=AccuracyCheck,
                    mode=mode,
                    temperature=temperature,
                    api_key=api_key,
                    base_url=base_url,
                    organization=organization,
                    verbose=verbose,
                )
            except Exception as e:
                raise XNANOException(f"Failed to check accuracy: {e}")

            # Context-aware validation if context is provided
            accuracy_score = None
            if context:
                system_message = (
                    "You are a validation expert. Rate how accurately the input aligns with "
                    "the provided reference context from 0.0 to 1.0, where 1.0 means perfect "
                    "alignment and 0.0 means complete misalignment."
                )

                try:
                    accuracy_score_result = completion(
                        messages=[
                            {"role": "system", "content": system_message},
                            {
                                "role": "user",
                                "content": f"Input: {input_text}\n\nReference Context: {context}",
                            },
                        ],
                        model=model,
                        response_model=AccuracyScore,
                        mode=mode,
                        max_retries=max_retries,
                        temperature=temperature,
                        api_key=api_key,
                        base_url=base_url,
                        organization=organization,
                        verbose=verbose,
                    )
                    accuracy_score = accuracy_score_result.accuracy
                except Exception as e:
                    raise XNANOException(f"Failed to check contextual accuracy: {e}")

            # Skip explanation and accurate generation if only guardrails are provided
            if guardrails and not context:
                results.append(
                    ValidationResult(
                        explanation=None,  # No explanation generated
                        content=input_text,
                        accuracy=None,  # No accuracy generated
                        context=context if context else None,
                        violates_guardrails=False,
                    )
                )
                continue  # Skip to the next input

            system_message = (
                "You are a validation expert. Provide a clear, concise explanation for why "
                "the input is or isn't accurate, focusing on key factors that influenced "
                "your assessment."
            )

            try:
                explanation_result = completion(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Input: {input_text}"},
                    ],
                    model=model,
                    response_model=ExplanationCheck,
                    mode=mode,
                    temperature=temperature,
                    api_key=api_key,
                    base_url=base_url,
                    organization=organization,
                    verbose=verbose,
                )
            except Exception as e:
                raise XNANOException(f"Failed to generate explanation: {e}")

            # Compile results
            results.append(
                ValidationResult(
                    accurate=accuracy_result.accurate,
                    explanation=explanation_result.explanation,
                    content=input_text,
                    accuracy=accuracy_score,
                    context=context if context else None,
                    violates_guardrails=False,
                )
            )

    if single_input:
        return results[0]
    else:
        return results


async def _avalidate(
    inputs: Union[str, List[str]],
    context: Optional[Any] = None,
    guardrails: Optional[Union[str, List[str]]] = None,
    model: Union[str, CompletionChatModelsParam] = "gpt-4o-mini",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.7,
    mode: CompletionInstructorModeParam = "tool_call",
    max_retries: int = 3,
    organization: Optional[str] = None,
    loader: Optional[bool] = True,
    verbose: bool = False,
) -> Union[ValidationResult, List[ValidationResult]]:
    """
    Validates input(s) for accuracy, contextual relevance, and guardrail compliance.

    Args:
        inputs (Union[str, List[str]]): Input(s) to validate
        context (Optional[Any]): Reference context for validation
        guardrails (Optional[Union[str, List[str]]]): Content moderation rules
        model (Union[str, PredefinedModel]): Model to use for validation
        api_key (Optional[str]): API key for the LLM service
        base_url (Optional[str]): Base URL for the LLM service
        temperature (float): Temperature for response generation
        mode (InstructorMode): Mode for the instructor
        max_retries (int): Maximum number of retries for API calls
        organization (Optional[str]): Organization for the LLM service
        client (Optional[Literal["openai", "litellm"]]): Client to use for API calls
        verbose (bool): Whether to log verbose output

    Returns:
        Union[ValidationResult, List[ValidationResult]]: Validation results
    """

    # Convert single input to list for consistent processing
    if isinstance(inputs, str):
        inputs = [inputs]
        single_input = True
    else:
        single_input = False

    results = []

    if loader:
        with console.progress(
            "Validating inputs...",
        ) as progress:
            task_id = progress.add_task("Validating inputs...", total=len(inputs))

            for input_text in inputs:
                # Check guardrails first if provided
                if guardrails:
                    progress.update(
                        task_id,
                        description=f"Checking guardrails for: {input_text[:30]}...",
                    ) if loader else None

                    guardrails_list = (
                        [guardrails] if isinstance(guardrails, str) else guardrails
                    )
                    guardrails_prompt = "\n".join(guardrails_list)

                    system_message = (
                        "You are a content moderator. Rate how well the input adheres to the specified "
                        "guardrails from 0.0 to 1.0, where 1.0 means perfect compliance and 0.0 means "
                        "complete violation."
                    )

                    try:
                        guardrails_result = completion(
                            messages=[
                                {"role": "system", "content": system_message},
                                {
                                    "role": "user",
                                    "content": f"Input: {input_text}\n\nGuardrails:\n{guardrails_prompt}",
                                },
                            ],
                            model=model,
                            response_model=GuardrailsCheck,
                            mode=mode,
                            temperature=temperature,
                            api_key=api_key,
                            base_url=base_url,
                            organization=organization,
                            verbose=verbose,
                        )
                    except Exception as e:
                        raise XNANOException(f"Failed to check guardrails: {e}")

                    if (
                        guardrails_result.guardrails < 0.5
                    ):  # Threshold for guardrails violation
                        results.append(
                            ValidationResult(
                                content=input_text, violates_guardrails=True
                            )
                        )
                        continue

                # Basic accuracy check
                progress.update(
                    task_id, description=f"Checking accuracy for: {input_text[:30]}..."
                )

                system_message = (
                    "You are a validation expert. Determine if the given input is accurate, "
                    "well-formed, and logically sound. Return true only if the input meets "
                    "all these criteria."
                )

                try:
                    accuracy_result = await async_completion(
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": f"Input: {input_text}"},
                        ],
                        model=model,
                        response_model=AccuracyCheck,
                        mode=mode,
                        temperature=temperature,
                        api_key=api_key,
                        base_url=base_url,
                        organization=organization,
                        verbose=verbose,
                    )
                except Exception as e:
                    raise XNANOException(f"Failed to check accuracy: {e}")

                # Context-aware validation if context is provided
                accuracy_score = None
                if context:
                    progress.update(
                        task_id,
                        description=f"Checking contextual accuracy for: {input_text[:30]}...",
                    )

                    system_message = (
                        "You are a validation expert. Rate how accurately the input aligns with "
                        "the provided reference context from 0.0 to 1.0, where 1.0 means perfect "
                        "alignment and 0.0 means complete misalignment."
                    )

                    try:
                        accuracy_score_result = await async_completion(
                            messages=[
                                {"role": "system", "content": system_message},
                                {
                                    "role": "user",
                                    "content": f"Input: {input_text}\n\nReference Context: {context}",
                                },
                            ],
                            model=model,
                            response_model=AccuracyScore,
                            mode=mode,
                            max_retries=max_retries,
                            temperature=temperature,
                            api_key=api_key,
                            base_url=base_url,
                            organization=organization,
                            verbose=verbose,
                        )
                        accuracy_score = accuracy_score_result.accuracy
                    except Exception as e:
                        raise XNANOException(
                            f"Failed to check contextual accuracy: {e}"
                        )

                # Skip explanation and accurate generation if only guardrails are provided
                if guardrails and not context:
                    results.append(
                        ValidationResult(
                            explanation=None,  # No explanation generated
                            content=input_text,
                            accuracy=None,  # No accuracy generated
                            context=context if context else None,
                            violates_guardrails=False,
                        )
                    )
                    continue  # Skip to the next input

                # Get explanation
                progress.update(
                    task_id,
                    description=f"Generating explanation for: {input_text[:30]}...",
                ) if loader else None

                system_message = (
                    "You are a validation expert. Provide a clear, concise explanation for why "
                    "the input is or isn't accurate, focusing on key factors that influenced "
                    "your assessment."
                )

                try:
                    explanation_result = await async_completion(
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": f"Input: {input_text}"},
                        ],
                        model=model,
                        response_model=ExplanationCheck,
                        mode=mode,
                        temperature=temperature,
                        api_key=api_key,
                        base_url=base_url,
                        organization=organization,
                        verbose=verbose,
                    )
                except Exception as e:
                    raise XNANOException(f"Failed to generate explanation: {e}")

                # Compile results
                results.append(
                    ValidationResult(
                        accurate=accuracy_result.accurate,
                        explanation=explanation_result.explanation,
                        content=input_text,
                        accuracy=accuracy_score,
                        context=context if context else None,
                        violates_guardrails=False,
                    )
                )

                progress.advance(task_id)

    else:
        for input_text in inputs:
            # Check guardrails first if provided
            if guardrails:
                guardrails_list = (
                    [guardrails] if isinstance(guardrails, str) else guardrails
                )
                guardrails_prompt = "\n".join(guardrails_list)

                system_message = (
                    "You are a content moderator. Rate how well the input adheres to the specified "
                    "guardrails from 0.0 to 1.0, where 1.0 means perfect compliance and 0.0 means "
                    "complete violation."
                )

                try:
                    guardrails_result = await async_completion(
                        messages=[
                            {"role": "system", "content": system_message},
                            {
                                "role": "user",
                                "content": f"Input: {input_text}\n\nGuardrails:\n{guardrails_prompt}",
                            },
                        ],
                        model=model,
                        response_model=GuardrailsCheck,
                        mode=mode,
                        temperature=temperature,
                        api_key=api_key,
                        base_url=base_url,
                        organization=organization,
                        verbose=verbose,
                    )
                except Exception as e:
                    raise XNANOException(f"Failed to check guardrails: {e}")

                if (
                    guardrails_result.guardrails < 0.5
                ):  # Threshold for guardrails violation
                    results.append(
                        ValidationResult(content=input_text, violates_guardrails=True)
                    )
                    continue

            system_message = (
                "You are a validation expert. Determine if the given input is accurate, "
                "well-formed, and logically sound. Return true only if the input meets "
                "all these criteria."
            )

            try:
                accuracy_result = await async_completion(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Input: {input_text}"},
                    ],
                    model=model,
                    response_model=AccuracyCheck,
                    mode=mode,
                    temperature=temperature,
                    api_key=api_key,
                    base_url=base_url,
                    organization=organization,
                    verbose=verbose,
                )
            except Exception as e:
                raise XNANOException(f"Failed to check accuracy: {e}")

            # Context-aware validation if context is provided
            accuracy_score = None
            if context:
                system_message = (
                    "You are a validation expert. Rate how accurately the input aligns with "
                    "the provided reference context from 0.0 to 1.0, where 1.0 means perfect "
                    "alignment and 0.0 means complete misalignment."
                )

                try:
                    accuracy_score_result = await async_completion(
                        messages=[
                            {"role": "system", "content": system_message},
                            {
                                "role": "user",
                                "content": f"Input: {input_text}\n\nReference Context: {context}",
                            },
                        ],
                        model=model,
                        response_model=AccuracyScore,
                        mode=mode,
                        max_retries=max_retries,
                        temperature=temperature,
                        api_key=api_key,
                        base_url=base_url,
                        organization=organization,
                        verbose=verbose,
                    )
                    accuracy_score = accuracy_score_result.accuracy
                except Exception as e:
                    raise XNANOException(f"Failed to check contextual accuracy: {e}")

            # Skip explanation and accurate generation if only guardrails are provided
            if guardrails and not context:
                results.append(
                    ValidationResult(
                        explanation=None,  # No explanation generated
                        content=input_text,
                        accuracy=None,  # No accuracy generated
                        context=context if context else None,
                        violates_guardrails=False,
                    )
                )
                continue  # Skip to the next input

            system_message = (
                "You are a validation expert. Provide a clear, concise explanation for why "
                "the input is or isn't accurate, focusing on key factors that influenced "
                "your assessment."
            )

            try:
                explanation_result = await async_completion(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Input: {input_text}"},
                    ],
                    model=model,
                    response_model=ExplanationCheck,
                    mode=mode,
                    temperature=temperature,
                    api_key=api_key,
                    base_url=base_url,
                    organization=organization,
                    verbose=verbose,
                )
            except Exception as e:
                raise XNANOException(f"Failed to generate explanation: {e}")

            # Compile results
            results.append(
                ValidationResult(
                    accurate=accuracy_result.accurate,
                    explanation=explanation_result.explanation,
                    content=input_text,
                    accuracy=accuracy_score,
                    context=context if context else None,
                    violates_guardrails=False,
                )
            )

    if single_input:
        return results[0]
    else:
        return results


async def async_generate_validation(
    inputs: Union[str, List[str]],
    context: Optional[Any] = None,
    guardrails: Optional[Union[str, List[str]]] = None,
    model: Union[str, CompletionChatModelsParam] = "gpt-4o-mini",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.7,
    mode: CompletionInstructorModeParam = "tool_call",
    max_retries: int = 3,
    organization: Optional[str] = None,
    loader: Optional[bool] = True,
    verbose: bool = False,
) -> Union[ValidationResult, List[ValidationResult]]:
    """
    Validates input(s) for accuracy, contextual relevance, and guardrail compliance.

    Args:
        inputs (Union[str, List[str]]): Input(s) to validate
        context (Optional[Any]): Reference context for validation
        guardrails (Optional[Union[str, List[str]]]): Content moderation rules
        model (Union[str, PredefinedModel]): Model to use for validation
        api_key (Optional[str]): API key for the LLM service
        base_url (Optional[str]): Base URL for the LLM service
        temperature (float): Temperature for response generation
        mode (InstructorMode): Mode for the instructor
        max_retries (int): Maximum number of retries for API calls
        organization (Optional[str]): Organization for the LLM service
        client (Optional[Literal["openai", "litellm"]]): Client to use for API calls
        verbose (bool): Whether to log verbose output

    Returns:
        Union[ValidationResult, List[ValidationResult]]: Validation results
    """
    return await _avalidate(
        inputs,
        context,
        guardrails,
        model,
        api_key,
        base_url,
        temperature,
        mode,
        max_retries,
        organization,
        loader,
        verbose,
    )


if __name__ == "__main__":
    import asyncio

    print(generate_validation("the capital of france is paris", loader=True))

    print(generate_validation("the capital of france is london", loader=False))

    result = asyncio.run(
        async_generate_validation(
            ["IM GONNA ATTACK YOU"], guardrails=["No violence or threats of violence"]
        )
    )

    print(result)

    print(
        asyncio.run(
            async_generate_validation(
                ["IM GONNA ATTACK YOU"],
                guardrails=["No violence or threats of violence"],
            )
        )
    )
