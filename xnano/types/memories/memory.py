# memory types

from enum import Enum
from typing import Literal, Union, Type, List, Dict, Any
from ..documents.document import Document


# memory location literal helper
MemoryLocation = Union[Literal[":memory:"], str]


# distance types
DistanceType = Literal["cosine", "euclid", "dot", "manhattan"]


DataType = Union[
    str, List[str], 
    Dict[str, Any], List[Dict[str, Any]],
    Document, List[Document]
]
