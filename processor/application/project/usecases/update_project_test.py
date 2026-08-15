import unittest

from application.project.usecases.update_project import UpdateProject
from model.project import ProjectId, ProjectImage, ProjectNotFound


class FakeStore:
    def __init__(self) -> None:
        self.ids = [ProjectId("Alpha")]
        self.replaced: list[ProjectId] = []

    def list_project_ids(self):
        return self.ids

    def replace_project_image(self, project_id, image):
        self.replaced.append(project_id)


class UpdateProjectTests(unittest.TestCase):
    def test_replaces_image_for_existing_project(self) -> None:
        store = FakeStore()
        UpdateProject(store, store).update("Alpha", ProjectImage(b"png"))
        self.assertEqual([ProjectId("Alpha")], store.replaced)

    def test_rejects_missing_project(self) -> None:
        with self.assertRaises(ProjectNotFound):
            UpdateProject(FakeStore(), FakeStore()).update("missing", ProjectImage(b"png"))


if __name__ == "__main__":
    unittest.main()
