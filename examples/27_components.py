"""
Components: functions and classes that draw themselves.

``@xnano.renderable`` turns a function of ``(context, **own_parameters)`` into a component:
``canvas.write(gauge(label='cpu'))`` draws it, and it is drawn again each frame only because
it read the clock; a component that reads nothing dynamic is drawn once. Any class with a
``__xnano_render__`` method is a component too. Dependencies given to ``xnano.new(deps=...)``
reach every component as ``context.deps``. ``gauge.hook(...)`` attaches a hook to every
placement of the component, and receives the component's own parameters; the hook counts what
it heard in ``context.plugin.state``, which each placement keeps for itself. Press ``r`` to say
which gauge heard it, ``h`` for a hook that needs the dependencies (``requires_deps=True``),
and ``q`` to quit.
"""

import dataclasses
import math

import xnano
from xnano.components import ComponentContext
from xnano.context import Context


@dataclasses.dataclass(frozen=True)
class Services:
    """What the components share."""

    host: str
    """The name shown in the badge."""


@xnano.renderable
def gauge(context: Context[Services], label: str, speed: float = 0.5) -> str:
    """A bar that fills and empties on the clock."""
    filled = round((math.sin(context.time.elapsed * speed * math.tau) + 1) / 2 * 20)
    return f'{label:<6}[{"#" * filled}{"." * (20 - filled)}]'


@dataclasses.dataclass(frozen=True)
class Badge:
    """A component that is a plain class: the method is all it needs."""

    name: str

    def __xnano_render__(self, context: Context[Services]) -> str:
        return f'{self.name} on {context.deps.host}'


with xnano.open(width=40, height=6, deps=Services(host='xnano.local')) as terminal:
    terminal.write(Badge('dashboard'))
    terminal.write(gauge(label='cpu', speed=0.5), y=2)
    terminal.write(gauge(label='memory', speed=0.25), y=3)
    message = terminal.write('press r to ask a gauge, h for the host', y=5)

    @terminal.hook(on='key', keys='h', requires_deps=True)
    def host(context: Context[Services]) -> None:
        message.text = f'the dependencies name {context.deps.host}'

    @gauge.hook(on='key', keys='r')
    def answer(context: Context, component: ComponentContext) -> None:
        state = context.plugin.state
        earlier = state.get('heard', default=0)
        heard = earlier + 1 if isinstance(earlier, int) else 1
        state.push('heard', heard)
        message.text = f'the {component.arguments["label"]} gauge heard r, {heard} in all'

    terminal.run(quit_on='q')
