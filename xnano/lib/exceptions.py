# base exception class used internally

import inspect
from rich.console import Console
from rich.traceback import install
from typing import Optional


# exception console
console = Console()


# install rich traceback
install(console=console)


# xnano exception
class XNANOException(Exception):
    """Base exception class for xnano."""

    def __init__(self, message: str, exception_name: Optional[str] = "XNANO"):
        # self.message is implemented with rich color tags
        # llxm uses rich .print as a builtin print method
        # console handles all other printing

        frame = inspect.currentframe().f_back

        if exception_name is None:
            exception_name = "XNANO"

        module = frame.f_globals["__name__"]

        self.message = f"[red]{exception_name} [italic bold white]{module}[/italic bold white] Exception:[/red] {message}"

    def __str__(self):
        # minimal message sent as non rich output
        return "XNANO Exception Occured"

    # prints exception message on exit (to use rich formatting)
    def __del__(self):
        console.print(self.message)


# test
if __name__ == "__main__":
    raise XNANOException("This is a test exception")
