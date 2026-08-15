import unittest

from application.view.usecases.list_views import ListViews
from model.project import ProjectId, ProjectNotFound
from model.project import Project, ProjectImage
from model.view import View


class FakeViewStore:
    def read_project_views(self, project_id: ProjectId) -> Project:
        return Project(ProjectId("project"), ProjectImage(b""), 2, (View(1, "Region 1"),))


class ListViewsTests(unittest.TestCase):
    def test_lists_views_of_project(self) -> None:
        views = ListViews(FakeViewStore()).list("project")
        self.assertEqual((1,), tuple(item.id for item in views.views))

    def test_rejects_invalid_project_id(self) -> None:
        with self.assertRaises(ProjectNotFound):
            ListViews(FakeViewStore()).list("../nope")


if __name__ == "__main__":
    unittest.main()
