import unittest

from application.project_access.ports.project_source import ProjectSource
from application.project_access.usecases.project_queries import ProjectQueries
from model.project import ProjectId, ProjectImage, ProjectNotFound


class FakeProjectSource(ProjectSource):
    def __init__(self) -> None:
        self.project_ids = [ProjectId("zebra"), ProjectId("Alpha")]
        self.read_ids: list[ProjectId] = []

    def list_project_ids(self) -> list[ProjectId]:
        return self.project_ids

    def read_project_image(self, project_id: ProjectId) -> ProjectImage:
        self.read_ids.append(project_id)
        return ProjectImage(b"image")


class ProjectQueriesTests(unittest.TestCase):
    def test_lists_project_ids_sorted(self) -> None:
        source = FakeProjectSource()
        self.assertEqual(["Alpha", "zebra"], ProjectQueries(source).list_projects())

    def test_rejects_invalid_raw_project_id(self) -> None:
        with self.assertRaisesRegex(ProjectNotFound, "^Project not found$"):
            ProjectQueries(FakeProjectSource()).read_project_image("../outside")

    def test_delegates_image_read_with_validated_id(self) -> None:
        source = FakeProjectSource()
        self.assertEqual(b"image", ProjectQueries(source).read_project_image("Alpha").data)
        self.assertEqual([ProjectId("Alpha")], source.read_ids)


if __name__ == "__main__":
    unittest.main()
