# singleton console object with helper methods
# used internally

# builtins -- xnano swaps out print with rich.print
import builtins
from rich import print

# console & ext imports
from rich.console import Console
from rich.progress import Progress, track

# imports
from contextlib import contextmanager
import inspect
from typing import Tuple
import questionary


# print swap
builtins.print = print


# console resource
class RichConsole(Console):
    """Console Resource"""

    # super
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # input collection method
    # uses questionary not rich.prompt
    def ask(self, prompt) -> str:
        """
        Collects input from the user. If a list is provided, displays a radio list.

        Example:
            console.ask("What is your name?")
            console.ask(["Option 1", "Option 2", "Option 3"])

        Args:
            prompt (Union[str, list]): Prompt to display to the user or list of options
        """
        if isinstance(prompt, list):
            # Use questionary to display a radio list with arrow key and number selection
            return questionary.select("Please select an option:", choices=prompt).ask()
        return questionary.text(prompt).ask()

    # confirmation method
    # uses questionary not rich.prompt
    def confirm(self, prompt) -> bool:
        """
        Collects a yes/no confirmation from the user.

        Example:
            console.confirm("Do you want to continue?")

        Args:
            prompt (str): Prompt to display to the user
        """
        return questionary.confirm(prompt).ask()

    # message printer for all 'verbose' message for methods
    def message(self, message: str):
        """
        Sends xnano message to the console

        Example:
            console.message("This is a message")

        Args:
            message (str): Message to display in the console
        """
        frame = inspect.currentframe().f_back
        module = frame.f_globals["__name__"]
        self.print(
            f"⚛️ [bold plum3] xnano[/bold plum3] | [cyan]{module}[/cyan] | [white italic]{message}[/white italic]"
        )

    # warning method
    # no exception -- exceptions raised by xnano.lib.common.exceptions
    def warning(self, message: str):
        """
        Prints a warning message to the console

        Example:
            console.warning("This is a warning message")

        Args:
            message (str): Message to display in the warning
        """
        frame = inspect.currentframe().f_back
        module = frame.f_globals["__name__"]
        self.print(
            f"⚠️ [bold yellow] XNANO WARNING[/bold yellow] | [yellow]{module}[/yellow] | [yellow italic]{message}[/yellow italic]"
        )

    # context manager for constant progress loader
    @contextmanager
    def progress(self, prompt: str, *args, **kwargs) -> Tuple[Progress, int, int]:
        """
        Quick rich.progress manager

        Example:
            with console.progress("Loading...") as (progress, task, task_id):
                progress.update(task, advance=1)
                # ...

        Args:
            prompt (str): Message to display in the progress loader
            *args: Additional arguments to pass to the rich.progress.Progress constructor
            **kwargs: Additional keyword arguments to pass to the rich.progress.Progress constructor

        Returns:
            Tuple[Progress, int, int]: Progress object, task, and task id
        """
        with Progress(*args, **kwargs, console=self, transient=True) as progress:
            task = progress.add_task(f"[plum3]{prompt}[/plum3]", total=None)
            task_id = task
            progress.start()
            try:
                yield progress
            finally:
                progress.stop()

    # track method
    # for iterable progress -- .progress if used for a static loader
    def track(self, iterable, prompt: str):
        """
        Track progress of an iterable

        Example:
            for item in console.track(range(100), "Loading..."):
                # ...

        Args:
            iterable: Iterable to track progress of
            prompt (str): Message to display in the progress loader
        """
        return track(iterable, description=prompt)


# singleton
console = RichConsole()


# test
if __name__ == "__main__":
    console.message("This is a test message")

    console.warning("This is a test warning")
