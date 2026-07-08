"""xnano.beta.core"""

# version constraint check happens on first import
# of xnano.beta.core
from xnano.beta.core.version import _ensure_xnano_core_version

_ensure_xnano_core_version()
del _ensure_xnano_core_version
