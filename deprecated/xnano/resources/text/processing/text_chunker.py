from typing import Union, List
from ....lib import console, XNANOException


def text_chunker(
    inputs: Union[str, List[str]],
    chunk_size: int = 512,
    processes: int = 1,
    memoize: bool = True,
    max_token_chars: int = None,
    progress_bar: bool = True,
    tiktoken_model: str = "gpt-4",
) -> Union[List[str], List[List[str]]]:
    """
    Chunks input text(s) for optimal retrieval and processing.

    Args:
        inputs (Union[str, List[str]]): The input string or list of strings to chunk.
        chunk_size (int): The target size for each chunk in tokens.
        processes (int): Number of processes for parallel chunking.
        memoize (bool): Cache results for repeated inputs.
        max_token_chars (int): Limits token count per chunk.
        progress_bar (bool): Show progress bar if True.
        tiktoken_model (str): Model identifier for tokenizer compatibility.

    Returns:
        Union[List[str], List[List[str]]]: Chunked text(s).
    """
    import semchunk
    import tiktoken

    try:
        # Initialize tokenizer for the specified model
        tokenizer = tiktoken.encoding_for_model(tiktoken_model)

        # Initialize semchunk chunker with required configuration
        chunker = semchunk.chunkerify(
            tokenizer,
            chunk_size=chunk_size,
            max_token_chars=max_token_chars,
            memoize=memoize,
        )

        # Ensure input consistency
        if isinstance(inputs, str):
            inputs = [inputs]
        elif not isinstance(inputs, list):
            raise TypeError("Input must be a string or a list of strings.")

        # Chunking with progress bar support
        chunked_texts = _process_chunks(inputs, chunker, processes)

        return chunked_texts

    except Exception as e:
        raise XNANOException(f"Error in chunk function: {str(e)}")


def _process_chunks(inputs: List[str], chunker, processes: int, progress=None):
    """
    Processes input chunks with optional multi-processing and progress bar.

    Args:
        inputs (List[str]): List of input texts.
        chunker: Initialized chunker instance from semchunk.
        processes (int): Number of processes for parallelization.
        progress: Optional progress indicator.

    Returns:
        List of chunked texts.
    """
    import multiprocessing

    if len(inputs) == 1:
        return chunker.chunk(inputs[0])

    if processes > 1:
        with multiprocessing.Pool(processes) as pool:
            if progress:
                results = [pool.apply_async(chunker.chunk, (text,)) for text in inputs]
                return [res.get() for res in progress.track(results)]
            else:
                return pool.map(chunker, inputs)
    else:
        return [chunker(text) for text in inputs]


# Example usage
if __name__ == "__main__":
    sample_text = (
        "Hello, world! My name is Hammad. I like to code. I like to eat. I like to sleep. "
        "I like to play. I like to learn. I like to teach. I like to help. I like to be helpful. "
        "I like to be a good person. I like to be a good friend. I like to be a good teacher. "
        "I like to be a good learner. I like to be a good helper."
    )
    print(text_chunker(sample_text, progress_bar=True, chunk_size=45))
