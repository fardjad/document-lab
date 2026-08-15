import unittest

from application.project.usecases.read_project_image_size import ReadProjectImageSize
from model.project import ProjectId, ProjectNotFound


class FakeStore:
    def read_project_image_size(self, project_id: ProjectId) -> tuple[int, int]:
        return 10, 20


class ReadProjectImageSizeTests(unittest.TestCase):
    def test_reads_project_image_size(self) -> None:
        self.assertEqual((10, 20), ReadProjectImageSize(FakeStore()).read("Alpha"))

    def test_rejects_invalid_raw_project_id(self) -> None:
        with self.assertRaisesRegex(ProjectNotFound, "^Project not found$"):
            ReadProjectImageSize(FakeStore()).read("../outside")


if __name__ == "__main__":
    unittest.main()
