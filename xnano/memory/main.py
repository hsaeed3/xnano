# memory client
# qdrant vector store

from pathlib import Path
import uuid
from typing import Literal, Optional, Union, Dict, Any, List

from .._lib import console, XNANOException
from ..types.nlp.embeddings import EmbeddingModel
from ..types.documents.document import Document
from ..types.memories.memory import MemoryLocation, DistanceType, DataType


class Memory:

    def __init__(
        self,

        # qdrant client/store args
        collection_name : str = "xnano_collection",
        location : Union[MemoryLocation, Path] = ":memory:",
        distance : DistanceType = "cosine",
        dimensions : int = 1536,

        # hnsw
        hnsw : bool = False,
        hnsw_m : int = 48,

        # verbosity
        verbose : bool = False,
    ):
        
        """
        Initializes the Qdrant Vector Store
        """

        # set verbosity
        self.verbose = verbose
        
        # set params
        self.collection_name = collection_name
        self.location = location
        self.distance = distance
        self.dimensions = dimensions
        # hnsw params
        self.hnsw = hnsw
        self.hnsw_m = hnsw_m

        # get imports
        from qdrant_client import QdrantClient

        try:
            if self._ensure_location_is_valid():
                self.client = QdrantClient(location=self.location)
            else:
                self.client = QdrantClient(path=self.location)
        except Exception as e:
            raise XNANOException(f"Invalid location: {e}") from e
        
        # init collection
        try:
            self._set_distance()
            self._create_or_load_collection()
        except Exception as e:
            raise XNANOException(f"Failed to initialize collection: {e}") from e
            

    def _ensure_location_is_valid(self) -> bool:
        """
        Ensures the location is valid & returns True if on memory
        """

        # if the location is not on memory, ensure we have a valid path
        if self.location != ":memory:":
            # Check if the location is a normal string and not a full path
            if not Path(self.location).is_absolute() and not self.location.startswith("./"):
                self.location = f"./{self.location}"

            path = Path(self.location)
            if not path.exists() or not path.is_dir():
                path.mkdir(parents=True, exist_ok=True)  # Create the directory if it does not exist
                if self.verbose:
                    console.message(f"Created Vector Store at Location: {self.location}")

            return False
        
        if self.verbose:
            console.message(f"Using [green]On Memory[/green] Vector Store")

        return True


    def _set_distance(self):
        """
        Sets the distance
        """
        try:
            from qdrant_client.models import Distance

            self.distance = Distance(self.distance.capitalize())

            if self.verbose:
                console.message(f"Using [sky_blue3]{self.distance}[/sky_blue3] Distance")
                console.message(f"Using a Dimension Size of [sky_blue3]{self.dimensions}[/sky_blue3]")

        except Exception as e:
            raise XNANOException(f"Invalid distance: {e}") from e


    def _create_or_load_collection(self):
        """
        Creates or loads the specified collection
        """
        from qdrant_client.models import VectorParams, HnswConfig

        if not self.client.collection_exists(self.collection_name):

            if self.verbose:
                console.message(f"Creating collection: [italic sky_blue3]{self.collection_name}[/italic sky_blue3]")

            if self.hnsw:
                if self.verbose:
                    console.message(f"Using [bold green]HNSW[/bold green] with [sky_blue3]{self.hnsw_m}[/sky_blue3] Links")
            
            try:
                self.client.create_collection(
                    collection_name = self.collection_name,
                    vectors_config = VectorParams(
                        size = self.dimensions,
                        distance = self.distance,
                        on_disk = False if self.location == ":memory:" else True
                    ),
                    hnsw_config = HnswConfig(
                        m = self.hnsw_m
                    ) if self.hnsw else None
                )
            except Exception as e:
                raise XNANOException(f"Failed to create collection: {e}") from e


    def _get_content_from_data(self, data : DataType, metadata : Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Gets the content from the data & returns a list of dicts in 
        content, metadata format
        """
        import time
        import uuid

        if not isinstance(data, list):
            data = [data]

        if self.verbose:
            console.message(f"Adding [sky_blue3]{len(data)}[/sky_blue3] items to memory")

        content = []

        for item in data:

            if isinstance(item, str):
                item_metadata = {
                    "time_added" : time.time(),
                    "id" : str(uuid.uuid4()),
                    "chunk_id" : None
                } 
                content.append({
                    "content" : item,
                    "metadata" : metadata
                })

            elif isinstance(item, Document):
                if not item.metadata:
                    item_metadata = {
                        "time_added" : time.time(),
                        "id" : str(uuid.uuid4()),
                        "chunk_id" : None
                    }
                else:
                    item_metadata = item.metadata

            elif isinstance(item, Dict):
                item_metadata = {
                    "time_added": time.time(),
                    "id": str(uuid.uuid4()),
                    "chunk_id" : None
                }
                content.append({
                    "content": item.get("content", ""),
                    "metadata": {**item_metadata, **(item.get("metadata", {}) or {})}
                })

            else:
                raise XNANOException(f"Invalid data type: {type(item)}")

        return content
    

    def _get_chunks(self, content : List[Dict[str, Any]], chunk_size : int = 2000) -> List[Dict[str, Any]]:
        """
        Gets the chunks from the content
        """
        import uuid
        from ..nlp import chunk
        
        results = []

        for item in content:

            if len(item["content"]) > chunk_size:

                try:

                    # TODO: 
                    # implement more sophisticated chunking
                    chunks = chunk(
                        inputs = item["content"],
                        chunk_size = chunk_size,
                        progress_bar = False
                    )

                    # Replace the item with the chunked documents
                    content = [
                        {
                            "content": chunk,
                            "metadata": {**item["metadata"].copy(), "chunk_id": str(uuid.uuid4())}
                        }
                        for chunk in chunks
                    ]

                    results.extend(content)

                    if self.verbose:
                            console.message(f"Chunked document [sky_blue3]{item['metadata']['id']}[/sky_blue3] into [sky_blue3]{len(chunks)}[/sky_blue3] chunks")

                except Exception as e:
                    raise XNANOException(f"Failed to chunk content for document {item['metadata']['id']}: {e}") from e
                
            else:
                results.append(item)

        return results



    def _get_embeddings(
        self,
        content: List[Dict[str, Any]],
        model: Union[str, EmbeddingModel],
        base_url : Optional[str] = None,
        api_key : Optional[str] = None,
        organization : Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates embeddings for the given content.
        If the content has chunk_id and chunks, it processes them accordingly.
        """
        embeddings = []

        from ..nlp.embedder import embedding

        for item in content:
            if "chunk_id" in item and "content" in item:
                # Process chunked content
                embedding_vector = embedding(
                    item["content"], model=model,
                    dimensions=self.dimensions,
                    base_url=base_url,
                    api_key=api_key,
                    organization=organization
                )
                embeddings.append({
                    "chunk_id": item["chunk_id"],
                    "embedding": embedding_vector,
                    "metadata": item.get("metadata", {})
                })
            else:
                # Process non-chunked content
                embedding_vector = embedding(item["content"], model=model)
                embeddings.append({
                    "embedding": embedding_vector,
                    "metadata": item.get("metadata", {})
                })

        # Ensure the content variable is returned after formatting
        return content
   
  
    def add(
            self,
            data : DataType,
            metadata : Optional[Dict[str, Any]] = None,
            
            chunk_size : int = 2000,
            model : Union[str, EmbeddingModel] = "text-embedding-3-small",
            base_url : Optional[str] = None,
            api_key : Optional[str] = None,
            organization : Optional[str] = None,
    ):
        """
        Adds data to the memory
        """
        from qdrant_client.models import UpdateStatus, PointStruct
        
        # get content
        try:
            content = self._get_content_from_data(data, metadata)
        except Exception as e:
            raise XNANOException(f"Failed to get content from data: {e}") from e

        # create chunks if needed
        try:
            content = self._get_chunks(content, chunk_size)
        except Exception as e:
            raise XNANOException(f"Failed to get chunks from content: {e}") from e
        
        # get embeddings
        try:
            content = self._get_embeddings(content, model, base_url, api_key, organization)
        except Exception as e:
            raise XNANOException(f"Failed to get embeddings from content: {e}") from e
        
        # create points
        try:
            points = [
                PointStruct(
                    id = item["metadata"]["id"],
                    vector = item["embedding"],
                    payload = item["metadata"]
                )
                for item in content
            ]
        except Exception as e:
            raise XNANOException(f"Failed to create points: {e}") from e
        
        # add to collection
        try:
            result = self.client.upsert(
                collection_name = self.collection_name,
                points = points
            )
            if result.status == UpdateStatus.COMPLETED:
                if self.verbose:
                    console.message(f"Successfully added [sky_blue3]{len(points)}[/sky_blue3] points to collection")
            else:
                raise XNANOException(f"Failed to add points to collection: {result.status}")
        except Exception as e:
            raise XNANOException(f"Failed to add points to collection: {e}") from e
        
        