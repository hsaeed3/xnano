"""xnano"""

from xnano.beta.core.version import VERSION, _ensure_xnano_core_version

_ensure_xnano_core_version()
del _ensure_xnano_core_version

__version__ = VERSION
