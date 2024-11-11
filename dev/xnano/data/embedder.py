from openai import OpenAI
from typing import List, Union, Optional, Literal
from .._console import console


# TYPING (Easy Model Names)
EmbeddingModel = Literal["text-embedding-3-small", "text-embedding-3-large",
                         "ollama/nomic-embed-text", "ollama/mxbai-embed-large",
                         "ollama/all-minilm"]


def embedding(
    text : str,
    model : Union[str, EmbeddingModel] = "text-embedding-3-small",
    dimensions : int = 1536,
    api_key : Optional[str] = None,
    base_url : Optional[str] = None,
    organization : Optional[str] = None,
) -> List[float]:
    """
    Generate embeddings for a given text using the specified model.

    Args:
        text (str): The text to generate embeddings for.
        model (str): The model to use for generating embeddings. Defaults to "text-embedding-3-small".
        dimensions (int): The number of dimensions for the embeddings. Defaults to 1536.
        api_key (str): The API key to use for authentication. Defaults to None.
        base_url (str): The base URL for the API. Defaults to None.
        organization (str): The organization to use for authentication. Defaults to None.

    Returns:
        List[float]: The embeddings for the given text.
    """

    if model.startswith("ollama/"):
        model = model[7:]

        if not base_url:
            base_url = "http://localhost:11434/v1"
        if not api_key:
            api_key = "ollama"

    if not model.startswith("ollama/") and model not in ["text-embedding-3-small", "text-embedding-3-large"]:
        from litellm import embedding

        return embedding(
            model = model,
            input = text,
            dimensions = dimensions,
            api_key = api_key,
            base_url = base_url,
            organization = organization,
        )

    try:

        client = OpenAI(api_key=api_key, base_url=base_url, organization=organization)

        return client.embeddings.create(input=text, model=model, dimensions=dimensions).data[0].embedding

    except Exception as e:
        from .._exceptions import XNANOException
        raise XNANOException(f"Error generating embeddings: {e}")


if __name__ == "__main__":
    print(embedding("Hello, world!"))