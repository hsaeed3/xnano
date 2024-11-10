import semchunk
import tiktoken
from typing import Union, List
from .._console import console


def chunk(
    inputs: Union[str, List[str]],
    chunk_size: int = 512,
    processes: int = 1,
    memoize: bool = True,
    progress: bool = False,
    max_token_chars: int = None,
    progress_bar: bool = True,
    tiktoken_model: str = "gpt-4"
) -> Union[List[str], List[List[str]]]:
    """
    Takes a string or a list of strings and returns the chunked content.

    Example:
        ```python
        chunk("Hello, world!")
        # ["Hello, world!"]
        ```

    Args:
        inputs: Union[str, List[str]]: The input to chunk.
        chunk_size: int: The size of the chunks to return.
        model: str: The model to use for chunking.
        processes: int: The number of processes to use for chunking.
        memoize: bool: Whether to memoize the chunking process.
        progress: bool: Whether to show a progress bar.
        max_token_chars: int: The maximum number of characters to use for chunking.

    Returns:
        Union[List[str], List[List[str]]]: The chunked content.
    """

    try:
        tokenizer = tiktoken.encoding_for_model(tiktoken_model)


        if progress_bar:
            with console.progress(
                "Chunking...",
            ) as progress:

                chunker = semchunk.chunkerify(
                    tokenizer,
                    chunk_size=chunk_size,
                    max_token_chars=max_token_chars,
                    memoize=memoize,
                )

        else:
            chunker = semchunk.chunkerify(
                tokenizer,
                chunk_size=chunk_size,
                max_token_chars=max_token_chars,
                memoize=memoize,
            )

        # Handle single input case (str)
        if isinstance(inputs, str):
            inputs = [inputs]  # Convert to list for uniform handling

        if not isinstance(inputs, list):
            raise TypeError(
                "inputs must be a string or a list of strings"
            )

        texts = []
        for item in inputs:
            # Handle string input directly
            if isinstance(item, str):
                texts.append(item)
            else:
                raise TypeError(f"Unsupported input type: {type(item)}")

        # Chunk the content, using processes and progress bar as needed
        if len(texts) == 1:
            return chunker(texts[0])  # Single input, return the chunked result
        else:

            return chunker(
                texts, processes=processes, progress=progress
            )  

    except Exception as e:
        # Detailed error logging
        print(f"Error in chunk function: {str(e)}")
        raise e
    

if __name__ == "__main__":
    print(chunk("Hello, world! My name is Hammad. I like to code. I like to eat. I like to sleep. I like to play. I like to learn. I like to teach. I like to help. I like to be helpful. I like to be a good person. I like to be a good friend. I like to be a good teacher. I like to be a good learner. I like to be a good helper. I like to be a good person. I like to be a good friend. I like to be a good teacher. I like to be a good learner. I like to be a good helper.", progress_bar=True,
                chunk_size=20))