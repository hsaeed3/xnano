import uuid
import logging
from typing import List, Union, Optional, Type, Literal, Callable
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from qdrant_client.http.models import UpdateStatus

from ..data.embedder import embedding
from ..data.chunker import chunk
from ..pydantic import BaseModel as Document
from ..completions import completion

from ..types.chat_models.chat_model import ChatModel
from ..types.embeddings.embedding_model import EmbeddingModel


logger = logging.getLogger(__name__)


class Store:
    """
    Class for storing and retrieving data using Qdrant.
    """

    def __init__(
        self,
        collection_name: str = "my_collection",
        model_class: Optional[Type[BaseModel]] = None,
        embedding_model: Union[str, EmbeddingModel] = "text-embedding-3-small",
        embedding_api_key: Optional[str] = None,
        embedding_dimensions: int = 1536,
        embedding_base_url: Optional[str] = None,
        embedding_organization: Optional[str] = None,
        location: Union[Literal[":memory:"], str] = ":memory:",
        persist_directory: str = "qdrant_db",
        chunk_size: int = 512,
        model: Union[str, ChatModel] = "gpt-4o-mini",
    ):
        """
        Initialize the Store with Qdrant.

        Args:
            collection_name (str): The name of the collection.
            model_class (Type[BaseModel], optional): Model class for storing data.
            embedding_model (Union[str, CustomEmbeddingFunction]): Embedding model or function.
            embedding_api_key (str, optional): API key for embedding model.
            embedding_dimensions (int): Dimensionality of the embeddings.
            embedding_base_url (str, optional): Base URL for the embedding service.
            embedding_organization (str, optional): Organization for the embedding service.
            location (Union[Literal[":memory:"], str]): ":memory:" for in-memory database or a string path for persistent storage.
            persist_directory (str): Directory for persisting Qdrant database (if not using in-memory storage).
            chunk_size (int): Size of chunks for text splitting.
            model (Union[str, PredefinedModel]): Model name for text summarization.
        """
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        self.embedding_api_key = embedding_api_key
        self.embedding_dimensions = embedding_dimensions
        self.embedding_base_url = embedding_base_url
        self.embedding_organization = embedding_organization
        self.model_class = model_class
        self.location = location
        self.persist_directory = persist_directory
        self.chunk_size = chunk_size
        self.model = model

        self.client = self._initialize_client()
        self._create_or_get_collection()


    def _initialize_client(self):
        """
        Initialize Qdrant client. Use in-memory database if location is ":memory:",
        otherwise, use persistent storage at the specified directory.
        """
        if self.location == ":memory:":
            logger.info("Using in-memory Qdrant storage.")
            return QdrantClient(location=":memory:")
        else:
            logger.info(f"Using persistent Qdrant storage at {self.persist_directory}.")
            return QdrantClient(path=self.persist_directory)


    def _create_or_get_collection(self):
        """
        Retrieve or create a Qdrant collection with the specified configuration.
        """
        if not self.client.collection_exists(self.collection_name):
            logger.info(f"Creating collection '{self.collection_name}'.")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dimensions,
                    distance=Distance.COSINE
                )
            )
        else:
            logger.info(f"Collection '{self.collection_name}' already exists.")


    def _get_embedding(self, text: str) -> List[float]:
        """
        Generate embeddings for a given text using the custom embedding function.

        Args:
            text (str): The text to generate an embedding for.

        Returns:
            List[float]: The embedding for the text.
        """

        return embedding(
            text=text,
            model=self.embedding_model,
            dimensions=self.embedding_dimensions,
            base_url=self.embedding_base_url,
            organization=self.embedding_organization
        )

    def add(
        self,
        data: Union[str, List[str], Document, List[Document]],
        chunk_size: int = 512,
        metadata: Optional[dict] = None,
    ):
        """
        Add documents or data to Qdrant.

        Args:
            data (Union[str, List[str], Document, List[Document]]): The data to add to Qdrant.
            metadata (Optional[dict]): The metadata to add to the data.
        """
        if isinstance(data, str):
            data = [data]
        elif isinstance(data, Document):
            data = [data]

        points = []

        for item in data:
            try:
                if isinstance(item, Document):
                    text = item.content
                    item_metadata = item.metadata
                else:
                    text = item
                    item_metadata = metadata

                # Chunk the content
                chunks = chunk(inputs = text, chunk_size=chunk_size)

                for chunk_text in chunks:
                    embedding_vector = self._get_embedding(chunk_text)
                    point_id = str(uuid.uuid4())
                    chunk_metadata = item_metadata.copy() if item_metadata else {}
                    chunk_metadata["chunk"] = True
                    points.append(
                        PointStruct(
                            id=point_id,
                            vector=embedding_vector,
                            payload=chunk_metadata
                        )
                    )
            except Exception as e:
                logger.error(f"Error processing item: {item}. Error: {e}")

        if points:
            try:
                result = self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                if result.status == UpdateStatus.COMPLETED:
                    logger.info(f"Successfully added {len(points)} chunks to the collection.")
                else:
                    logger.error(f"Failed to add points to collection: {result.status}")
            except Exception as e:
                logger.error(f"Error adding points to collection: {e}")
        else:
            logger.warning("No valid embeddings to add to the collection.")


    def search(self, query: str, top_k: int = 5) -> List[dict]:
        """
        Search in Qdrant collection.

        Args:
            query (str): The query to search for.
            top_k (int): The number of results to return.

        Returns:
            List[dict]: The search results.
        """
        try:
            query_embedding = self._get_embedding(query)
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k
            )

            results = [
                {
                    "id": hit.id,
                    "text": hit.payload.get("text", ""),
                    "metadata": hit.payload,
                    "score": hit.score
                }
                for hit in search_results
            ]
            return results
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return []

    def _summarize_results(self, results: List[dict]) -> str:
        """
        Summarize the search results.

        Args:
            results (List[dict]): The search results.

        Returns:
            str: The summary of the search results.
        """

        class SummaryModel(BaseModel):
            summary: str

        texts = [result["text"] for result in results]
        combined_text = "\n\n".join(texts)

        summary = completion(
            response_model=SummaryModel,
            messages="Provide a concise summary of the following text, focusing on the most important information:",
            model=self.model,
        )

        return summary.summary

    def completion(
        self,
        messages: Union[str, List[dict]] = None,
        model: Optional[str] = None,
        top_k: Optional[int] = 5,
        tools: Optional[List[Union[Callable, dict, BaseModel]]] = None,
        run_tools: Optional[bool] = True,
        response_model: Optional[BaseModel] = None,
        verbose: Optional[bool] = False,
    ):
        """
        Perform completion with context from Qdrant.

        Args:
            messages (Union[str, List[dict]]): The messages to use for the completion.
            model (Optional[str]): The model to use for the completion.
            top_k (Optional[int]): The number of results to return from the search.
            tools (Optional[List[Union[Callable, dict, BaseModel]]]): The tools to use for the completion.
            run_tools (Optional[bool]): Whether to run the tools for the completion.
            response_model (Optional[BaseModel]): The response model to use for the completion.
            verbose (Optional[bool]): Whether to print messages to the console.
        """
        logger.info(f"Initial messages: {messages}")

        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        elif isinstance(messages, list):
            messages = [
                {"role": "user", "content": m} if isinstance(m, str) else m
                for m in messages
            ]

        query = messages[-1].get("content", "") if messages else ""

        try:
            results = self.search(query, top_k=top_k)
            summarized_results = self._summarize_results(results)
        except Exception as e:
            logger.error(f"Error during search or summarization: {e}")
            summarized_results = ""

        if messages:
            if not any(message.get("role", "") == "system" for message in messages):
                system_message = {
                    "role": "system",
                    "content": f"Relevant information retrieved: \n{summarized_results}",
                }
                messages.insert(0, system_message)
            else:
                for message in messages:
                    if message.get("role", "") == "system":
                        message["content"] += (
                            f"\nAdditional context: {summarized_results}"
                        )

        try:
            result = completion(
                messages=messages,
                model=model or self.model,
                tools=tools,
                run_tools=run_tools,
                response_model=response_model,
            )

            if verbose:
                logger.info(f"Completion result: {result}")

            return result
        except Exception as e:
            logger.error(f"Error during completion: {e}")
            raise

# Example main block to test
if __name__ == "__main__":
    try:
        # Initialize the Store
        store = Store(
            collection_name="test_collection", embedding_api_key="your-api-key"
        )

        # Test adding data
        store.add("This is a test string.")
        print("Added a test string.")

        # Test search
        search_query = "test"
        results = store.search(search_query, top_k=3)
        print(f"\nSearch results for '{search_query}':")
        for result in results:
            print(f"ID: {result['id']}, Text: {result['text']}, Metadata: {result['metadata']}")

        # Test completion
        completion_query = "What is the main topic?"
        completion_result = store.completion(completion_query)
        print(f"\nCompletion result for '{completion_query}':")
        print(completion_result)

    except Exception as e:
        logger.error(f"Error in main execution: {e}")

