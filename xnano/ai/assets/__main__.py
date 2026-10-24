"""
xnano.ai.assets.__main__

``python -m xnano.ai.assets``: list, install, remove and find the libraries of examples.
"""

import sys

from xnano.ai.assets import _main

if __name__ == '__main__':
    sys.exit(_main(sys.argv[1:]))
