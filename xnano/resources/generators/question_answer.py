from typing import List, Optional, Literal, Union
from pydantic import BaseModel, create_model

from ...lib import console

from ..text.processing.text_chunker import text_chunker as chunker
from ..completions.main import completion
from ...types.completions.params import (
    CompletionChatModelsParam,
    CompletionInstructorModeParam,
)


class Question(BaseModel):
    question: str
    answer: str


class Dataset(BaseModel):
    questions: List[Question]


def _qa(
    input_text: str,
    num_questions: int = 5,
    chunk_size: Optional[int] = 512,
    model: CompletionChatModelsParam = "gpt-4o-mini",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    organization: Optional[str] = None,
    temperature: float = 0.7,
    mode: CompletionInstructorModeParam = "tool_call",
    max_retries: int = 3,
    client: Optional[Literal["openai", "litellm"]] = "openai",
    progress_bar: Optional[bool] = True,
    verbose: bool = False,
    question_instructions: Optional[str] = None,
    answer_instructions: Optional[str] = None,
) -> Dataset:
    """
    Generate a dataset of questions and answers based on the input text.

    Args:
        input_text (str): The input text to generate questions and answers from.
        num_questions (int): The number of questions to generate per chunk.
        chunk_size (Optional[int]): The size of each chunk when processing large texts. If None, no chunking is performed.
        model (str): The model to use for generation.
        api_key (Optional[str]): API key for the LLM service.
        base_url (Optional[str]): Base URL for the LLM service.
        organization (Optional[str]): Organization for the LLM service.
        temperature (float): Temperature for response generation.
        mode (InstructorMode): Mode for the instructor.
        max_retries (int): Maximum number of retries for API calls.
        client (Optional[Literal["openai", "litellm"]]): Client to use for API calls.
        verbose (bool): Whether to log verbose output.

    Returns:
        Dataset: A dataset containing generated questions and answers.
    """
    if verbose:
        console.message(
            f"Generating dataset from input text of length: {len(input_text)}"
        )

    # Chunk the input text only if chunk_size is not None
    if chunk_size is not None:
        chunks = chunker(
            input_text, chunk_size=chunk_size, model=model, progress_bar=progress_bar
        )
        if verbose:
            console.message(f"Text chunked into {len(chunks)} parts")
    else:
        chunks = [input_text]
        if verbose:
            console.message("Chunking disabled, processing entire text as one chunk")

    all_qa_pairs = []

    def process_chunk(chunk):
        # Generate questions
        questions = generate_questions(
            chunk,
            num_questions,
            model,
            mode,
            max_retries,
            temperature,
            progress_bar,
            api_key,
            base_url,
            organization,
            question_instructions,
            verbose,
        )

        # Generate answers for each question
        qa_pairs = generate_answers(
            chunk,
            questions,
            model,
            mode,
            max_retries,
            temperature,
            progress_bar,
            api_key,
            base_url,
            organization,
            answer_instructions,
            verbose,
        )

        return qa_pairs

    if progress_bar:
        with console.progress(
            prompt="Chunking Text...",
        ) as progress:
            task_id = progress.add_task("Chunking Text...", total=len(chunks))

            results = []
            for chunk in chunks:
                progress.update(
                    task_id,
                    description=f"Processing Chunk: {chunk[:30]}...",
                    completed=0,
                )
                results.append(process_chunk(chunk))
                progress.update(task_id, advance=1)

            progress.update(
                task_id, description="All Chunks Processed", completed=len(chunks)
            )
    else:
        results = [process_chunk(chunk) for chunk in chunks]

    # Flatten the results
    all_qa_pairs = [qa for result in results for qa in result]

    return Dataset(questions=all_qa_pairs)


def generate_questions(
    context,
    num_questions,
    model,
    mode,
    max_retries,
    temperature,
    progress_bar,
    api_key,
    base_url,
    organization,
    instructions=None,
    verbose=False,
):
    system_message = (
        "You are an expert question generator. Your task is to create insightful and diverse questions "
        "based on the given context. The questions should cover various aspects of the text and be answerable "
        "using only the information provided in the context."
    )
    if instructions:
        system_message += f"\n\nInstructions: {instructions}"
    user_message = f"Context:\n\n{context}\n\nGenerate {num_questions} diverse questions based on this context."

    response = completion(
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        model=model,
        response_model=create_model("QuestionList", questions=(List[str], ...)),
        mode=mode,
        max_retries=max_retries,
        temperature=temperature,
        progress_bar=progress_bar,
        api_key=api_key,
        base_url=base_url,
        organization=organization,
        verbose=verbose,
    )

    return response.questions


def generate_answers(
    context,
    questions,
    model,
    mode,
    max_retries,
    temperature,
    progress_bar,
    api_key,
    base_url,
    organization,
    instructions=None,
    verbose=False,
):
    qa_pairs = []

    for question in questions:
        system_message = (
            "You are an expert in answering questions based on given contexts. Your task is to provide "
            "accurate and concise answers using only the information available in the provided context."
        )
        if instructions:
            system_message += f"\n\nInstructions: {instructions}"
        user_message = f"Context:\n\n{context}\n\nQuestion: {question}\n\nProvide a concise answer based only on the given context."

        response = completion(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            model=model,
            response_model=create_model("Answer", answer=(str, ...)),
            mode=mode,
            max_retries=max_retries,
            temperature=temperature,
            progress_bar=progress_bar,
            api_key=api_key,
            base_url=base_url,
            organization=organization,
        )

        qa_pairs.append(Question(question=question, answer=response.answer))

    return qa_pairs


def generate_qa_pairs(
    input_text: str,
    num_questions: int = 5,
    chunk_size: Optional[int] = 512,
    model: CompletionChatModelsParam = "gpt-4o-mini",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    organization: Optional[str] = None,
    temperature: float = 0.7,
    mode: CompletionInstructorModeParam = "markdown_json_mode",
    max_retries: int = 3,
    client: Optional[Literal["openai", "litellm"]] = "openai",
    progress_bar: Optional[bool] = True,
    verbose: bool = False,
    question_instructions: Optional[str] = None,
    answer_instructions: Optional[str] = None,
) -> Dataset:
    """
    Generate a dataset of questions and answers based on the input text.

    Example:

    >>> qa(input_text="Artificial Intelligence (AI) is a broad field of computer science that aims to create intelligent machines
    that can perform tasks that typically require human intelligence. These tasks include visual perception, ...)

    Args:
        input_text (str): The input text to generate questions and answers from.
        num_questions (int): The number of questions to generate per chunk.
        chunk_size (Optional[int]): The size of each chunk when processing large texts. If None, no chunking is performed.
        model (str): The model to use for generation.
        api_key (Optional[str]): API key for the LLM service.
        base_url (Optional[str]): Base URL for the LLM service.
        organization (Optional[str]): Organization for the LLM service.
        temperature (float): Temperature for response generation.
        mode (InstructorMode): Mode for the instructor.
        max_retries (int): Maximum number of retries for API calls.
        client (Optional[Literal["openai", "litellm"]]): Client to use for API calls.
        verbose (bool): Whether to log verbose output.

    Returns:
        Dataset: A dataset containing generated questions and answers.
    """
    return _qa(
        input_text,
        num_questions,
        chunk_size,
        model,
        api_key,
        base_url,
        organization,
        temperature,
        mode,
        max_retries,
        client,
        progress_bar,
        verbose,
        question_instructions,
        answer_instructions,
    )


# Example usage
if __name__ == "__main__":
    sample_text = """
    Artificial Intelligence (AI) is a broad field of computer science that aims to create intelligent machines
    that can perform tasks that typically require human intelligence. These tasks include visual perception,
    speech recognition, decision-making, and language translation. AI systems are designed to learn from
    experience, adjust to new inputs, and perform human-like tasks.

    There are two main types of AI: narrow AI and general AI. Narrow AI is designed to perform a specific
    task, such as voice recognition or playing chess. General AI, on the other hand, would have the ability
    to perform any intellectual task that a human can do.

    Machine Learning (ML) is a subset of AI that focuses on the development of algorithms and statistical
    models that enable computer systems to improve their performance on a specific task through experience.
    Deep Learning is a subfield of machine learning that uses artificial neural networks with multiple layers
    to analyze various factors of data.

    AI has numerous applications across various industries, including healthcare, finance, transportation,
    and entertainment. In healthcare, AI is used for disease diagnosis and drug discovery. In finance,
    it's applied for fraud detection and algorithmic trading. Self-driving cars use AI for navigation and
    obstacle avoidance. In entertainment, AI powers recommendation systems on platforms like Netflix and Spotify.

    Despite its benefits, AI also raises ethical concerns, such as privacy issues, potential job displacement,
    and the need for transparency in AI decision-making processes. As AI continues to evolve, addressing these
    challenges will be crucial for its responsible development and implementation.
    """

    result = generate_qa_pairs(sample_text, num_questions=5, verbose=True)
    print("Generated Dataset:")
    for qa in result.questions:
        print(f"Q: {qa.question}")
        print(f"A: {qa.answer}")
        print()
