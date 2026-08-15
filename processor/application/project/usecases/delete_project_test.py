import unittest

from application.project.usecases.delete_project import DeleteProject
from model.project import ProjectId, ProjectNotFound


class FakeStore:
    def __init__(self) -> None:
        self.ids = [ProjectId("Alpha")]
        self.deleted: list[ProjectId] = []

    def list_project_ids(self):
        return self.ids

    def delete_project(self, project_id):
        self.deleted.append(project_id)


class DeleteProjectTests(unittest.TestCase):
    def test_deletes_existing_project(self) -> None:
        store = FakeStore()
        DeleteProject(store, store).delete("Alpha")
        self.assertEqual([ProjectId("Alpha")], store.deleted)

    def test_rejects_missing_project(self) -> None:
        with self.assertRaises(ProjectNotFound):
            DeleteProject(FakeStore(), FakeStore()).delete("missing")

    def test_rejects_invalid_project_id(self) -> None:
        with self.assertRaises(ProjectNotFound):
            DeleteProject(FakeStore(), FakeStore()).delete("../escape")


if __name__ == "__main__":
    unittest.main()
