def _import_dependencies(): 
    global OpenAI, List, Union, Optional, Literal, Dict, Any, TypedDict, ThreadPoolExecutor, lru_cache, json, hashlib, deque, time, XNANOException
    from openai import OpenAI
    from typing import List, Union, Optional, Literal, Dict, Any, TypedDict
    from concurrent.futures import ThreadPoolExecutor
    from functools import lru_cache
    import json
    import hashlib
    from collections import deque
    import time
    from .._lib import XNANOException

_import_dependencies()

from ..types.nlp.embeddings import EmbeddingModel


MODEL_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 1536,
    "ollama/nomic-embed-text": 768,
    "ollama/mxbai-embed-large": 1024,
    "ollama/all-minilm": 384
}

class EmbeddingCache:
    """LRU cache implementation for embeddings with size limits and TTL"""
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self._cache: Dict[str, tuple[List[float], float]] = {}
        self._max_size = max_size
        self._ttl = ttl
        self._access_order = deque()
        
    def _generate_key(self, text: str, model: str, dimensions: int) -> str:
        """Generate a consistent hash key for the input parameters"""
        key_string = f"{text}:{model}:{dimensions}"
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get(self, text: str, model: str, dimensions: int) -> Optional[List[float]]:
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
        batch = self.current_batch[:self.batch_size]
        self.current_batch = self.current_batch[self.batch_size:]
        return batch

def embedding(
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
    cache = EmbeddingCache() if use_cache else None
    
    # Set model dimensions based on input or fallback
    dimensions = dimensions or MODEL_DIMENSIONS.get(model, 1536)
    batch_size = batch_size or (8 if model == "text-embedding-3-small" else 4)

    if model.startswith("ollama/"):
        if not base_url:
            base_url = "http://localhost:11434/v1"
        if not api_key:
            api_key = "ollama"

    def process_single_text(input_text: str) -> List[float]:
        if cache:
            cached_result = cache.get(input_text, model, dimensions)
            if cached_result:
                return cached_result

        for attempt in range(retry_attempts):
            try:
                client = OpenAI(api_key=api_key, base_url=base_url, organization=organization)
                result = client.embeddings.create(
                    input=input_text,
                    model=model,
                    dimensions=dimensions
                ).data[0].embedding
                
                if cache:
                    cache.set(input_text, model, dimensions, result)
                return result
                
            except Exception as e:
                if attempt == retry_attempts - 1:
                    raise XNANOException(f"Error generating embeddings after {retry_attempts} attempts: {e}")
                time.sleep(retry_delay * (2 ** attempt))

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
            futures = [executor.submit(process_single_text, t) for t in batch_processor.current_batch]
            results.extend([f.result() for f in futures])

    return results

if __name__ == "__main__":
    test_text = "Hello, world!"
    result = embedding(test_text)
    print(result)
    print(f"Generated embedding with {len(result)} dimensions")

    texts = ["Hello, world!", "Another text", "Third example"]
    results = embedding(texts)
    print(results)
    print(f"Generated {len(results)} embeddings")
