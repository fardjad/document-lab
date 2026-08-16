import unittest

from application.project.usecases.rename_project import RenameProject
from model.project import ProjectId, ProjectNotFound


class FakeStore:
    def __init__(self) -> None:
        self.ids = [ProjectId("scan")]
        self.renamed = []

    def list_project_ids(self):
        return self.ids

    def rename_project(self, project_id, name):
        self.renamed.append((project_id, name))


class RenameProjectTests(unittest.TestCase):
    def test_trims_and_persists_name(self) -> None:
        store = FakeStore()
        self.assertEqual("My scan", RenameProject(store, store).rename("scan", " My scan "))
        self.assertEqual([(ProjectId("scan"), "My scan")], store.renamed)

    def test_rejects_invalid_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "^Invalid project name$"):
            RenameProject(FakeStore(), FakeStore()).rename("scan", "\n")

    def test_rejects_missing_project(self) -> None:
        with self.assertRaises(ProjectNotFound):
            RenameProject(FakeStore(), FakeStore()).rename("missing", "Name")


if __name__ == "__main__":
    unittest.main()
