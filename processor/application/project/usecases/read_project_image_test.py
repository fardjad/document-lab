import unittest

from application.project.usecases.read_project_image import ReadProjectImage
from model.project import ProjectId, ProjectImage, ProjectNotFound


class FakeStore:
    def read_project_image(self, project_id: ProjectId) -> ProjectImage:
        return ProjectImage(b"image")


class ReadProjectImageTests(unittest.TestCase):
    def test_reads_project_image(self) -> None:
        self.assertEqual(ProjectImage(b"image"), ReadProjectImage(FakeStore()).read("Alpha"))

    def test_rejects_invalid_raw_project_id(self) -> None:
        with self.assertRaisesRegex(ProjectNotFound, "^Project not found$"):
            ReadProjectImage(FakeStore()).read("../outside")


if __name__ == "__main__":
    unittest.main()
