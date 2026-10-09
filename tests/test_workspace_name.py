"""Custom workspace names survive existing databases and full learning backups."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from server.store import Store


PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"


class WorkspaceNameTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="workspace-name-test-")
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "progress.db"
        self.store = Store(self.path, range(1, 101))

    def rename(self, name):
        return self.store.action({"type": "settings", "settings": {"workspaceName": name}})

    def test_default_and_trimmed_unicode_name_persist_without_changing_other_settings(self):
        self.assertEqual(self.store.read()["settings"]["workspaceName"], "我的工作空间")
        original = self.store.action({"type": "settings", "settings": {"avatar": PNG, "language": "cpp"}})
        original = self.store.action({"type": "note", "problemId": 1, "text": "保留旧笔记"})
        updated = self.rename("  咕咕 🐧 的 C++ 学习空间  ")
        expected = copy.deepcopy(original)
        expected["settings"]["workspaceName"] = "咕咕 🐧 的 C++ 学习空间"
        self.assertEqual(updated, expected)
        self.assertEqual(Store(self.path, range(1, 101)).read(), expected)
        updated = self.store.action({"type": "settings", "settings": {"theme": "dark"}})
        self.assertEqual(updated["settings"]["workspaceName"], "咕咕 🐧 的 C++ 学习空间")
        self.assertEqual(updated["settings"]["avatar"], PNG)

    def test_length_counts_unicode_codepoints_instead_of_utf16_units(self):
        self.assertEqual(self.rename("🐧" * 40)["settings"]["workspaceName"], "🐧" * 40)
        with self.assertRaises(ValueError):
            self.rename("🐧" * 41)
        self.assertEqual(self.store.read()["settings"]["workspaceName"], "🐧" * 40)

    def test_invalid_names_do_not_change_state(self):
        original = self.rename("企鹅的学习空间")
        invalid = (None, True, 7, [], {}, "", " \u3000 ", "a" * 41,
                   "\n企鹅", "企鹅\n", "企\t鹅", "企\r鹅", "企\0鹅",
                   "企\x7f鹅", "企\x85鹅", "企\u2028鹅", "企\u2029鹅", "企\ud800鹅")
        for name in invalid:
            with self.subTest(name=repr(name)), self.assertRaises(ValueError):
                self.rename(name)
            self.assertEqual(self.store.read(), original)

    def test_v2_database_adds_default_without_losing_avatar_or_notes(self):
        original = self.store.action({"type": "settings", "settings": {"avatar": PNG}})
        original = self.store.action({"type": "note", "problemId": 1, "text": "原笔记"})
        original["settings"].pop("workspaceName")
        with self.store.connect() as db:
            db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(original),))
        expected = copy.deepcopy(original)
        expected["settings"]["workspaceName"] = "我的工作空间"
        self.assertEqual(Store(self.path, range(1, 101)).read(), expected)
        self.assertEqual(Store(self.path, range(1, 101)).read(), expected)

    def test_v1_migration_preserves_original_backup_and_defaults_name(self):
        original = self.store.read()
        original["version"] = 1
        original["settings"].pop("workspaceName")
        original["notes"]["1"] = "旧版学习笔记"
        with self.store.connect() as db:
            db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(original),))
        upgraded = Store(self.path, range(1, 101)).read()
        self.assertEqual(upgraded["settings"]["workspaceName"], "我的工作空间")
        self.assertEqual(upgraded["notes"], original["notes"])
        backups = list(self.path.parent.glob("before-v2-upgrade-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text(encoding="utf-8")), original)

    def test_older_v1_and_v2_backup_imports_default_name(self):
        for version in (1, 2):
            with self.subTest(version=version):
                old = self.store.read()
                old["version"] = version
                old["settings"].pop("workspaceName")
                old["notes"]["1"] = "可恢复的旧笔记"
                self.rename("目前的自定义名称")
                restored = self.store.action({"type": "import", "state": old})
                self.assertEqual(restored["settings"]["workspaceName"], "我的工作空间")
                self.assertEqual(restored["notes"], old["notes"])

    def test_full_backup_roundtrip_keeps_name_and_rejects_invalid_name_atomically(self):
        original = self.rename("企鹅的知识小屋")
        changed = self.rename("另一个名称")
        restored = self.store.action({"type": "import", "state": original})
        self.assertEqual(restored, original)
        backups = list(self.path.parent.glob("before-import-*.json"))
        self.assertEqual(json.loads(backups[0].read_text(encoding="utf-8")), changed)
        invalid = copy.deepcopy(changed)
        invalid["settings"]["workspaceName"] = " "
        with self.assertRaises(ValueError):
            self.store.action({"type": "import", "state": invalid})
        self.assertEqual(self.store.read(), original)


if __name__ == "__main__":
    unittest.main()
