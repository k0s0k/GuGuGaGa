"""Avatar settings persist safely alongside existing study data and backups."""
import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest

from server.store import MAX_AVATAR_BYTES, Store


# One-pixel raster files; fixtures require no imaging dependency at test/runtime.
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
WEBP = "data:image/webp;base64,UklGRjwAAABXRUJQVlA4IDAAAADQAQCdASoBAAEAAUAmJaACdLoB+AADsAD+8ut//NgVzXPv9//S4P0uD9Lg/9KQAAA="
JPEG = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDi6KKK+ZP3E//Z"


class AvatarTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="avatar-test-")
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "progress.db"
        self.store = Store(self.path, range(1, 101))

    def save_avatar(self, avatar):
        return self.store.action({"type": "settings", "settings": {"avatar": avatar}})

    def test_new_user_and_avatar_removal_use_default_avatar(self):
        self.assertEqual(self.store.read()["settings"]["avatar"], "")
        self.save_avatar(PNG)
        self.assertEqual(self.save_avatar("")["settings"]["avatar"], "")

    def test_rasters_persist_and_other_settings_do_not_clear_avatar(self):
        for avatar in (PNG, JPEG, WEBP):
            with self.subTest(mime=avatar.split(";")[0]):
                self.save_avatar(avatar)
                changed = self.store.action({"type": "settings", "settings": {"theme": "dark"}})
                self.assertEqual(changed["settings"]["avatar"], avatar)
                self.assertEqual(Store(self.path, range(1, 101)).read(), changed)

    def test_invalid_avatar_is_rejected_without_changing_state(self):
        original = self.save_avatar(PNG)
        invalid = (None, True, {}, "https://example.com/avatar.png", "data:image/png;base64,",
                   "data:image/svg+xml;base64,PHN2Zy8+", "data:image/png;base64,%%%",
                   PNG.replace("image/png", "image/jpeg"), PNG + "\n", WEBP[:-2] + "B=",
                   "data:image/png;base64," + base64.b64encode(b"<svg></svg>").decode("ascii"),
                   "data:image/webp;base64," + base64.b64encode(b"RIFF\x00\x00\x00\x00WEBPVP8 ").decode("ascii"))
        for avatar in invalid:
            with self.subTest(avatar=str(avatar)[:50]), self.assertRaises(ValueError):
                self.save_avatar(avatar)
        self.assertEqual(self.store.read(), original)

    def test_oversized_avatar_is_rejected_without_changing_state(self):
        original = self.save_avatar(PNG)
        oversized = "data:image/png;base64," + base64.b64encode(b"x" * (MAX_AVATAR_BYTES + 1)).decode("ascii")
        with self.assertRaisesRegex(ValueError, "256 KB"):
            self.save_avatar(oversized)
        self.assertEqual(self.store.read(), original)

    def test_old_v2_database_gets_avatar_without_losing_existing_fields(self):
        existing = self.store.action({"type": "note", "problemId": 1, "text": "保留旧笔记"})
        existing["settings"].pop("avatar")
        existing["settings"]["includeHot100"] = False
        with self.store.connect() as db:
            db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(existing),))
        expected = copy.deepcopy(existing)
        expected["settings"]["avatar"] = ""
        upgraded = Store(self.path, range(1, 101)).read()
        self.assertEqual(upgraded, expected)
        self.assertEqual(self.store.validate_import(existing), expected)
        self.assertEqual(Store(self.path, range(1, 101)).read(), expected)

    def test_v1_backup_import_defaults_avatar_without_losing_notes(self):
        old = self.store.read()
        old["version"] = 1
        old["settings"].pop("avatar")
        old["notes"]["1"] = "原来的学习内容"
        imported = self.store.action({"type": "import", "state": old})
        self.assertEqual(imported["settings"]["avatar"], "")
        self.assertEqual(imported["notes"], old["notes"])

    def test_full_backup_roundtrip_retains_avatar_and_rejects_invalid_avatar(self):
        original = self.save_avatar(PNG)
        incoming = self.save_avatar(WEBP)
        self.store.action({"type": "import", "state": original})
        backups = list(self.path.parent.glob("before-import-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text(encoding="utf-8")), incoming)
        self.assertEqual(self.store.read(), original)
        invalid = copy.deepcopy(incoming)
        invalid["settings"]["avatar"] = "javascript:alert(1)"
        with self.assertRaises(ValueError):
            self.store.action({"type": "import", "state": invalid})
        self.assertEqual(self.store.read(), original)
        restored = self.store.action({"type": "import", "state": incoming})
        self.assertEqual(restored, incoming)


if __name__ == "__main__":
    unittest.main()
