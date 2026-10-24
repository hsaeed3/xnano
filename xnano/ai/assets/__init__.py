"""
xnano.ai.assets

Libraries of examples that the task models can use, which you install when you want them.

Every model works without them, from the few examples built into xnano. An installed library
gives a model many more to choose from, and it shows the model the ones closest to each
request: [`ArtModel`][xnano.ai.models.art.ArtModel] reads ``'art-references'``,
[`ComponentModel`][xnano.ai.models.components.ComponentModel] reads ``'component-examples'`` and
[`MusicModel`][xnano.ai.models.music.MusicModel] reads ``'melodies'``.

Install one from the command line, the way spaCy downloads a language model:

```bash
python -m xnano.ai.assets install art-references
```

or from Python with [`install`][xnano.ai.assets.install]. ``python -m xnano.ai.assets list``
shows each library and whether it is installed. A library is saved under
[`directory`][xnano.ai.assets.directory], the user data directory of xnano (or the directory
in ``XNANO_DATA_DIRECTORY`` when it is set), so every program on the computer finds it.

Examples:
    ```python
    from xnano.ai import assets

    assert [asset.name for asset in assets.catalog()] == [
        'art-references',
        'component-examples',
        'melodies',
    ]
    if not assets.is_installed('melodies'):
        print('install it with: python -m xnano.ai.assets install melodies')
    ```
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import pathlib
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from collections.abc import Sequence
from typing import Final, Literal, cast, get_args

from xnano.errors import TerminalError

__all__ = [
    'Asset',
    'AssetName',
    'catalog',
    'directory',
    'install',
    'is_installed',
    'path',
    'remove',
]

AssetName = Literal['art-references', 'component-examples', 'melodies']
"""The name of a library of examples: ``'art-references'``, ``'component-examples'`` or ``'melodies'``."""

_DOWNLOADS: Final = 'https://github.com/hsaeed3/xnano/releases/download'
"""Where the libraries are published, one release per version of the libraries."""

_ENTRIES_FILE: Final = 'entries.jsonl'
"""The file of a library that holds its examples, one JSON object per line."""

_DESCRIPTION_FILE: Final = 'asset.json'
"""The file of a library that names it and gives its version."""


@dataclasses.dataclass(frozen=True, slots=True)
class Asset:
    """
    A library of examples in the catalog: what it is, and the download that installs it.

    Get them from [`catalog`][xnano.ai.assets.catalog]; install one by its ``name``.

    Attributes:
        name: The name to install it by, such as ``'art-references'``.
        description: What it holds and which model reads it.
        version: The version of the library that this xnano reads.
        size_bytes: The size of the download, in bytes.
        sha256: The checksum the download must have.
        url: Where the download is published.
    """

    name: AssetName
    description: str
    version: str
    size_bytes: int
    sha256: str

    @property
    def url(self) -> str:
        """Where the download is published."""
        return f'{_DOWNLOADS}/ai-assets-{self.version}/{self.name}-{self.version}.tar.gz'


_CATALOG: Final[tuple[Asset, ...]] = (
    Asset(
        name='art-references',
        description=(
            'Hand-drawn pixel art at 8, 12 and 16 pixels, written as rows and a palette '
            'with roles, which ArtModel shows as references for the closest subjects.'
        ),
        version='1.0.0',
        size_bytes=2469,
        sha256='3005b31c1d6087135a482b1fd6c84bdc0f1789babd610b4f27184c15bfb96191',
    ),
    Asset(
        name='component-examples',
        description=(
            'Sandbox programs that draw cards, gauges, tables and lists at several sizes, '
            'each with what it draws, which ComponentModel shows as worked examples.'
        ),
        version='1.0.0',
        size_bytes=3665,
        sha256='2ab7fd60f9766570d84fac16276ebd177783b9fcdd73d00844db3b9ea5123da6',
    ),
    Asset(
        name='melodies',
        description=(
            'Short melodies in melody text, described by mood, meter and key, which '
            'MusicModel shows as examples of the grammar and of phrasing.'
        ),
        version='1.0.0',
        size_bytes=1497,
        sha256='0a757d286ca63142f821d44d80674489ba7d647e787aae25a8cb2879f69189a8',
    ),
)


def catalog() -> tuple[Asset, ...]:
    """
    Every library that can be installed, in the order of their names.

    Returns:
        The [`Asset`][xnano.ai.assets.Asset] of each library.
    """
    return _CATALOG


def directory() -> pathlib.Path:
    r"""
    The directory the libraries are installed in.

    It is ``XNANO_DATA_DIRECTORY`` when that is set, and otherwise the user data directory of
    xnano: ``~/Library/Application Support/xnano`` on macOS, ``%LOCALAPPDATA%\\xnano`` on
    Windows, and ``$XDG_DATA_HOME/xnano`` (or ``~/.local/share/xnano``) elsewhere. Each library
    is in ``assets/<name>/<version>`` inside it. The directory is not created until something
    is installed.

    Returns:
        The path of the directory.
    """
    configured = os.environ.get('XNANO_DATA_DIRECTORY')
    if configured:
        return pathlib.Path(configured).expanduser()
    home = pathlib.Path.home()
    if sys.platform == 'darwin':
        return home / 'Library' / 'Application Support' / 'xnano'
    if sys.platform == 'win32':
        local = os.environ.get('LOCALAPPDATA')
        return (pathlib.Path(local) if local else home / 'AppData' / 'Local') / 'xnano'
    data_home = os.environ.get('XDG_DATA_HOME')
    return (pathlib.Path(data_home) if data_home else home / '.local' / 'share') / 'xnano'


def is_installed(name: AssetName) -> bool:
    """
    Whether a library is installed, at the version this xnano reads.

    Args:
        name: The name of the library, such as ``'melodies'``.

    Raises:
        ValueError: No library has that name.
    """
    return (_installed_directory(_asset(name)) / _ENTRIES_FILE).is_file()


def path(name: AssetName) -> pathlib.Path:
    """
    The directory a library is installed in.

    Args:
        name: The name of the library, such as ``'melodies'``.

    Returns:
        The directory, which holds the library's ``entries.jsonl``.

    Raises:
        ValueError: No library has that name.
        TerminalError: The library is not installed. The message says how to install it.
    """
    asset = _asset(name)
    installed = _installed_directory(asset)
    if not (installed / _ENTRIES_FILE).is_file():
        raise TerminalError(
            f'The library {name!r} is not installed. Install it with: python -m '
            f'xnano.ai.assets install {name}, or xnano.ai.assets.install({name!r}).',
            code='ai.asset',
        )
    return installed


def install(
    name: AssetName,
    /,
    *,
    archive: str | os.PathLike[str] | None = None,
    should_replace: bool = False,
) -> pathlib.Path:
    """
    Download a library and install it, so the models that read it find it.

    The download is checked against the checksum in the catalog before anything is
    installed, and an earlier install of the same version is kept unless ``should_replace``
    is true. Pass ``archive`` to install from a copy of the download on this computer
    instead, such as one taken to a machine without a network.

    Args:
        name: The name of the library, such as ``'art-references'``.
        archive: The path of the library's ``.tar.gz`` download, to install without the
            network; ``None`` downloads it.
        should_replace: Whether to install again over a library that is installed.

    Returns:
        The directory the library is installed in.

    Raises:
        ValueError: No library has that name, or the archive is not this library.
        TerminalError: The download failed, or its checksum is not the one in the catalog.
            The message says what to do.
    """
    asset = _asset(name)
    destination = _installed_directory(asset)
    if (destination / _ENTRIES_FILE).is_file() and not should_replace:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as working:
        working_path = pathlib.Path(working)
        downloaded = working_path / 'download.tar.gz'
        if archive is None:
            _download(asset, downloaded)
        else:
            shutil.copyfile(archive, downloaded)
        _check_checksum(asset, downloaded, from_archive=archive is not None)
        unpacked = working_path / 'unpacked'
        _unpack(downloaded, unpacked)
        _check_contents(asset, unpacked)
        if destination.exists():
            shutil.rmtree(destination)
        # Moved in one step, so a program never sees half a library.
        unpacked.rename(destination)
    return destination


def remove(name: AssetName) -> bool:
    """
    Remove an installed library, every version of it.

    Args:
        name: The name of the library, such as ``'melodies'``.

    Returns:
        Whether there was anything to remove.

    Raises:
        ValueError: No library has that name.
    """
    library = directory() / 'assets' / _asset(name).name
    if not library.exists():
        return False
    shutil.rmtree(library)
    return True


# -- reading a library ---------------------------------------------------------------------


def _entries(name: AssetName) -> tuple[dict[str, object], ...]:
    """The examples of an installed library, or none when it is not installed."""
    asset = _asset(name)
    entries_path = _installed_directory(asset) / _ENTRIES_FILE
    key = (str(entries_path), _modified_time(entries_path))
    cached = _read_entries.get(name)
    if cached is not None and cached[0] == key:
        return cached[1]
    if key[1] is None:
        return ()
    with entries_path.open(encoding='utf-8') as file:
        entries = tuple(
            cast('dict[str, object]', json.loads(line)) for line in file if line.strip()
        )
    _read_entries[name] = (key, entries)
    return entries


_read_entries: dict[
    str, tuple[tuple[str, float | None], tuple[dict[str, object], ...]]
] = {}
"""The examples read from each library, with the path and time of the file they came from."""


def _modified_time(file: pathlib.Path) -> float | None:
    try:
        return file.stat().st_mtime
    except OSError:
        return None


def _closest(
    entries: Sequence[dict[str, object]],
    request: str,
    *,
    fields: Sequence[str],
    count: int,
) -> list[dict[str, object]]:
    """The ``count`` entries whose ``fields`` share the most words with ``request``."""
    wanted = _words(request)
    scored: list[tuple[int, int, dict[str, object]]] = []
    for index, entry in enumerate(entries):
        text = ' '.join(_field_text(entry.get(field)) for field in fields)
        scored.append((len(wanted & _words(text)), -index, entry))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [entry for score, _, entry in scored[:count] if score > 0]


def _field_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return ' '.join(str(item) for item in value)
    return ''


def _words(text: str) -> set[str]:
    return {
        word.strip('.,;:!?()[]"\'').lower()
        for word in text.split()
        if len(word.strip('.,;:!?()[]"\'')) > 2
    }


# -- installing ----------------------------------------------------------------------------


def _asset(name: object) -> Asset:
    for asset in _CATALOG:
        if asset.name == name:
            return asset
    names = ', '.join(repr(item) for item in get_args(AssetName))
    raise ValueError(
        f'There is no library called {name!r}. The libraries are {names}; '
        f'python -m xnano.ai.assets list shows them.'
    )


def _installed_directory(asset: Asset) -> pathlib.Path:
    return directory() / 'assets' / asset.name / asset.version


def _download(asset: Asset, target: pathlib.Path) -> None:
    try:
        with (
            urllib.request.urlopen(asset.url, timeout=60) as response,
            target.open('wb') as file,
        ):
            shutil.copyfileobj(response, file)
    except (urllib.error.URLError, OSError) as error:
        raise TerminalError(
            f'The library {asset.name!r} could not be downloaded from {asset.url}: '
            f'{error}. Check the network and try again, or download the file elsewhere and '
            f'install it with install({asset.name!r}, archive=path).',
            code='ai.asset',
        ) from error


def _check_checksum(asset: Asset, archive: pathlib.Path, *, from_archive: bool) -> None:
    digest = hashlib.sha256()
    with archive.open('rb') as file:
        for block in iter(lambda: file.read(1 << 16), b''):
            digest.update(block)
    if digest.hexdigest() != asset.sha256:
        where = 'The archive given' if from_archive else 'The download'
        raise TerminalError(
            f'{where} for {asset.name!r} has the checksum {digest.hexdigest()}, but version '
            f'{asset.version} has {asset.sha256}, so it was not installed. Download '
            f'{asset.url} again; nothing on this computer was changed.',
            code='ai.asset',
        )


def _unpack(archive: pathlib.Path, target: pathlib.Path) -> None:
    target.mkdir()
    with tarfile.open(archive, 'r:gz') as bundle:
        for member in bundle.getmembers():
            inside = (target / member.name).resolve()
            if not inside.is_relative_to(target.resolve()) or not (
                member.isfile() or member.isdir()
            ):
                raise TerminalError(
                    f'The archive holds {member.name!r}, which is not a plain file inside the '
                    f'library, so it was not installed. Download the library again from the '
                    f'catalog.',
                    code='ai.asset',
                )
        if hasattr(tarfile, 'data_filter'):
            bundle.extractall(target, filter='data')
        else:
            # Python 3.11 before 3.11.4 has no filters; every member was checked above.
            bundle.extractall(target)  # noqa: S202


def _check_contents(asset: Asset, unpacked: pathlib.Path) -> None:
    description_path = unpacked / _DESCRIPTION_FILE
    if not description_path.is_file() or not (unpacked / _ENTRIES_FILE).is_file():
        raise ValueError(
            f'This archive is not a library of xnano: it has no {_DESCRIPTION_FILE} and '
            f'{_ENTRIES_FILE}. Install the download of {asset.name!r} from {asset.url}.'
        )
    description = json.loads(description_path.read_text(encoding='utf-8'))
    if (description.get('name'), description.get('version')) != (
        asset.name,
        asset.version,
    ):
        raise ValueError(
            f'This archive is {description.get("name")!r} version '
            f'{description.get("version")!r}, not {asset.name!r} version {asset.version}. '
            f'Install the download of {asset.name!r} from {asset.url}.'
        )


# -- the command line ----------------------------------------------------------------------


def _main(arguments: Sequence[str]) -> int:
    """Run ``python -m xnano.ai.assets``; return the exit status."""
    usage = (
        'Usage: python -m xnano.ai.assets list\n'
        '       python -m xnano.ai.assets install NAME [--archive PATH] [--replace]\n'
        '       python -m xnano.ai.assets remove NAME\n'
        '       python -m xnano.ai.assets path NAME\n'
    )
    if not arguments or arguments[0] in ('-h', '--help'):
        sys.stdout.write(usage)
        return 0 if arguments else 2
    command, *rest = arguments
    try:
        if command == 'list':
            for asset in catalog():
                state = 'installed' if is_installed(asset.name) else 'not installed'
                kilobytes = asset.size_bytes / 1024
                sys.stdout.write(
                    f'{asset.name:<20} {asset.version:<8} {kilobytes:7.1f} KB  {state}\n'
                    f'    {asset.description}\n'
                )
            sys.stdout.write(f'Libraries are installed in {directory() / "assets"}\n')
            return 0
        if command in ('install', 'remove', 'path') and rest:
            name = cast('AssetName', rest[0])
            if command == 'install':
                archive = None
                if '--archive' in rest:
                    position = rest.index('--archive')
                    if position + 1 >= len(rest):
                        sys.stderr.write('--archive needs the path of the download.\n')
                        return 2
                    archive = rest[position + 1]
                installed = install(
                    name, archive=archive, should_replace='--replace' in rest
                )
                sys.stdout.write(f'Installed {name} in {installed}\n')
            elif command == 'remove':
                removed = remove(name)
                sys.stdout.write(
                    f'Removed {name}\n' if removed else f'{name} was not installed\n'
                )
            else:
                sys.stdout.write(f'{path(name)}\n')
            return 0
    except (ValueError, TerminalError) as error:
        sys.stderr.write(f'{error}\n')
        return 1
    sys.stderr.write(usage)
    return 2
