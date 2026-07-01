import time
from xnano.terminal import Terminal
from xnano.widgets import Block
from xnano.layout import Layout

# Explicitly define named layout regions using a dictionary
layout = Layout(
    direction="vertical",
    constraints={
        "header": 3,
        "body": "fill",
        "footer": 3
    }
)

with Terminal() as terminal:
    start_time = time.time()
    while time.time() - start_time < 3.0:
        elapsed = time.time() - start_time

        # Explicit, self-documenting mapping from layout keys to widgets/strings
        # Uses frame.area() dynamically to adapt to any terminal window size
        terminal.draw(
            lambda frame: layout.map(
                frame.area(),
                widgets={
                    "header": "  Dashboard Header",
                    "body": Block(borders="all", title=f" Main Content - {elapsed:.2f}s "),
                    "footer": "  Status: Active"
                }
            )
        )
        time.sleep(0.016)  # ~60 FPS