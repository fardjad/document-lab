import unittest

from application.view.usecases.delete_view import DeleteView
from model.project import ProjectId, ProjectNotFound
from model.view import View, ProjectViews, ViewNotFound


class FakeViewStore:
    def __init__(self) -> None:
        self.value = ProjectViews(3, (View(1, "Region 1"), View(2, "Region 2")))

    def read_project_views(self, project_id: ProjectId) -> ProjectViews:
        return self.value

    def write_project_views(self, project_id: ProjectId, views: ProjectViews) -> None:
        self.value = views


class DeleteViewTests(unittest.TestCase):
    def test_removes_view_and_keeps_next_id(self) -> None:
        store = FakeViewStore()
        DeleteView(store).delete("project", 1)
        self.assertEqual((2,), tuple(item.id for item in store.value.views))
        self.assertEqual(3, store.value.next_view_id)

    def test_rejects_missing_view(self) -> None:
        with self.assertRaises(ViewNotFound):
            DeleteView(FakeViewStore()).delete("project", 9)

    def test_rejects_invalid_project_id(self) -> None:
        with self.assertRaises(ProjectNotFound):
            DeleteView(FakeViewStore()).delete("../nope", 1)


if __name__ == "__main__":
    unittest.main()
