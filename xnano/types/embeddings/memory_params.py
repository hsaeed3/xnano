# memory types

from enum import Enum
from typing import Literal, Union, Type, List, Dict, Any
from ..data.document import Document


# memory location literal helper
MemoryLocationParam = Union[Literal[":memory:"], str]


# distance types
MemoryDistanceParam = Literal["cosine", "euclid", "dot", "manhattan"]


# data types
MemoryDataTypeParam = Union[
    str, List[str], Dict[str, Any], List[Dict[str, Any]], Document, List[Document]
]
