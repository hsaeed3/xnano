from ....lib import XNANOException
from ....types.embeddings.embedding_model import EmbeddingModel
from typing import List, Union, Optional, Dict


MODEL_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 1536,
    "ollama/nomic-embed-text": 768,
    "ollama/mxbai-embed-large": 1024,
    "ollama/all-minilm": 384,
}


FASTEMBED_MODELS = {
    "fastembed/BAAI/bge-small-en-v1.5": 384,
    "fastembed/BAAI/bge-small-zh-v1.5": 512,
    "fastembed/snowflake/snowflake-arctic-embed-xs": 384,
    "fastembed/sentence-transformers/all-MiniLM-L6-v2": 384,
    "fastembed/jinaai/jina-embeddings-v2-small-en": 512,
    "fastembed/BAAI/bge-small-en": 384,
    "fastembed/snowflake/snowflake-arctic-embed-s": 384,
    "fastembed/nomic-ai/nomic-embed-text-v1.5-Q": 768,
    "fastembed/BAAI/bge-base-en-v1.5": 768,
    "fastembed/sentence-transformers/paraphrase-multilingual-...": 384,
    "fastembed/Qdrant/clip-ViT-B-32-text": 512,
    "fastembed/jinaai/jina-embeddings-v2-base-de": 768,
    "fastembed/BAAI/bge-base-en": 768,
    "fastembed/snowflake/snowflake-arctic-embed-m": 768,
    "fastembed/nomic-ai/nomic-embed-text-v1.5": 768,
    "fastembed/jinaai/jina-embeddings-v2-base-en": 768,
    "fastembed/nomic-ai/nomic-embed-text-v1": 768,
    "fastembed/snowflake/snowflake-arctic-embed-m-long": 768,
    "fastembed/mixedbread-ai/mxbai-embed-large-v1": 1024,
    "fastembed/jinaai/jina-embeddings-v2-base-code": 768,
    "fastembed/sentence-transformers/paraphrase-multilingual-...": 768,
    "fastembed/snowflake/snowflake-arctic-embed-l": 1024,
    "fastembed/thenlper/gte-large": 1024,
    "fastembed/BAAI/bge-large-en-v1.5": 1024,
    "fastembed/intfloat/multilingual-e5-large": 1024,
}


class EmbeddingCache:
    """LRU cache implementation for embeddings with size limits and TTL"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        from collections import deque

        self._cache: Dict[str, tuple[List[float], float]] = {}
        self._max_size = max_size
        self._ttl = ttl
        self._access_order = deque()

    def _generate_key(self, text: str, model: str, dimensions: int) -> str:
        """Generate a consistent hash key for the input parameters"""
        import hashlib

        key_string = f"{text}:{model}:{dimensions}"
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get(self, text: str, model: str, dimensions: int) -> Optional[List[float]]:
        import time

        key = self._generate_key(text, model, dimensions)
        if key in self._cache:
            embedding, timestamp = self._cache[key]
            if time.time() - timestamp <= self._ttl:
                self._access_order.remove(key)
                self._access_order.append(key)
                return embedding
            else:
                del self._cache[key]
                self._access_order.remove(key)
        return None

    def set(self, text: str, model: str, dimensions: int, embedding: List[float]):
        import time

        key = self._generate_key(text, model, dimensions)
        if len(self._cache) >= self._max_size:
            old_key = self._access_order.popleft()
            del self._cache[old_key]

        self._cache[key] = (embedding, time.time())
        self._access_order.append(key)


class BatchProcessor:
    """Handles efficient batching of embedding requests"""

    def __init__(self, batch_size: int = 8):
        self.batch_size = batch_size
        self.current_batch: List[str] = []
        self.results: List[List[float]] = []

    def add(self, text: str):
        self.current_batch.append(text)

    def should_process(self) -> bool:
        return len(self.current_batch) >= self.batch_size

    def get_batch(self) -> List[str]:
        batch = self.current_batch[: self.batch_size]
        self.current_batch = self.current_batch[self.batch_size :]
        return batch


def text_embeddings(
    text: Union[str, List[str]],
    model: Union[str, EmbeddingModel] = "text-embedding-3-small",
    dimensions: Optional[int] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    organization: Optional[str] = None,
    use_cache: bool = True,
    batch_size: Optional[int] = None,
    retry_attempts: int = 3,
    retry_delay: float = 1.0,
) -> Union[List[float], List[List[float]]]:
    """
    Enhanced embedding generation with intelligent batching, caching, and error handling.
    Args:
        text (Union[str, List[str]]): Input text(s) to embed
        model (Union[str, EmbeddingModel]): Model identifier
        dimensions (Optional[int]): Override default dimensions for model
        api_key (Optional[str]): API key for authentication
        base_url (Optional[str]): Base URL for API
        organization (Optional[str]): Organization identifier
        use_cache (bool): Whether to use embedding cache
        batch_size (Optional[int]): Override default batch size
        retry_attempts (int): Number of retry attempts
        retry_delay (float): Delay between retries in seconds
    Returns:
        Union[List[float], List[List[float]]]: Generated embeddings
    """
    from litellm import embedding as litellm_embedding
    import time
    from concurrent.futures import ThreadPoolExecutor

    cache = EmbeddingCache() if use_cache else None

    # Check if model is in FastEmbed list and lock dimensions if so
    if model.startswith("fastembed"):
        dimensions = FASTEMBED_MODELS[model]
    else:
        # Set model dimensions based on input or fallback
        dimensions = dimensions or MODEL_DIMENSIONS.get(model, 1536)

    batch_size = batch_size or (8 if model == "text-embedding-3-small" else 4)

    def process_single_text(input_text: str) -> List[float]:
        if cache:
            cached_result = cache.get(input_text, model, dimensions)
            if cached_result:
                return cached_result

        for attempt in range(retry_attempts):
            try:
                if model.startswith("fastembed"):
                    try:
                        from fastembed import TextEmbedding
                    except ImportError:
                        raise XNANOException(
                            "fastembed is not included in the base xnano package. To use fastembed models, install it with 'pip install xnano[fastembed]' or 'pip install fastembed'"
                        )

                    embedding_model = TextEmbedding(model_name=model)
                    result = list(embedding_model.embed([input_text]))[0]
                else:
                    result = litellm_embedding(
                        input=input_text,
                        model=model,
                        dimensions=dimensions,
                        api_base=base_url,
                        api_key=api_key,
                        organization=organization,
                    ).data[0]["embedding"]

                if cache:
                    cache.set(input_text, model, dimensions, result)
                return result

            except Exception as e:
                if attempt == retry_attempts - 1:
                    raise XNANOException(
                        f"Error generating embeddings after {retry_attempts} attempts: {e}"
                    )
                time.sleep(retry_delay * (2**attempt))

    if isinstance(text, str):
        return process_single_text(text)

    batch_processor = BatchProcessor(batch_size)
    results: List[List[float]] = []

    with ThreadPoolExecutor() as executor:
        for input_text in text:
            batch_processor.add(input_text)
            if batch_processor.should_process():
                batch = batch_processor.get_batch()
                futures = [executor.submit(process_single_text, t) for t in batch]
                results.extend([f.result() for f in futures])

        if batch_processor.current_batch:
            futures = [
                executor.submit(process_single_text, t)
                for t in batch_processor.current_batch
            ]
            results.extend([f.result() for f in futures])

    return results


if __name__ == "__main__":
    test_text = "Hello, world!"
    result = text_embeddings(test_text)
    print(result)
    print(f"Generated embedding with {len(result)} dimensions")

    texts = ["Hello, world!", "Another text", "Third example"]
    results = text_embeddings(texts)
    print(results)
    print(f"Generated {len(results)} embeddings")
