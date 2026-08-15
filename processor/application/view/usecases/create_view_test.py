import unittest

from application.view.usecases.create_view import CreateView
from model.pipeline import Pipeline
from model.project import ProjectId, ProjectNotFound
from model.project import Project, ProjectImage
from model.view import View


class FakeImageSizes:
    size = (100, 100)

    def read(self, raw_project_id: str) -> tuple[int, int]:
        return self.size


class FakeViewStore:
    def __init__(self) -> None:
        self.value = Project(ProjectId("project"), ProjectImage(b""))

    def read_project_views(self, project_id: ProjectId) -> Project:
        return self.value

    def write_project_views(self, project_id: ProjectId, views: Project) -> None:
        self.value = views


class CreateViewTests(unittest.TestCase):
    def test_creates_view_with_identity_pipeline_and_sequential_ids(self) -> None:
        store = FakeViewStore()
        first = CreateView(store).create("project", "Region 1")
        second = CreateView(store).create("project", "Region 2")
        self.assertEqual((1, 2), (first.id, second.id))
        self.assertEqual("Region 2", second.name)
        self.assertEqual(Pipeline(), first.pipeline)

    def test_persists_created_view(self) -> None:
        store = FakeViewStore()
        created = CreateView(store).create("project", "New view")
        self.assertEqual(created, store.value.find_view(created.id))

    def test_rejects_invalid_project_id(self) -> None:
        with self.assertRaises(ProjectNotFound):
            CreateView(FakeViewStore()).create("../nope", "New view")


if __name__ == "__main__":
    unittest.main()
