import os
from pathlib import Path
import unittest
from unittest.mock import patch

from config.settings import Settings


class SettingsTests(unittest.TestCase):
    def test_default_project_root_is_repository_projects_directory(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_environment()
        self.assertEqual((Path(__file__).resolve().parents[2] / "projects").resolve(), settings.project_root)

    def test_project_root_override_expands_and_resolves(self) -> None:
        with patch.dict(os.environ, {"PROJECTS_ROOT": "~/../"}, clear=True):
            settings = Settings.from_environment()
        self.assertEqual(Path.home().parent.resolve(), settings.project_root)


if __name__ == "__main__":
    unittest.main()
