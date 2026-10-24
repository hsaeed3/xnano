"""
tests.test_ai_assets

The libraries of examples: the catalog, installing from an archive, reading, removing, and the
command line.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

pytest.importorskip('pydantic_ai')

from xnano.ai import assets  # noqa: E402
from xnano.errors import TerminalError  # noqa: E402

REPOSITORY = Path(__file__).resolve().parent.parent


def archive_of(
    files: dict[str, bytes], *, members: dict[str, bytes] | None = None
) -> bytes:
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w:gz') as bundle:
        for name, content in {**files, **(members or {})}.items():
            information = tarfile.TarInfo(name)
            information.size = len(content)
            bundle.addfile(information, io.BytesIO(content))
    return data.getvalue()


def library_archive(
    name: str = 'melodies', version: str = '1.0.0', entries=None
) -> bytes:
    entries = entries or [
        {'description': 'a cheerful march', 'tags': ['march'], 'text': 'C4 E4 G4:2'},
        {
            'description': 'a sad waltz in a minor key',
            'tags': ['waltz'],
            'text': 'A3 C4 E4',
        },
    ]
    return archive_of(
        {
            'asset.json': json.dumps({'name': name, 'version': version}).encode(),
            'entries.jsonl': ''.join(
                json.dumps(entry) + '\n' for entry in entries
            ).encode(),
        }
    )


@pytest.fixture(autouse=True)
def data_directory(tmp_path, monkeypatch):
    monkeypatch.setenv('XNANO_DATA_DIRECTORY', str(tmp_path / 'data'))
    assets._read_entries.clear()
    return tmp_path / 'data'


@pytest.fixture
def catalog_of(monkeypatch):
    """Point the catalog's melodies at an archive, as a published download would be."""

    def point(data: bytes) -> assets.Asset:
        original = next(asset for asset in assets._CATALOG if asset.name == 'melodies')
        replaced = assets.Asset(
            name='melodies',
            description=original.description,
            version=original.version,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        )
        monkeypatch.setattr(
            assets,
            '_CATALOG',
            tuple(
                replaced if asset.name == 'melodies' else asset
                for asset in assets._CATALOG
            ),
        )
        return replaced

    return point


class TestCatalog:
    def test_every_library_has_a_name_a_version_and_a_download(self):
        names = [asset.name for asset in assets.catalog()]
        assert names == ['art-references', 'component-examples', 'melodies']
        for asset in assets.catalog():
            assert asset.url.endswith(
                f'/ai-assets-{asset.version}/{asset.name}-{asset.version}.tar.gz'
            )
            assert len(asset.sha256) == 64

    def test_the_directory_follows_the_environment(self, data_directory):
        assert assets.directory() == data_directory

    def test_an_unknown_name_lists_the_libraries(self):
        with pytest.raises(
            ValueError, match="'art-references', 'component-examples', 'melodies'"
        ):
            assets.is_installed('pictures')  # type: ignore[arg-type]

    def test_the_catalog_matches_the_archives_built_from_the_sources(
        self, tmp_path, monkeypatch
    ):
        pytest.importorskip('pydantic_monty')
        pytest.importorskip('xnano_audio')
        sys.path.insert(0, str(REPOSITORY / 'scripts'))
        try:
            import build_ai_assets
        finally:
            sys.path.remove(str(REPOSITORY / 'scripts'))
        monkeypatch.setattr(build_ai_assets, 'OUTPUT', tmp_path)
        for asset in assets.catalog():
            _, size, checksum = build_ai_assets.build(asset.name, asset.version)
            assert (size, checksum) == (asset.size_bytes, asset.sha256), (
                f'{asset.name} changed: run uv run python scripts/build_ai_assets.py --update'
            )


class TestWithoutALibrary:
    def test_it_is_not_installed_and_reads_as_empty(self):
        assert not assets.is_installed('melodies')
        assert assets._entries('melodies') == ()

    def test_its_path_says_how_to_install_it(self):
        with pytest.raises(
            TerminalError, match='python -m xnano.ai.assets install melodies'
        ) as caught:
            assets.path('melodies')
        assert caught.value.code == 'ai.asset'

    def test_removing_it_does_nothing(self):
        assert assets.remove('melodies') is False


class TestInstalling:
    def test_an_archive_installs_and_its_entries_are_read(
        self, tmp_path, catalog_of, data_directory
    ):
        data = library_archive()
        catalog_of(data)
        archive = tmp_path / 'melodies.tar.gz'
        archive.write_bytes(data)
        installed = assets.install('melodies', archive=archive)
        assert installed == data_directory / 'assets' / 'melodies' / '1.0.0'
        assert assets.is_installed('melodies')
        assert assets.path('melodies') == installed
        entries = assets._entries('melodies')
        assert [entry['text'] for entry in entries] == ['C4 E4 G4:2', 'A3 C4 E4']
        assert assets._entries('melodies') is entries

    def test_the_closest_entries_share_words_with_the_request(self, tmp_path, catalog_of):
        data = library_archive()
        catalog_of(data)
        (tmp_path / 'melodies.tar.gz').write_bytes(data)
        assets.install('melodies', archive=tmp_path / 'melodies.tar.gz')
        closest = assets._closest(
            assets._entries('melodies'),
            'a slow sad waltz',
            fields=('description', 'tags'),
            count=2,
        )
        assert [entry['text'] for entry in closest] == ['A3 C4 E4']

    def test_an_installed_library_is_kept_unless_it_is_replaced(
        self, tmp_path, catalog_of
    ):
        data = library_archive()
        catalog_of(data)
        archive = tmp_path / 'melodies.tar.gz'
        archive.write_bytes(data)
        installed = assets.install('melodies', archive=archive)
        (installed / 'entries.jsonl').write_text('{"text": "edited"}\n')
        assets.install('melodies', archive=archive)
        assert (installed / 'entries.jsonl').read_text() == '{"text": "edited"}\n'
        assets.install('melodies', archive=archive, should_replace=True)
        assert 'C4 E4 G4:2' in (installed / 'entries.jsonl').read_text()

    def test_a_wrong_checksum_installs_nothing(self, tmp_path, catalog_of):
        catalog_of(library_archive())
        archive = tmp_path / 'other.tar.gz'
        archive.write_bytes(library_archive(entries=[{'text': 'D4'}]))
        with pytest.raises(TerminalError, match='checksum') as caught:
            assets.install('melodies', archive=archive)
        assert caught.value.code == 'ai.asset'
        assert not assets.is_installed('melodies')

    def test_an_archive_of_another_library_is_refused(self, tmp_path, catalog_of):
        data = library_archive(name='art-references')
        catalog_of(data)
        (tmp_path / 'art.tar.gz').write_bytes(data)
        with pytest.raises(ValueError, match="is 'art-references' version"):
            assets.install('melodies', archive=tmp_path / 'art.tar.gz')
        assert not assets.is_installed('melodies')

    def test_a_member_outside_the_library_is_refused(self, tmp_path, catalog_of):
        data = archive_of(
            {'asset.json': b'{}', 'entries.jsonl': b''}, members={'../escaped.txt': b'no'}
        )
        catalog_of(data)
        (tmp_path / 'bad.tar.gz').write_bytes(data)
        with pytest.raises(TerminalError, match='not a plain file inside the library'):
            assets.install('melodies', archive=tmp_path / 'bad.tar.gz')
        assert not (tmp_path / 'data' / 'assets' / 'escaped.txt').exists()

    def test_removing_takes_every_version_away(self, tmp_path, catalog_of):
        data = library_archive()
        catalog_of(data)
        (tmp_path / 'melodies.tar.gz').write_bytes(data)
        assets.install('melodies', archive=tmp_path / 'melodies.tar.gz')
        assert assets.remove('melodies') is True
        assert not assets.is_installed('melodies')
        assert assets._entries('melodies') == ()


class TestCommandLine:
    def test_list_shows_each_library_and_where_they_go(self, capsys, data_directory):
        assert assets._main(['list']) == 0
        output = capsys.readouterr().out
        assert 'art-references' in output and 'not installed' in output
        assert str(data_directory / 'assets') in output

    def test_install_from_an_archive_and_path(self, tmp_path, capsys, catalog_of):
        data = library_archive()
        catalog_of(data)
        (tmp_path / 'melodies.tar.gz').write_bytes(data)
        assert (
            assets._main(
                ['install', 'melodies', '--archive', str(tmp_path / 'melodies.tar.gz')]
            )
            == 0
        )
        assert 'Installed melodies' in capsys.readouterr().out
        assert assets._main(['path', 'melodies']) == 0
        installed = Path(capsys.readouterr().out.strip())
        assert installed.parts[-2:] == ('melodies', '1.0.0')

    def test_a_problem_is_reported_without_a_trace(self, capsys):
        assert assets._main(['path', 'melodies']) == 1
        assert 'is not installed' in capsys.readouterr().err
        assert assets._main(['frobnicate']) == 2
