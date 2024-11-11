# embeddings

from typing import Literal


# model
EmbeddingModel = Literal["text-embedding-3-small", "text-embedding-3-large",
                         "ollama/nomic-embed-text", "ollama/mxbai-embed-large",
                         "ollama/all-minilm"]
