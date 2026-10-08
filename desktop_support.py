"""User data paths and non-destructive migration for the desktop launcher."""
from contextlib import closing
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time


def data_directory() -> Path:
    """Return an existing per-user data directory, independent of the EXE location."""
    if sys.platform == 'win32':
        configured = os.environ.get('LOCALAPPDATA', '').strip()
        base = Path(configured) if configured and Path(configured).is_absolute() else Path.home() / 'AppData' / 'Local'
        directory = base / 'CodeRecall'
    elif sys.platform == 'darwin':
        directory = Path.home() / 'Library' / 'Application Support' / 'CodeRecall'
    else:
        configured = os.environ.get('XDG_DATA_HOME', '').strip()
        base = Path(configured) if configured and Path(configured).is_absolute() else Path.home() / '.local' / 'share'
        directory = base / 'coderecall'
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _reject_json_constant(value):
    raise ValueError(f'Non-finite JSON constant: {value}')


def _is_state(value) -> bool:
    """Recognize the complete version-1 state envelope, not just a version flag."""
    if not isinstance(value, dict) or type(value.get('version')) is not int or value['version'] != 1:
        return False
    for key in ('settings', 'cards', 'notes', 'drafts'):
        if not isinstance(value.get(key), dict):
            return False
    for key in ('favorites', 'events', 'checkins'):
        if not isinstance(value.get(key), list):
            return False
    settings = value['settings']
    if (type(settings.get('dailyGoal')) is not int or not 1 <= settings['dailyGoal'] <= 30
            or type(settings.get('newPerDay')) is not int or not 1 <= settings['newPerDay'] <= 10
            or settings.get('language') not in ('python', 'cpp')
            or settings.get('mode') not in ('leetcode', 'acm')
            or settings.get('theme') not in ('light', 'dark')
            or type(settings.get('retention')) not in (int, float)
            or not math.isfinite(settings['retention']) or not 0.8 <= settings['retention'] <= 0.95):
        return False
    if not all(isinstance(item, dict) for item in value['cards'].values()):
        return False
    if not all(isinstance(item, str) for item in value['notes'].values()):
        return False
    if not all(isinstance(item, str) for item in value['drafts'].values()):
        return False
    if not all(type(item) is int and item > 0 for item in value['favorites']):
        return False
    if not all(isinstance(item, dict) for item in value['events']):
        return False
    return all(isinstance(item, str) for item in value['checkins'])


def _is_database(connection: sqlite3.Connection) -> bool:
    try:
        table = connection.execute("SELECT type FROM sqlite_master WHERE name='state'").fetchone()
        if table != ('table',):
            return False
        columns = {column[1]: column for column in connection.execute('PRAGMA table_info(state)')}
        if set(columns) != {'id', 'data'}:
            return False
        if columns['id'][2].upper() != 'INTEGER' or columns['id'][5] != 1:
            return False
        if columns['data'][2].upper() != 'TEXT' or columns['data'][3] != 1:
            return False
        rows = connection.execute('SELECT id, data FROM state LIMIT 2').fetchall()
        if len(rows) != 1 or rows[0][0] != 1 or not isinstance(rows[0][1], str):
            return False
        return _is_state(json.loads(rows[0][1], parse_constant=_reject_json_constant))
    except (sqlite3.DatabaseError, ValueError, TypeError, OverflowError):
        return False


def _publish_without_overwrite(temporary: Path, target: Path) -> bool:
    """Atomically publish the complete file; an existing target always wins."""
    try:
        if os.name == 'nt':
            # Windows rename fails if the destination exists; os.replace would overwrite it.
            os.rename(temporary, target)
        else:
            # POSIX rename replaces its destination, so publish an exclusive hard link instead.
            os.link(temporary, target)
        return True
    except FileExistsError:
        return False


def migrate_legacy_database(target_db: Path, candidates: list[Path]) -> Path | None:
    """Copy the first recognized candidate using SQLite's consistent online backup.

    Return its absolute source path on success. An existing target (including a
    concurrent creator) or no recognized source returns None. Never remove a
    source or replace current progress. Destination I/O/backup errors propagate
    so the caller can report them instead of silently starting with empty data.
    Only the explicitly supplied candidates are examined; no directory scan runs.
    """
    target = Path(os.path.abspath(os.fspath(target_db)))
    if os.path.lexists(target):
        return None
    for candidate in candidates:
        source = Path(os.path.abspath(os.fspath(candidate)))
        if not source.is_file():
            continue
        try:
            source_db = sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True, timeout=1)
        except (sqlite3.DatabaseError, OSError):
            continue
        with closing(source_db):
            if not _is_database(source_db):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            descriptor, filename = tempfile.mkstemp(prefix=f'.{target.name}.migrate-', suffix='.tmp', dir=target.parent)
            os.close(descriptor)
            temporary = Path(filename)
            try:
                deadline = time.monotonic() + 10

                def check_timeout(status, remaining, total):
                    if time.monotonic() > deadline:
                        raise TimeoutError('The previous progress database is busy; close the previous app and retry.')

                with closing(sqlite3.connect(temporary)) as destination:
                    # Unlike a file copy, this includes committed data still present in a WAL.
                    source_db.backup(destination, pages=128, progress=check_timeout, sleep=0.01)
                    if not _is_database(destination):
                        continue
                    if destination.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                        continue
                    # Publish one self-contained database, never a DB depending on temporary WAL files.
                    destination.execute('PRAGMA journal_mode=DELETE')
                    destination.commit()
                with temporary.open('r+b') as stream:
                    os.fsync(stream.fileno())
                if _publish_without_overwrite(temporary, target):
                    return source
                return None
            finally:
                # Only migration-owned temporary files are removed; both user databases remain intact.
                for suffix in ('', '-journal', '-wal', '-shm'):
                    Path(str(temporary) + suffix).unlink(missing_ok=True)
    return None
