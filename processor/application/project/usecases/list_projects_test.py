import unittest

from application.project.usecases.list_projects import ListProjects
from model.project import ProjectId


class FakeStore:
    def list_project_ids(self):
        return [ProjectId("zebra"), ProjectId("Alpha")]


class ListProjectsTests(unittest.TestCase):
    def test_lists_project_ids_sorted(self) -> None:
        self.assertEqual(["Alpha", "zebra"], ListProjects(FakeStore()).list())


if __name__ == "__main__":
    unittest.main()
