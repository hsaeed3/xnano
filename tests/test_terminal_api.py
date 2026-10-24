"""
tests.test_terminal_api

The shape of the canvas's interface, automatic sizing and injected events.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib.util
import inspect
import pathlib
import re
import typing

import pytest
from documented_attributes import (
    documented_attributes,
    imported_names,
    is_documented_in,
    names_defined_at_runtime,
)

import xnano
import xnano.devices
from xnano_core import Event

SUBPACKAGES = (
    '_schema',
    '_internal',
    '_runtime',
    'appearance',
    'art',
    'audio',
    'hooks',
    'effects',
    'terminal',
)


def package_scripts(package: pathlib.Path) -> list[pathlib.Path]:
    """The scripts of the package: its modules and those of its subpackages."""
    scripts = sorted(package.glob('*.py'))
    for name in SUBPACKAGES:
        scripts.extend(sorted(package.glob(f'{name}/*.py')))
    return scripts


@pytest.fixture
def canvas():
    with xnano.new(width=20, height=6) as canvas:
        yield canvas


class TestAutomaticSizing:
    def test_everything_left_out_is_taken_from_the_content(self, canvas):
        placement = canvas.screen.write('hello')
        assert (placement.x, placement.y) == (0, 0)
        assert (placement.width, placement.height) == (5, 1)

    def test_several_lines_set_the_height(self, canvas):
        placement = canvas.screen.write('one\ntwo\nthree')
        assert (placement.width, placement.height) == (5, 3)

    def test_a_given_number_wins_over_the_content(self, canvas):
        placement = canvas.screen.write('hello', x=3, width=8)
        assert (placement.x, placement.width, placement.height) == (3, 8, 1)

    def test_a_cell_buffer_is_sized_by_the_buffer(self, canvas):
        from xnano_core import Buffer

        grid = Buffer.with_text('abcd').to_cell_grid()
        assert canvas.screen.write(Buffer.from_cell_grid(grid)).width == 4

    def test_each_axis_can_be_left_out_on_its_own(self, canvas):
        placement = canvas.screen.write('hello', y=2)
        assert (placement.x, placement.y, placement.width) == (0, 2, 5)


class TestInterface:
    def test_the_canvas_groups_what_is_not_declaring(self, canvas):
        assert isinstance(canvas.screen.output, xnano.devices.Output)
        assert isinstance(canvas.speaker, xnano.devices.Speaker)
        assert isinstance(canvas.clock, xnano.devices.Clock)

    def test_the_time_controls_are_part_of_the_interface(self, canvas):
        for name in ('iter', 'run', 'stop', 'open', 'push'):
            assert callable(getattr(canvas, name)), name
        for name in ('step', 'pause', 'resume', 'sleep'):
            assert callable(getattr(canvas.clock, name)), name
        assert callable(canvas.screen.render)

    def test_machinery_is_not_part_of_the_interface(self, canvas):
        for name in (
            'loop',
            'core',
            'run_soon',
            'snapshot',
            'advance',
            'frames',
            'is_live',
            'is_autonomous',
            'is_stopped',
            'backend',
            'inject',
            'tempo',
            'note',
        ):
            assert not hasattr(canvas, name), name

    def test_the_top_level_names_are_what_xnano_exports(self):
        public = {name for name in dir(xnano) if not name.startswith('_')}
        assert all(hasattr(xnano, name) for name in xnano.__all__)
        extra = public - set(xnano.__all__)
        left_over = {
            name
            for name in extra
            if not inspect.ismodule(getattr(xnano, name)) and name != 'TYPE_CHECKING'
        }
        assert left_over == set()

    @pytest.mark.parametrize(
        'name',
        ['axis_expression', 'axis_limits', 'to_rgb', 'Stop', 'fx', 'make'],
    )
    def test_machinery_is_not_exported(self, name):
        assert name not in xnano.__all__
        assert not hasattr(xnano, name)

    @pytest.mark.parametrize(
        'name',
        [
            'Sound',
            'load_sound',
            'AudioDevice',
            'TerminalSound',
            'TerminalNote',
            'TerminalMelody',
            'TerminalAudioEffect',
            'TerminalAudioPlayer',
            'TerminalMicrophone',
            'PlaySource',
        ],
    )
    def test_audio_keeps_only_its_own_names(self, name):
        assert name not in xnano.audio.__all__
        assert not hasattr(xnano.audio, name)

    def test_the_removed_modules_are_gone(self):
        import importlib

        for name in (
            'xnano.loop',
            'xnano._values',
            'xnano._attributes',
            'xnano._appearance',
            'xnano._decoration',
            'xnano._axes',
            'xnano._optional',
            'xnano._host',
            'xnano._hooks',
            'xnano._when',
            'xnano._customize',
            'xnano._effect_controller',
            'xnano.effects._schema',
            'xnano.pixel',
            'xnano.image',
            'xnano._media',
            'xnano.music',
        ):
            with pytest.raises(ModuleNotFoundError):
                importlib.import_module(name)

    def test_no_module_uses_any(self):
        package = pathlib.Path(xnano.__file__).parent
        offenders = []
        for path in package_scripts(package):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == 'Any':
                    offenders.append(f'{path.name}:{node.lineno}')
                if isinstance(node, ast.alias) and node.name == 'Any':
                    offenders.append(f'{path.name}: imports Any')
        assert offenders == []


class TestInjectedEvents:
    def test_every_kind_of_event_reaches_a_hook_on_the_canvas(self, canvas):
        events = {
            'key': Event.key_press('a'),
            'paste': Event.paste('text'),
            'resize': Event.resize(width=30, height=8),
            'focus_gained': Event.focus_gained(),
            'focus_lost': Event.focus_lost(),
            'custom': Event.custom('volume_changed', data='7'),
        }
        heard: list[str] = []

        @canvas.hook
        def listen(context: xnano.hooks.Context) -> None:
            assert context.event is not None
            heard.append(context.event.kind)

        for event in events.values():
            canvas.push(event)
        canvas.clock.step(delta_seconds=0.05)
        assert sorted(heard) == sorted(events)

    def test_a_custom_event_carries_a_name_and_data(self, canvas):
        seen: list[tuple[str | None, str | None]] = []

        @canvas.hook(on=lambda context: context.event.kind == 'custom')
        def volume(context: xnano.hooks.Context) -> None:
            seen.append((context.event.custom_name, context.event.custom_data))

        canvas.push(Event.custom('volume_changed', data='7'))
        canvas.clock.step(delta_seconds=0.05)
        assert seen == [('volume_changed', '7')]

    def test_pushing_into_a_closed_canvas_says_so(self):
        with xnano.new(width=4, height=1) as canvas:
            pass
        with pytest.raises(xnano.errors.TerminalClosedError):
            canvas.push(Event.wake())


@dataclasses.dataclass
class Settings:
    volume: int = 40
    muted: bool = False


class TestTypedState:
    def test_the_state_is_the_dataclass_that_was_given(self):
        with xnano.new(width=8, height=1, state=Settings()) as canvas:
            assert canvas.state.volume == 40
            canvas.state.volume = 55
            assert canvas.state.volume == 55

    def test_a_value_of_the_wrong_type_is_refused(self):
        with xnano.new(width=8, height=1, state=Settings()) as canvas:
            with pytest.raises(xnano.errors.TerminalError, match='volume'):
                canvas.state.volume = 'loud'  # type: ignore[assignment]

    def test_a_reference_drives_an_axis(self):
        with xnano.new(width=30, height=2, state=Settings()) as canvas:
            thumb = canvas.screen.write('#')
            thumb.x = canvas.state_reference(lambda state: state.volume)
            canvas.state.volume = 12
            canvas.clock.step(delta_seconds=0.05)
            assert thumb.x == 12

    def test_a_canvas_without_a_dataclass_still_has_a_state(self, canvas):
        canvas.state.set('volume', 3)
        assert canvas.state.get('volume') == 3

    def test_the_context_carries_the_same_state(self):
        with xnano.new(width=8, height=1, state=Settings()) as canvas:
            seen: list[int] = []

            @canvas.hook(on=lambda context: context.keyboard.key is not None)
            def press(context: xnano.hooks.Context[None, Settings]) -> None:
                context.root.state.volume += 5
                seen.append(context.root.state.volume)

            canvas.push(Event.key_press('up'))
            canvas.clock.step(delta_seconds=0.05)
            assert seen == [45]
            assert canvas.state.volume == 45
            assert typing.get_type_hints(Settings)['volume'] is int


class TestOutputCapture:
    def test_a_canvas_on_the_screen_that_cannot_hold_output_back_warns(self):
        from xnano.terminal._screen import warn_if_output_is_not_held_back

        with pytest.warns(RuntimeWarning, match='capture=False'):
            warn_if_output_is_not_held_back(requested=True, is_held_back=False)

    @pytest.mark.parametrize(
        ('requested', 'is_held_back'), [(True, True), (False, False)]
    )
    def test_nothing_is_said_when_it_was_not_needed_or_it_worked(
        self, requested, is_held_back
    ):
        import warnings

        from xnano.terminal._screen import warn_if_output_is_not_held_back

        with warnings.catch_warnings():
            warnings.simplefilter('error')
            warn_if_output_is_not_held_back(
                requested=requested, is_held_back=is_held_back
            )

    def test_a_canvas_off_the_screen_never_warns(self):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter('error')
            with xnano.new(width=4, height=1):
                pass


class TestDocumentation:
    PACKAGE = pathlib.Path(xnano.__file__).parent

    PENDING_REMOVAL: frozenset[str] = frozenset()
    """Modules a later part of this release removes, whose references may still be stale."""

    NOT_INSTALLED: frozenset[str] = (
        frozenset()
        if importlib.util.find_spec('pydantic_ai')
        else frozenset({'xnano.ai'})
    )
    """Modules whose extra is not installed, such as ``xnano.ai`` before Python 3.11."""

    @staticmethod
    def _resolves(dotted: str) -> bool:
        import importlib

        parts = dotted.split('.')
        for cut in range(len(parts), 0, -1):
            try:
                found: object = importlib.import_module('.'.join(parts[:cut]))
            except ImportError:
                continue
            for name in parts[cut:]:
                if hasattr(found, name):
                    found = getattr(found, name)
                elif name in getattr(found, '__annotations__', {}):
                    found = None
                else:
                    return False
            return True
        return False

    def test_cross_references_resolve(self):
        reference = re.compile(r'\]\[([A-Za-z_][\w.]*)\]')
        repository = self.PACKAGE.parent
        texts: list[tuple[str, str]] = []
        for path in package_scripts(self.PACKAGE):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                    if isinstance(node.value.value, str):
                        texts.append((path.name, node.value.value))
        documents = [
            repository / 'README.md',
            *sorted((repository / 'docs' / 'learn').rglob('*.md')),
        ]
        texts.extend((path.name, path.read_text(encoding='utf-8')) for path in documents)
        broken = sorted(
            {
                f'{where}: {dotted}'
                for where, text in texts
                for dotted in reference.findall(text)
                if not self._resolves(dotted)
                and not any(
                    dotted == module or dotted.startswith(f'{module}.')
                    for module in self.PENDING_REMOVAL | self.NOT_INSTALLED
                )
            }
        )
        assert broken == []

    def test_every_public_attribute_has_inline_documentation(self):
        repository = self.PACKAGE.parent
        paths = [
            path for path in self.PACKAGE.glob('*.py') if not path.name.startswith('_')
        ]
        paths.extend(self.PACKAGE.glob('appearance/*.py'))
        paths.extend(self.PACKAGE.glob('art/*.py'))
        paths.extend(self.PACKAGE.glob('audio/*.py'))
        paths.extend(self.PACKAGE.glob('hooks/*.py'))
        paths.extend(self.PACKAGE.glob('effects/*.py'))
        paths.extend(self.PACKAGE.glob('terminal/*.py'))
        paths.extend(self.PACKAGE.glob('_schema/*.py'))
        paths.extend(repository.glob('packages/*/src/**/*.py'))
        paths.extend(repository.glob('packages/*/src/**/*.pyi'))
        missing = []
        for path in sorted(paths):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if not isinstance(node, ast.ClassDef) or node.name.startswith('_'):
                    continue
                for index, member in enumerate(node.body):
                    if isinstance(member, ast.FunctionDef):
                        if member.name.startswith('_'):
                            continue
                        is_property = any(
                            ast.unparse(decorator) == 'property'
                            for decorator in member.decorator_list
                        )
                        if is_property and not ast.get_docstring(member):
                            missing.append(
                                f'{path.relative_to(repository)}:{node.name}.{member.name}'
                            )
                    elif isinstance(member, ast.AnnAssign) and isinstance(
                        member.target, ast.Name
                    ):
                        if member.target.id.startswith('_'):
                            continue
                        following = (
                            node.body[index + 1] if index + 1 < len(node.body) else None
                        )
                        has_docstring = (
                            isinstance(following, ast.Expr)
                            and isinstance(following.value, ast.Constant)
                            and isinstance(following.value.value, str)
                            and bool(following.value.value.strip())
                        )
                        if not has_docstring:
                            missing.append(
                                f'{path.relative_to(repository)}:{node.name}.{member.target.id}'
                            )
        assert missing == []

    def test_stub_classes_with_readable_attributes_list_their_meanings(self):
        repository = self.PACKAGE.parent
        missing = []
        for path in sorted(repository.glob('packages/*/src/**/*.pyi')):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if not isinstance(node, ast.ClassDef) or node.name.startswith('_'):
                    continue
                attributes = []
                for member in node.body:
                    if isinstance(member, ast.AnnAssign) and isinstance(
                        member.target, ast.Name
                    ):
                        if not member.target.id.startswith('_'):
                            attributes.append(member.target.id)
                    elif isinstance(
                        member, ast.FunctionDef
                    ) and not member.name.startswith('_'):
                        if any(
                            ast.unparse(decorator) == 'property'
                            for decorator in member.decorator_list
                        ):
                            attributes.append(member.name)
                # Operations and other classes without readable attributes have no
                # attribute section; their constructor arguments belong in Args.
                if not attributes:
                    continue
                docstring = ast.get_docstring(node) or ''
                if 'Attributes:' not in docstring:
                    missing.append(f'{path.relative_to(repository)}:{node.name}')
                    continue
                section = docstring.split('Attributes:', 1)[1]
                missing.extend(
                    f'{path.relative_to(repository)}:{node.name}.{name}'
                    for name in attributes
                    if f'{name}:' not in section
                )
        assert missing == []

    def test_every_public_class_lists_its_attributes(self):
        missing = []
        for path in package_scripts(self.PACKAGE):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if not isinstance(node, ast.ClassDef) or node.name.startswith('_'):
                    continue
                bases = [ast.unparse(base) for base in node.bases]
                if any('Protocol' in base or 'Error' in base for base in bases):
                    continue
                if 'Attributes:' not in (ast.get_docstring(node) or ''):
                    missing.append(f'{path.name}:{node.name}')
        assert missing == []

    def test_examples_use_the_names_xnano_exports_without_renaming_them(self):
        renamed = []
        for path in package_scripts(self.PACKAGE):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                docstring = (
                    ast.get_docstring(node)
                    if isinstance(
                        node,
                        (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
                    )
                    else None
                )
                for line in (docstring or '').splitlines():
                    stripped = line.strip()
                    if (
                        stripped.startswith(('from xnano', 'import xnano'))
                        and ' as ' in stripped
                    ):
                        renamed.append(f'{path.name}: {stripped}')
        assert renamed == []

    def test_every_constructor_has_a_docstring(self):
        missing = [
            f'{path.name}:{node.name}'
            for path in package_scripts(self.PACKAGE)
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8')))
            if isinstance(node, ast.ClassDef)
            for method in node.body
            if isinstance(method, ast.FunctionDef)
            and method.name == '__init__'
            and not ast.get_docstring(method)
        ]
        assert missing == []

    def test_every_module_starts_with_its_own_name(self):
        wrong = []
        for path in package_scripts(self.PACKAGE):
            parts = path.relative_to(self.PACKAGE).with_suffix('').parts
            if parts[-1] == '__init__':
                parts = parts[:-1]
            expected = '.'.join(('xnano', *parts))
            docstring = (
                ast.get_docstring(ast.parse(path.read_text(encoding='utf-8'))) or ''
            )
            if docstring.splitlines()[0:1] != [expected]:
                wrong.append(str(path.relative_to(self.PACKAGE)))
        assert wrong == []


class TestDocumentationSite:
    ROOT = pathlib.Path(xnano.__file__).resolve().parent.parent

    def test_the_reference_is_read_from_the_source(self):
        text = (self.ROOT / 'zensical.toml').read_text()
        assert re.search(
            r'^\[project\.plugins\.mkdocstrings\.handlers\.python\]', text, re.M
        )
        assert re.search(
            r'^\[project\.plugins\.mkdocstrings\.handlers\.python\.options\]', text, re.M
        )

    def test_every_page_in_the_navigation_exists(self):
        text = (self.ROOT / 'zensical.toml').read_text()
        navigation = text[text.index('nav = [') :]
        pages = re.findall(r'^\s*\{?[^#\n]*?"([\w/.-]+\.md)"', navigation, re.M)
        assert pages
        missing = [page for page in pages if not (self.ROOT / 'docs' / page).exists()]
        assert missing == []


class TestOutputCaptureStatus:
    def test_a_canvas_off_the_screen_holds_nothing_back(self):
        with xnano.new(width=4, height=1) as canvas:
            assert canvas.screen.output.is_captured is False


class TestReturnTypesAreReachable:
    def test_hook_handles_and_effect_controllers_are_public_types(self):
        import xnano.effects
        import xnano.effects._controller
        import xnano.hooks
        import xnano.hooks._handles
        import xnano.operations

        assert (
            xnano.hooks.HookHandle
            is xnano.hooks.HookHandle
            is xnano.hooks._handles.HookHandle
        )
        assert (
            xnano.effects.EffectController
            is xnano.effects.EffectController
            is xnano.effects._controller.EffectController
        )
        assert xnano.effects.EffectSpecification is not xnano.operations.Effect
        assert (
            xnano.effects.WritableEffectProperties
            is xnano.effects.WritableEffectProperties
        )
        for name in ('fx', 'Customization', 'CustomizationKind'):
            assert name not in xnano.operations.__all__

    def test_hook_lives_in_the_hooks_package(self):
        import xnano
        import xnano.hooks
        import xnano.operations

        assert xnano.hook is xnano.hooks.hook
        assert not hasattr(xnano.operations, 'hook')
        assert 'hook' not in xnano.operations.__all__
        assert xnano.hooks.When is xnano.hooks.When
        assert xnano.hooks.Hook is xnano.hooks.Hook
        assert xnano.hooks.HookKind is xnano.hooks.HookKind
        assert xnano.hooks.HookResult is xnano.hooks.HookResult
        assert not hasattr(xnano, 'HookGenerator')
        assert not hasattr(xnano.hooks, 'HookGenerator')

    def test_terminal_settings_live_in_the_terminal_package(self):
        import xnano
        import xnano.canvas
        import xnano.terminal

        assert xnano.terminal.TerminalSettings is xnano.terminal.TerminalSettings
        assert not hasattr(xnano, 'GateSettings')
        assert not hasattr(xnano.canvas, '_GATE_NAMES')
        assert not hasattr(xnano.canvas, '_split_settings')
        assert not hasattr(xnano.canvas.Canvas, '_attach_screen')
        assert not hasattr(xnano.canvas.Canvas, '_gates_for_screen')

    def test_the_hook_aliases_take_the_dependencies_and_state_types(self):
        import typing

        import xnano.hooks

        assert len(xnano.hooks.Hook.__type_params__) == 2
        assert len(xnano.hooks.HookResult.__type_params__) == 2
        assert len(xnano.hooks.When.__type_params__) == 2
        assert typing.get_args(xnano.hooks.Hook[int, int]) == (int, int)
        assert typing.get_args(xnano.hooks.When[int, int]) == (int, int)
        assert xnano.hooks.When is xnano.hooks.When
        assert typing.get_args(xnano.hooks.HookResult[None, None]) == (None, None)
        assert typing.get_args(xnano.hooks.Hook[None, None]) == (None, None)


def test_the_expressions_module_lists_only_its_public_names() -> None:
    import importlib.util

    import xnano.expressions

    specification = importlib.util.spec_from_file_location(
        'fresh_expressions', xnano.expressions.__file__
    )
    assert specification is not None
    assert specification.loader is not None
    fresh = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(fresh)

    assert 'Width' not in vars(fresh)
    assert dir(fresh) == sorted(fresh.__all__)
    fresh.Width  # noqa: B018
    assert 'Width' in vars(fresh)
    assert dir(fresh) == sorted(fresh.__all__)
    assert dir(xnano.expressions) == sorted(xnano.expressions.__all__)


LAZY_REEXPORT_MODULES = [
    'xnano.expressions',
    'xnano.styles',
    'xnano.layout',
    'xnano.events',
    'xnano.buffers',
    'xnano.widgets',
    'xnano.operations',
]

LAZY_MODULES = [*LAZY_REEXPORT_MODULES, 'xnano.audio']


@pytest.mark.parametrize('module_name', LAZY_MODULES)
class TestLazyModules:
    def test_dir_lists_exactly_the_public_names(self, module_name: str) -> None:
        module = importlib.import_module(module_name)
        assert dir(module) == sorted(module.__all__)

    def test_every_public_name_resolves(self, module_name: str) -> None:
        module = importlib.import_module(module_name)
        for name in module.__all__:
            assert getattr(module, name) is not None, name

    def test_an_unknown_name_is_refused_in_the_name_of_the_module(
        self, module_name: str
    ) -> None:
        module = importlib.import_module(module_name)
        with pytest.raises(AttributeError, match=module_name):
            module.NoSuchName  # noqa: B018


@pytest.mark.parametrize('module_name', LAZY_REEXPORT_MODULES)
def test_every_lazy_name_is_documented_with_an_example(module_name: str) -> None:
    module = importlib.import_module(module_name)
    tree = ast.parse(pathlib.Path(module.__file__).read_text(encoding='utf-8'))
    documented = dict(documented_attributes(tree))
    imported = imported_names(tree)
    lazy_names = set(module.__all__) - names_defined_at_runtime(tree)
    assert lazy_names, f'{module_name} defines every one of its names at runtime'
    undocumented = sorted(
        name
        for name in lazy_names - documented.keys()
        if name not in imported or not is_documented_in(imported[name], name)
    )
    assert not undocumented, (
        f'These names of {module_name} have no docstring where they are defined: '
        f'{undocumented}.'
    )
    # A name imported from where it is defined keeps its example there.
    for name in sorted(lazy_names & documented.keys()):
        assert '```python' in documented[name], f'{module_name}.{name} has no example'


def test_the_target_size_expression_lives_only_in_the_expressions_module() -> None:
    import xnano.buffers
    import xnano.expressions
    import xnano_core

    assert 'TargetSize' not in xnano.buffers.__all__
    with pytest.raises(AttributeError, match='xnano.buffers'):
        xnano.buffers.TargetSize  # noqa: B018
    assert xnano.expressions.TargetSize is xnano_core.BufferSize


class TestWidgetsFigure:
    FIGURE_NAMES = {
        'Figure': 'Canvas',
        'FigureCircle': 'CanvasCircle',
        'FigureLabel': 'CanvasLabel',
        'FigureLine': 'CanvasLine',
        'FigureMap': 'CanvasMap',
        'FigurePoints': 'CanvasPoints',
        'FigureRectangle': 'CanvasRectangle',
    }

    @pytest.mark.parametrize(('name', 'core_name'), FIGURE_NAMES.items())
    def test_the_figure_classes_are_the_core_canvas_classes(
        self, name: str, core_name: str
    ) -> None:
        import xnano.widgets
        import xnano_core

        assert getattr(xnano.widgets, name) is getattr(xnano_core, core_name)

    def test_the_drawing_widget_is_no_longer_called_canvas(self) -> None:
        import xnano.widgets

        assert 'Canvas' not in xnano.widgets.__all__
        assert not hasattr(xnano.widgets, 'Canvas')
        assert not [name for name in xnano.widgets.__all__ if name.startswith('Canvas')]
        for core_name in self.FIGURE_NAMES.values():
            assert not hasattr(xnano.widgets, core_name)


def test_the_color_value_alias_is_public_in_styles():
    import xnano.styles

    assert 'ColorValue' in xnano.styles.__all__
