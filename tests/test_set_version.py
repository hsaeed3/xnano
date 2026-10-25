"""
tests.test_set_version

The version script keeps the install pins of the current major version in step with the
Cargo manifests, and leaves the pins of older major versions alone.
"""

from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys
from collections.abc import Iterator
from types import ModuleType

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / 'scripts' / 'set_version.py'


@pytest.fixture
def script() -> Iterator[ModuleType]:
    specification = importlib.util.spec_from_file_location('set_version_script', SCRIPT)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    yield module
    del sys.modules[specification.name]


@pytest.fixture
def documents(
    script: ModuleType, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """A temporary README and docs directory that the script treats as the repository."""
    docs = tmp_path / 'docs'
    (docs / 'v1').mkdir(parents=True)
    monkeypatch.setattr(script, 'ROOT', tmp_path)
    monkeypatch.setattr(script, 'DOCS_DIR', docs)
    monkeypatch.setattr(script, 'LEGACY_DOCS_DIR', docs / 'v1')
    return tmp_path


def test_a_pin_with_an_upper_bound_is_left_alone(script, documents):
    readme = documents / 'README.md'
    readme.write_text('pip install "xnano>=1.2.3,<2"\n', encoding='utf-8')
    assert script.synchronize_markdown_pins('2.0.0-beta.4', check=False) == []
    assert readme.read_text(encoding='utf-8') == 'pip install "xnano>=1.2.3,<2"\n'
    assert script.synchronize_markdown_pins('2.0.0-beta.4', check=True) == []


def test_the_legacy_documentation_is_left_alone(script, documents):
    page = documents / 'docs' / 'v1' / 'index.md'
    page.write_text('pip install "xnano>=1.0.0"\n', encoding='utf-8')
    assert script.markdown_pin_paths() == []
    assert script.synchronize_markdown_pins('2.0.0-beta.4', check=False) == []
    assert page.read_text(encoding='utf-8') == 'pip install "xnano>=1.0.0"\n'


def test_a_pin_of_the_current_version_is_updated(script, documents):
    page = documents / 'docs' / 'index.md'
    page.write_text('pip install "xnano>=2.0.0b3"\n', encoding='utf-8')
    with pytest.raises(script.VersionError, match='outdated xnano install pin'):
        script.synchronize_markdown_pins('2.0.0-beta.4', check=True)
    assert script.synchronize_markdown_pins('2.0.0-beta.4', check=False) == [page]
    assert page.read_text(encoding='utf-8') == 'pip install "xnano>=2.0.0b4"\n'
    assert script.synchronize_markdown_pins('2.0.0-beta.4', check=True) == []


def test_the_prerelease_spelling_follows_python(script):
    assert script.pep440('2.0.0-beta.4') == '2.0.0b4'
    assert script.pin_specifier('2.0.0-beta.4') == '>=2.0.0b4'
    assert script.pin_specifier('0.3.0') == '>=0.3.0,<0.4'


def test_a_core_fix_does_not_bump_xnano(script, tmp_path, monkeypatch):
    repository = SCRIPT.parent.parent
    manifests = {}
    for name, manifest in script.CRATES.items():
        copy = tmp_path / manifest.relative_to(repository)
        copy.parent.mkdir(parents=True)
        copy.write_text(manifest.read_text(encoding='utf-8'), encoding='utf-8')
        manifests[name] = copy
    for name in ('Cargo.toml', 'pyproject.toml'):
        (tmp_path / name).write_text(
            (repository / name).read_text(encoding='utf-8'), encoding='utf-8'
        )
    monkeypatch.setattr(script, 'ROOT', tmp_path)
    monkeypatch.setattr(script, 'WORKSPACE_MANIFEST', tmp_path / 'Cargo.toml')
    monkeypatch.setattr(script, 'ROOT_PYPROJECT', tmp_path / 'pyproject.toml')
    monkeypatch.setattr(script, 'CRATES', manifests)
    xnano_version = script.read_version(tmp_path / 'Cargo.toml', 'xnano')

    script.bump('xnano-core', '9.9.9', update_locks=False)

    assert script.read_version(manifests['xnano-core'], 'xnano-core') == '9.9.9'
    assert script.read_version(tmp_path / 'Cargo.toml', 'xnano') == xnano_version
    pyproject = (tmp_path / 'pyproject.toml').read_text(encoding='utf-8')
    assert f"version = '{script.pep440(xnano_version)}'" in pyproject
    assert '"xnano-core>=9.9.9",' in pyproject


def test_the_repository_versions_are_synchronized():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), '--check'],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
