import unittest

from model.project import ProjectId


class ProjectIdTests(unittest.TestCase):
    def test_accepts_valid_ids(self) -> None:
        for value in ("project", "A1", "project.name", "project-name", "project_name"):
            self.assertEqual(value, ProjectId(value).value)

    def test_rejects_invalid_ids(self) -> None:
        for value in ("", "../outside", "bad project", "/absolute", ".hidden"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ProjectId(value)


if __name__ == "__main__":
    unittest.main()
