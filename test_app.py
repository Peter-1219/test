import os
import tempfile
import unittest
from unittest import mock

import app


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        app.DB_PATH = app.Path(self.tmp_dir.name) / "memory.db"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_history_is_scoped_and_ordered(self):
        app.save("a", "user", "第一句")
        app.save("b", "user", "別人的話")
        app.save("a", "assistant", "第二句")
        self.assertEqual([m["content"] for m in app.history("a")], ["第一句", "第二句"])

    def test_missing_key_returns_setup_message(self):
        old = os.environ.pop("OPENAI_API_KEY", None)
        try:
            result = app.generate([])
            self.assertIn("OPENAI_API_KEY", result["reply"])
            self.assertEqual(len(result["suggestions"]), 3)
        finally:
            if old: os.environ["OPENAI_API_KEY"] = old

    def test_profile_is_detailed_and_persisted(self):
        answers = {
            "energy": "獨處充電", "decision": "兩者平衡",
            "stress": "找人聊聊", "comfort": "先聽我說",
            "conflict": "冷靜後再談", "structure": "大方向即可",
            "sensitivity": "很容易察覺", "expression": "確認安全才說",
        }
        analysis = app.save_profile("person-a", answers)
        profile = app.get_profile("person-a")
        self.assertEqual(profile["answers"], answers)
        self.assertEqual(profile["analysis"], analysis)
        self.assertIn("情緒感受度", analysis)
        self.assertIn("非心理診斷", analysis)

    def test_default_data_directory_is_platform_specific(self):
        with mock.patch("app.platform.system", return_value="Windows"), mock.patch.dict(os.environ, {"APPDATA": "/user/appdata"}):
            self.assertEqual(app.default_data_dir(), app.Path("/user/appdata/WarmCompanion"))
        with mock.patch("app.platform.system", return_value="Linux"), mock.patch.dict(os.environ, {"XDG_DATA_HOME": "/user/data"}):
            self.assertEqual(app.default_data_dir(), app.Path("/user/data/WarmCompanion"))


if __name__ == "__main__": unittest.main()
