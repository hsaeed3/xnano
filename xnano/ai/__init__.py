"""
xnano.ai

Language models, decision models and agents that work on a canvas: task models that decide what
a widget does, judge what is on the screen, keep state, and write text, pixel art, components and
melodies.

Each task model lives in a module of [`xnano.ai.models`][xnano.ai.models], named for what it
makes, and is exported from ``xnano.ai`` too, so ``from xnano.ai import ArtModel`` works:

| Module | Models |
| --- | --- |
| [`xnano.ai.models.decisions`][xnano.ai.models.decisions] | ``ChoiceModel`` and ``JudgeModel``: pick an option, or judge a claim |
| [`xnano.ai.models.state`][xnano.ai.models.state] | ``StateModel``: move a program's state from one value to the next |
| [`xnano.ai.models.text`][xnano.ai.models.text] | ``TextModel``: write and stream text into a placement |
| [`xnano.ai.models.art`][xnano.ai.models.art] | ``ArtModel``: generate, edit and animate pixel art |
| [`xnano.ai.models.components`][xnano.ai.models.components] | ``ComponentModel``: write a component as a program |
| [`xnano.ai.models.music`][xnano.ai.models.music] | ``MusicModel``: write melodies |

Each one owns one pydantic-ai agent. Its methods take what is on the canvas as evidence (a hook's
[`Context`][xnano.hooks.Context], a canvas, a placement, or a mapping of them with the facts the
program knows) and return xnano values. Every method that asks a model has two spellings:
``choose()`` waits for the answer, and ``choose_async()`` is awaited. They share the errors and
reports of a generation, the evidence they read, and the plugins that run them from hooks, all
defined here; [`xnano.ai.capabilities`][xnano.ai.capabilities] gives an agent the canvas.

Decision models (``'typesafe:jev-1.14.0'``) answer typed questions with probabilities in a
fraction of a second, which suits what happens on a key press; language models
(``'openrouter:anthropic/claude-sonnet-5-5'``) write text and drawings. Install with
``pip install "xnano[ai]"``; it needs Python 3.11 or newer.

[`xnano.ai.testing`][xnano.ai.testing] has models that answer from a script, for tests and for
trying a program without credentials.

Examples:
    ```python
    import xnano
    from xnano.ai import ChoiceModel
    from xnano.ai.testing import ScriptedDecisionModel
    from xnano.events import Event

    pick = ChoiceModel(ScriptedDecisionModel({'response': 'wave'}))

    with xnano.new(width=20, height=2) as canvas:
        hero = canvas.screen.write('hero')

        @hero.hook(on='key', keys='enter')
        def react(context: xnano.Context) -> None:
            decision = pick.choose(context, {'wave': 'greet the player', 'hide': 'run away'})
            hero.text = f'hero: {decision.choice}'

        canvas.push(Event.key_press('enter'))
        canvas.clock.step()
        assert canvas.screen.render().splitlines()[0] == 'hero: wave'
    ```
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 11):
    raise ImportError(
        'xnano.ai needs Python 3.11 or newer, because pydantic-ai does, but this is Python '
        f'{sys.version_info.major}.{sys.version_info.minor}. Run the program with a newer Python.'
    )

from xnano._internal._optional import require

_pydantic_ai = require('ai', needed_for='xnano.ai')
# The banner pydantic-ai prints on its first run would be drawn over the canvas.
_pydantic_ai.BANNER_ENABLED = False

from pydantic_ai import BoolCriteria as BoolCriteria  # noqa: E402
from pydantic_ai import Choice as Choice  # noqa: E402
from pydantic_ai import Choices as Choices  # noqa: E402
from pydantic_ai import ModelRetry as ModelRetry  # noqa: E402
from pydantic_ai.models.decision import DecisionHandOff as DecisionHandOff  # noqa: E402
from pydantic_ai.models.fallback import FallbackModel as FallbackModel  # noqa: E402

from xnano.ai._background import BackgroundRun, BackgroundRuns, background  # noqa: E402
from xnano.ai._generations import Critique, GenerationError, GenerationReport  # noqa: E402
from xnano.ai._observe import Evidence, Observation, observe  # noqa: E402
from xnano.ai._plugins import decide, watch  # noqa: E402
from xnano.ai.models import TaskModel, is_decision_model, run_to_completion  # noqa: E402
from xnano.ai.models.art import (  # noqa: E402
    Animation,
    ArtModel,
    ArtPatch,
    ArtSize,
    ArtStrategy,
    ArtText,
    ColorRole,
    EditMode,
    PaletteColor,
    PixelRun,
)
from xnano.ai.models.components import Component, ComponentModel  # noqa: E402
from xnano.ai.models.decisions import (  # noqa: E402
    ChoiceModel,
    Decision,
    JudgeModel,
    Options,
    Score,
    Verdict,
)
from xnano.ai.models.music import Meter, MusicModel  # noqa: E402
from xnano.ai.models.state import StateModel, StateTransition  # noqa: E402
from xnano.ai.models.text import TextModel, stream_into, stream_into_async  # noqa: E402

__all__ = [
    'Animation',
    'ArtModel',
    'ArtPatch',
    'ArtSize',
    'ArtStrategy',
    'ArtText',
    'BackgroundRun',
    'BackgroundRuns',
    'BoolCriteria',
    'Choice',
    'ChoiceModel',
    'Choices',
    'ColorRole',
    'Component',
    'ComponentModel',
    'Critique',
    'Decision',
    'DecisionHandOff',
    'EditMode',
    'Evidence',
    'FallbackModel',
    'GenerationError',
    'GenerationReport',
    'JudgeModel',
    'Meter',
    'ModelRetry',
    'MusicModel',
    'Observation',
    'Options',
    'PaletteColor',
    'PixelRun',
    'Score',
    'StateModel',
    'StateTransition',
    'TaskModel',
    'TextModel',
    'Verdict',
    'background',
    'decide',
    'is_decision_model',
    'observe',
    'run_to_completion',
    'stream_into',
    'stream_into_async',
    'watch',
]
