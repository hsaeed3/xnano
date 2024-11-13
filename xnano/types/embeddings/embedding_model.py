# embeddings

from typing import Literal


# model
EmbeddingModel = Literal[
    "text-embedding-3-small",
    "text-embedding-3-large",
    "ollama/nomic-embed-text",
    "ollama/mxbai-embed-large",
    "ollama/all-minilm",
    "fastembed/BAAI/bge-small-en-v1.5",
    "fastembed/BAAI/bge-small-zh-v1.5",
    "fastembed/snowflake/snowflake-arctic-embed-xs",
    "fastembed/sentence-transformers/all-MiniLM-L6-v2",
    "fastembed/jinaai/jina-embeddings-v2-small-en",
    "fastembed/BAAI/bge-small-en",
    "fastembed/snowflake/snowflake-arctic-embed-s",
    "fastembed/nomic-ai/nomic-embed-text-v1.5-Q",
    "fastembed/BAAI/bge-base-en-v1.5",
    "fastembed/sentence-transformers/paraphrase-multilingual-...",
    "fastembed/Qdrant/clip-ViT-B-32-text",
    "fastembed/jinaai/jina-embeddings-v2-base-de",
    "fastembed/BAAI/bge-base-en",
    "fastembed/snowflake/snowflake-arctic-embed-m",
    "fastembed/nomic-ai/nomic-embed-text-v1.5",
    "fastembed/jinaai/jina-embeddings-v2-base-en",
    "fastembed/nomic-ai/nomic-embed-text-v1",
    "fastembed/snowflake/snowflake-arctic-embed-m-long",
    "fastembed/mixedbread-ai/mxbai-embed-large-v1",
    "fastembed/jinaai/jina-embeddings-v2-base-code",
    "fastembed/sentence-transformers/paraphrase-multilingual-...",
    "fastembed/snowflake/snowflake-arctic-embed-l",
    "fastembed/thenlper/gte-large",
    "fastembed/BAAI/bge-large-en-v1.5",
    "fastembed/intfloat/multilingual-e5-large",
]
