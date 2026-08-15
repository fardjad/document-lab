import unittest

from model.operation import Operation
from model.pipeline import Pipeline
from model.view import ProjectViews, View, ViewNotFound


class ViewTests(unittest.TestCase):
    def test_strips_surrounding_whitespace_from_name(self) -> None:
        self.assertEqual("Receipt", View(1, "  Receipt  ").name)

    def test_rejects_blank_or_unprintable_names(self) -> None:
        for name in ("", "   ", "x" * 101, "bad\nname"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                View(1, name)

    def test_with_pipeline_rebinds_only_pipeline(self) -> None:
        view = View(1, "Receipt")
        pipeline = Pipeline((Operation("rotate", {"degrees": 90}),))
        rebound = view.with_pipeline(pipeline)
        self.assertEqual(pipeline, rebound.pipeline)
        self.assertEqual((view.id, view.name), (rebound.id, rebound.name))

    def test_default_pipeline_is_empty(self) -> None:
        self.assertEqual(Pipeline(), View(1, "x").pipeline)

    def test_view_requires_pipeline(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid view pipeline"):
            View(1, "View 1", pipeline={"rotate": 90})  # type: ignore[arg-type]


class ProjectViewsTests(unittest.TestCase):
    def test_find_returns_matching_or_none(self) -> None:
        views = ProjectViews(2, (View(1, "a"),))
        self.assertEqual(1, views.find(1).id)
        self.assertIsNone(views.find(9))

    def test_add_assigns_next_id_and_never_reuses(self) -> None:
        views = ProjectViews(5)
        added = views.add(View(5, "View 5"))
        self.assertEqual(6, added.next_view_id)
        removed = added.remove(5)
        self.assertEqual(6, removed.next_view_id)
        recreated = removed.add(View(6, "View 6"))
        self.assertEqual(7, recreated.next_view_id)

    def test_add_rejects_duplicate_ids(self) -> None:
        views = ProjectViews(2, (View(1, "a"),))
        with self.assertRaises(ValueError):
            views.add(View(1, "dup"))

    def test_replace_swaps_by_id(self) -> None:
        first = View(1, "a")
        second = View(2, "b")
        updated = View(1, "renamed")
        views = ProjectViews(3, (first, second))
        replaced = views.replace(updated)
        self.assertEqual((updated, second), replaced.views)
        with self.assertRaises(ViewNotFound):
            ProjectViews(1).replace(updated)

    def test_remove_deletes_by_id(self) -> None:
        first = View(1, "a")
        second = View(2, "b")
        views = ProjectViews(3, (first, second))
        self.assertEqual((second,), views.remove(1).views)
        with self.assertRaises(ViewNotFound):
            views.remove(9)

    def test_rejects_next_id_not_after_existing_ids(self) -> None:
        with self.assertRaises(ValueError):
            ProjectViews(1, (View(1, "a"),))


if __name__ == "__main__":
    unittest.main()
