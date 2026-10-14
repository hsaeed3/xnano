"""
tests.test_terminal_api

The shape of the terminal's interface, automatic sizing and injected events.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import pathlib
import typing

import pytest

import xnano
from xnano_core import Event


@pytest.fixture
def terminal():
    with xnano.iter(offscreen=True, width=20, height=6) as terminal:
        yield terminal


class TestAutomaticSizing:
    def test_everything_left_out_is_taken_from_the_content(self, terminal):
        placement = terminal.write('hello')
        assert (placement.x, placement.y) == (0, 0)
        assert (placement.width, placement.height) == (5, 1)

    def test_several_lines_set_the_height(self, terminal):
        placement = terminal.write('one\ntwo\nthree')
        assert (placement.width, placement.height) == (5, 3)

    def test_a_given_number_wins_over_the_content(self, terminal):
        placement = terminal.write('hello', x=3, width=8)
        assert (placement.x, placement.width, placement.height) == (3, 8, 1)

    def test_bytes_of_a_cell_grid_are_sized_by_the_grid(self, terminal):
        from xnano_core import Buffer

        grid = Buffer.with_text('abcd').to_cell_grid()
        assert terminal.write(grid).width == 4

    def test_each_axis_can_be_left_out_on_its_own(self, terminal):
        placement = terminal.write('hello', y=2)
        assert (placement.x, placement.y, placement.width) == (0, 2, 5)


class TestInterface:
    def test_the_terminal_groups_what_is_not_declaring(self, terminal):
        assert isinstance(terminal.loop, xnano.loop.Loop)
        assert isinstance(terminal.output, xnano.output.Output)
        assert isinstance(terminal.audio, xnano.audio.AudioDevice)

    def test_machinery_is_not_part_of_the_interface(self, terminal):
        for name in (
            'core',
            'run_soon',
            'render',
            'snapshot',
            'advance',
            'step',
            'frames',
        ):
            assert not hasattr(terminal, name), name

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
        'name', ['axis_expression', 'axis_limits', 'to_rgb', 'find_active', 'Stop']
    )
    def test_machinery_is_not_exported(self, name):
        assert name not in xnano.__all__

    def test_no_module_uses_any(self):
        package = pathlib.Path(xnano.__file__).parent
        offenders = []
        for path in sorted(package.glob('*.py')):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == 'Any':
                    offenders.append(f'{path.name}:{node.lineno}')
                if isinstance(node, ast.alias) and node.name == 'Any':
                    offenders.append(f'{path.name}: imports Any')
        assert offenders == []


class TestInjectedEvents:
    def test_every_kind_of_event_reaches_a_hook_on_the_terminal(self, terminal):
        events = {
            'key': Event.key_press('a'),
            'paste': Event.paste('text'),
            'resize': Event.resize(width=30, height=8),
            'focus_gained': Event.focus_gained(),
            'focus_lost': Event.focus_lost(),
            'custom': Event.custom('volume_changed', data='7'),
        }
        heard: list[str] = []

        @terminal.hook
        def listen(context: xnano.context.Context) -> None:
            assert context.event is not None
            heard.append(context.event.kind)

        for event in events.values():
            terminal.inject(event)
        terminal.loop.advance(0.05)
        assert sorted(heard) == sorted(events)

    def test_a_custom_event_carries_a_name_and_data(self, terminal):
        seen: list[tuple[str | None, str | None]] = []

        @terminal.hook(when=lambda context: context.event.kind == 'custom')
        def volume(context: xnano.context.Context) -> None:
            seen.append((context.event.custom_name, context.event.custom_data))

        terminal.inject(Event.custom('volume_changed', data='7'))
        terminal.loop.advance(0.05)
        assert seen == [('volume_changed', '7')]

    def test_injecting_into_a_closed_terminal_says_so(self):
        with xnano.iter(offscreen=True, width=4, height=1) as terminal:
            pass
        with pytest.raises(xnano.errors.TerminalClosedError):
            terminal.inject(Event.wake())


@dataclasses.dataclass
class Settings:
    volume: int = 40
    muted: bool = False


class TestTypedState:
    def test_the_state_is_the_dataclass_that_was_given(self):
        with xnano.iter(offscreen=True, width=8, height=1, state=Settings()) as terminal:
            assert terminal.state.volume == 40
            terminal.state.volume = 55
            assert terminal.state.volume == 55

    def test_a_value_of_the_wrong_type_is_refused(self):
        with xnano.iter(offscreen=True, width=8, height=1, state=Settings()) as terminal:
            with pytest.raises(xnano.errors.TerminalError, match='volume'):
                terminal.state.volume = 'loud'  # type: ignore[assignment]

    def test_a_reference_drives_an_axis(self):
        with xnano.iter(offscreen=True, width=30, height=2, state=Settings()) as terminal:
            thumb = terminal.write('#')
            thumb.x = terminal.ref(lambda state: state.volume)
            terminal.state.volume = 12
            terminal.loop.advance(0.05)
            assert thumb.x == 12

    def test_a_terminal_without_state_says_how_to_add_it(self, terminal):
        with pytest.raises(xnano.errors.TerminalError, match=r'iter\(state='):
            _ = terminal.state

    def test_the_context_carries_the_same_state(self):
        with xnano.iter(offscreen=True, width=8, height=1, state=Settings()) as terminal:
            seen: list[int] = []

            @terminal.hook(when=lambda context: context.keyboard is not None)
            def press(context: xnano.context.Context[Settings]) -> None:
                context.state.volume += 5
                seen.append(context.state.volume)

            terminal.inject(Event.key_press('up'))
            terminal.loop.advance(0.05)
            assert seen == [45]
            assert terminal.state.volume == 45
            assert typing.get_type_hints(Settings)['volume'] is int


class TestOutputCapture:
    def test_a_live_terminal_that_cannot_hold_output_back_warns(self):
        from xnano.terminal import warn_if_output_is_not_held_back

        with pytest.warns(RuntimeWarning, match='capture=False'):
            warn_if_output_is_not_held_back(requested=True, is_held_back=False)

    @pytest.mark.parametrize(
        ('requested', 'is_held_back'), [(True, True), (False, False)]
    )
    def test_nothing_is_said_when_it_was_not_needed_or_it_worked(
        self, requested, is_held_back
    ):
        import warnings

        from xnano.terminal import warn_if_output_is_not_held_back

        with warnings.catch_warnings():
            warnings.simplefilter('error')
            warn_if_output_is_not_held_back(
                requested=requested, is_held_back=is_held_back
            )

    def test_an_offscreen_terminal_never_warns(self):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter('error')
            with xnano.iter(offscreen=True, width=4, height=1):
                pass


class TestDocumentation:
    PACKAGE = pathlib.Path(xnano.__file__).parent

    def test_every_public_attribute_has_inline_documentation(self):
        repository = self.PACKAGE.parent
        paths = [
            path for path in self.PACKAGE.glob('*.py') if not path.name.startswith('_')
        ]
        paths.append(self.PACKAGE / '_hooks.py')
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
        for path in sorted(self.PACKAGE.glob('*.py')):
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
        for path in sorted(self.PACKAGE.glob('*.py')):
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
            for path in sorted(self.PACKAGE.glob('*.py'))
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
        for path in sorted(self.PACKAGE.glob('*.py')):
            expected = 'xnano' if path.stem == '__init__' else f'xnano.{path.stem}'
            docstring = (
                ast.get_docstring(ast.parse(path.read_text(encoding='utf-8'))) or ''
            )
            if docstring.splitlines()[0:1] != [expected]:
                wrong.append(path.name)
        assert wrong == []

    def test_every_example_file_uses_public_imports_only(self):
        examples = pathlib.Path(xnano.__file__).parent.parent / 'examples'
        private = [
            path.name
            for path in examples.glob('*.py')
            if '_xnano_core' in path.read_text(encoding='utf-8')
            or '._' in path.read_text(encoding='utf-8')
        ]
        assert private == []


class TestOutputCaptureStatus:
    def test_an_offscreen_terminal_holds_nothing_back(self):
        with xnano.iter(offscreen=True, width=4, height=1) as terminal:
            assert terminal.output.is_captured is False
