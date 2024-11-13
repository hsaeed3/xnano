# document export (idk if this is really needed no ones ever going to touch it)

from ...types.data.document import Document
from .mixin import patch


Document = patch(Document)
