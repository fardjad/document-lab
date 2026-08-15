import unittest

from application.project.usecases.import_project import ImportProject
from model.project import ProjectImage


class FakeStore:
    def list_project_ids(self):
        return []

    def create_project(self, project_id, image):
        raise AssertionError("stub must not create")


class ImportProjectTests(unittest.TestCase):
    def test_stub_rejects_every_import(self) -> None:
        with self.assertRaisesRegex(NotImplementedError, "not available"):
            ImportProject(FakeStore(), FakeStore()).import_("anything", ProjectImage(b"png"))

    def test_stub_validates_identifier_first(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid project ID"):
            ImportProject(FakeStore(), FakeStore()).import_("../escape", ProjectImage(b"png"))


if __name__ == "__main__":
    unittest.main()
