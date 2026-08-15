import unittest

from model.project import Project, ProjectId, ProjectImage
from model.view import ProjectViews, View


class ProjectIdTests(unittest.TestCase):
    def test_accepts_valid_ids(self) -> None:
        for value in ("project", "A1", "project.name", "project-name", "project_name"):
            self.assertEqual(value, ProjectId(value).value)

    def test_rejects_invalid_ids(self) -> None:
        for value in ("", "../outside", "bad project", "/absolute", ".hidden", 42, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ProjectId(value)  # type: ignore[arg-type]


class ProjectImageTests(unittest.TestCase):
    def test_from_png_accepts_png_data(self) -> None:
        data = b"\x89PNG\r\n\x1a\n" + b"rest"
        self.assertEqual(ProjectImage(data), ProjectImage.from_png(data))

    def test_from_png_rejects_other_formats(self) -> None:
        for data in (b"\xff\xd8\xff\xe0jpeg", b"", "not bytes"):
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, "Only PNG"):
                ProjectImage.from_png(data)  # type: ignore[arg-type]


class ProjectViewsDelegationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Project(ProjectId("project"), ProjectImage(b"image"), ProjectViews(2, (View(1, "first"),)))

    def test_find_view_delegates(self) -> None:
        self.assertEqual(View(1, "first"), self.project.find_view(1))

    def test_add_view_delegates(self) -> None:
        updated = self.project.add_view(View(2, "second"))
        self.assertEqual((View(1, "first"), View(2, "second")), updated.views.views)

    def test_replace_view_delegates(self) -> None:
        updated = self.project.replace_view(View(1, "renamed"))
        self.assertEqual("renamed", updated.find_view(1).name)

    def test_remove_view_delegates(self) -> None:
        updated = self.project.remove_view(1)
        self.assertEqual((), updated.views.views)


if __name__ == "__main__":
    unittest.main()
