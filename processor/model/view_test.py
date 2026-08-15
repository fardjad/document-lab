import unittest

from model.operation import Operation
from model.pipeline import Pipeline
from model.view import View


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


if __name__ == "__main__":
    unittest.main()
