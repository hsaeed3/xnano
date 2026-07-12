"""xnano_core.rust.engine

Runtime shim for the Rust-implemented engine submodule. Importing
:mod:`xnano_core.rust.native` registers the real module object on
``sys.modules`` under this name.
"""

import importlib
import sys


_DOC = __doc__

importlib.import_module("xnano_core.rust.native")

_engine = sys.modules.get("xnano_core.rust.engine")
if _DOC is not None and _engine is not None and _engine.__doc__ is None:
    _engine.__doc__ = _DOC
