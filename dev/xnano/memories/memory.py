# memories
# vector store client for vector search & retrieval
# used for agentic memory

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue
)
from qdrant_client.http.models import UpdateStatus
