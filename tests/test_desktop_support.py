"""Desktop migrations preserve existing progress and correctly snapshot live SQLite data."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import copy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import desktop_support
from server.store import DEFAULT_STATE


class DesktopSupportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='coderecall-desktop-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.target = self.root / 'user-data' / 'coderecall.db'

    def make_database(self, name='legacy.db', state=None):
        source = self.root / name
        connection = sqlite3.connect(source)
        with connection:
            connection.execute('CREATE TABLE state (id INTEGER PRIMARY KEY, data TEXT NOT NULL)')
            connection.execute('INSERT INTO state VALUES (1, ?)', (json.dumps(state if state is not None else DEFAULT_STATE),))
        connection.close()
        return source

    def read_state(self, path):
        connection = sqlite3.connect(path)
        try:
            return json.loads(connection.execute('SELECT data FROM state WHERE id=1').fetchone()[0])
        finally:
            connection.close()

    def test_windows_data_directory_uses_local_app_data(self):
        with patch.object(desktop_support.sys, 'platform', 'win32'), patch.dict(os.environ, {'LOCALAPPDATA': str(self.root)}):
            directory = desktop_support.data_directory()
        self.assertEqual(directory, self.root / 'CodeRecall')
        self.assertTrue(directory.is_dir())

    def test_windows_missing_environment_uses_home_fallback(self):
        with patch.object(desktop_support.sys, 'platform', 'win32'), patch.dict(os.environ, {'LOCALAPPDATA': ''}), patch.object(Path, 'home', return_value=self.root):
            self.assertEqual(desktop_support.data_directory(), self.root / 'AppData' / 'Local' / 'CodeRecall')

    def test_linux_xdg_path_and_relative_path_fallback(self):
        with patch.object(desktop_support.sys, 'platform', 'linux'), patch.object(Path, 'home', return_value=self.root):
            with patch.dict(os.environ, {'XDG_DATA_HOME': str(self.root / 'xdg')}):
                self.assertEqual(desktop_support.data_directory(), self.root / 'xdg' / 'coderecall')
            with patch.dict(os.environ, {'XDG_DATA_HOME': 'relative-is-not-valid'}):
                self.assertEqual(desktop_support.data_directory(), self.root / '.local' / 'share' / 'coderecall')

    def test_macos_directory(self):
        with patch.object(desktop_support.sys, 'platform', 'darwin'), patch.object(Path, 'home', return_value=self.root):
            self.assertEqual(desktop_support.data_directory(), self.root / 'Library' / 'Application Support' / 'CodeRecall')
            self.assertEqual(desktop_support.data_directory('CodeRecall-v2'), self.root / 'Library' / 'Application Support' / 'CodeRecall-v2')

    def test_valid_database_is_copied_and_source_preserved(self):
        state = copy.deepcopy(DEFAULT_STATE)
        state['notes']['1'] = '保留笔记与中文内容'
        state['favorites'] = [1, 146]
        state['drafts']['1:python:leetcode'] = 'class Solution:\n    pass\n'
        source = self.make_database(state=state)
        original_bytes = source.read_bytes()
        result = desktop_support.migrate_legacy_database(self.target, [source])
        self.assertEqual(result, source)
        self.assertEqual(self.read_state(self.target), state)
        self.assertEqual(source.read_bytes(), original_bytes)
        self.assertEqual(list(self.target.parent.iterdir()), [self.target])

    def test_existing_target_never_changes_even_if_invalid(self):
        source = self.make_database()
        self.target.parent.mkdir()
        self.target.write_bytes(b'existing user file must not be overwritten')
        original = self.target.read_bytes()
        self.assertIsNone(desktop_support.migrate_legacy_database(self.target, [source]))
        self.assertEqual(self.target.read_bytes(), original)

    def test_missing_and_unrelated_candidates_are_skipped(self):
        not_sqlite = self.root / 'not-sqlite.db'
        not_sqlite.write_text('unrelated file', encoding='utf-8')
        unrelated = self.make_database('unrelated.db', {'version': 1})
        valid = self.make_database('valid.db')
        result = desktop_support.migrate_legacy_database(self.target, [self.root / 'missing.db', not_sqlite, unrelated, valid])
        self.assertEqual(result, valid)
        self.assertEqual(self.read_state(self.target), DEFAULT_STATE)

    def test_bad_version_or_envelope_is_not_imported(self):
        invalid_states = []
        for version in (True, 3, '1'):
            value = copy.deepcopy(DEFAULT_STATE)
            value['version'] = version
            invalid_states.append(value)
        for key, bad in [('cards', []), ('notes', []), ('events', {}), ('settings', {}), ('favorites', [True])]:
            value = copy.deepcopy(DEFAULT_STATE)
            value[key] = bad
            invalid_states.append(value)
        sources = [self.make_database(f'invalid-{i}.db', state) for i, state in enumerate(invalid_states)]
        self.assertIsNone(desktop_support.migrate_legacy_database(self.target, sources))
        self.assertFalse(self.target.exists())

    def test_view_named_state_is_not_accepted_as_application_table(self):
        source = self.root / 'view.db'
        with closing(sqlite3.connect(source)) as connection, connection:
            connection.execute('CREATE TABLE other (id INTEGER, data TEXT)')
            connection.execute('INSERT INTO other VALUES (1, ?)', (json.dumps(DEFAULT_STATE),))
            connection.execute('CREATE VIEW state AS SELECT * FROM other')
        self.assertIsNone(desktop_support.migrate_legacy_database(self.target, [source]))

    def test_live_wal_data_is_included_without_deleting_source(self):
        source = self.make_database()
        writer = sqlite3.connect(source)
        self.addCleanup(writer.close)
        writer.execute('PRAGMA journal_mode=WAL')
        writer.execute('PRAGMA wal_autocheckpoint=0')
        state = copy.deepcopy(DEFAULT_STATE)
        state['notes']['1'] = 'committed only in the live WAL'
        writer.execute('UPDATE state SET data=? WHERE id=1', (json.dumps(state),))
        writer.commit()
        self.assertTrue(Path(str(source) + '-wal').exists())
        self.assertEqual(desktop_support.migrate_legacy_database(self.target, [source]), source)
        self.assertEqual(self.read_state(self.target), state)
        self.assertEqual(self.read_state(source), state)
        self.assertFalse(Path(str(self.target) + '-wal').exists())

    def test_competing_creator_keeps_its_progress(self):
        source = self.make_database()
        original_publish = desktop_support._publish_without_overwrite
        winner = copy.deepcopy(DEFAULT_STATE)
        winner['notes']['1'] = 'new desktop progress wins'

        def publish_after_other_instance(temporary, target):
            with closing(sqlite3.connect(target)) as connection, connection:
                connection.execute('CREATE TABLE state (id INTEGER PRIMARY KEY, data TEXT NOT NULL)')
                connection.execute('INSERT INTO state VALUES (1, ?)', (json.dumps(winner),))
            return original_publish(temporary, target)

        with patch.object(desktop_support, '_publish_without_overwrite', side_effect=publish_after_other_instance):
            self.assertIsNone(desktop_support.migrate_legacy_database(self.target, [source]))
        self.assertEqual(self.read_state(self.target), winner)
        self.assertEqual(list(self.target.parent.iterdir()), [self.target])

    def test_two_simultaneous_migrations_publish_exactly_once(self):
        source = self.make_database()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: desktop_support.migrate_legacy_database(self.target, [source]), range(2)))
        self.assertEqual(sum(result == source for result in results), 1)
        self.assertEqual(self.read_state(self.target), DEFAULT_STATE)
        self.assertEqual(list(self.target.parent.iterdir()), [self.target])

    def test_publish_failure_preserves_source_and_removes_temporary_files(self):
        source = self.make_database()
        before = source.read_bytes()
        with patch.object(desktop_support, '_publish_without_overwrite', side_effect=PermissionError('read-only destination')):
            with self.assertRaises(PermissionError):
                desktop_support.migrate_legacy_database(self.target, [source])
        self.assertFalse(self.target.exists())
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(list(self.target.parent.iterdir()), [])

    def test_idempotent_second_run_does_not_refresh_from_legacy(self):
        source = self.make_database()
        self.assertEqual(desktop_support.migrate_legacy_database(self.target, [source]), source)
        state = copy.deepcopy(DEFAULT_STATE)
        state['notes']['1'] = 'legacy changed after migration'
        with closing(sqlite3.connect(source)) as connection, connection:
            connection.execute('UPDATE state SET data=? WHERE id=1', (json.dumps(state),))
        self.assertIsNone(desktop_support.migrate_legacy_database(self.target, [source]))
        self.assertEqual(self.read_state(self.target), DEFAULT_STATE)


if __name__ == '__main__':
    unittest.main()
