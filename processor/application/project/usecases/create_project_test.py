import unittest

from application.project.usecases.create_project import CreateProject
from model.project import ProjectId, ProjectImage


class FakeStore:
    def __init__(self) -> None:
        self.ids = [ProjectId("zebra")]
        self.created: list[ProjectId] = []

    def list_project_ids(self):
        return self.ids

    def create_project(self, project_id, image):
        self.created.append(project_id)


class CreateProjectTests(unittest.TestCase):
    def test_creates_project(self) -> None:
        store = FakeStore()
        self.assertEqual("fresh", str(CreateProject(store, store).create("fresh", ProjectImage(b"png"))))
        self.assertEqual([ProjectId("fresh")], store.created)

    def test_rejects_duplicate_project(self) -> None:
        with self.assertRaisesRegex(ValueError, "already exists"):
            CreateProject(FakeStore(), FakeStore()).create("zebra", ProjectImage(b"png"))

    def test_rejects_invalid_project_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid project ID"):
            CreateProject(FakeStore(), FakeStore()).create("../escape", ProjectImage(b"png"))


if __name__ == "__main__":
    unittest.main()
