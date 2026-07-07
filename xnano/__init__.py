"""xnano

>>> import xnano.beta as x
>>> from xnano.beta import Grid, Field, Terminal
"""

from xnano.beta.core.version import VERSION, _ensure_xnano_core_version

_ensure_xnano_core_version()
del _ensure_xnano_core_version

__version__ = VERSION
