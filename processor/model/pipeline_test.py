import unittest

from model.operation import Operation
from model.pipeline import Pipeline


class PipelineTests(unittest.TestCase):
    def test_empty_pipeline_is_identity(self) -> None:
        self.assertEqual((), Pipeline().operations)

    def test_accepts_ordered_operations(self) -> None:
        ops = (Operation("rotate", {"degrees": 90}), Operation("straighten", {"angle": 1.5}))
        self.assertEqual(ops, Pipeline(ops).operations)

    def test_rejects_non_operation_elements(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid pipeline operations"):
            Pipeline(("rotate",))  # type: ignore[arg-type]

    def test_without_filters_by_kind(self) -> None:
        ops = (
            Operation("rotate", {"degrees": 90}),
            Operation("straighten", {"angle": 1.5}),
            Operation("trim", {"top": 2}),
        )
        pipeline = Pipeline(ops)
        filtered = pipeline.without("straighten", "trim")
        self.assertEqual((Operation("rotate", {"degrees": 90}),), filtered.operations)

    def test_without_preserves_order(self) -> None:
        ops = (
            Operation("rotate", {"degrees": 90}),
            Operation("trim", {"top": 2}),
            Operation("remove_background", {"model": "u2net"}),
        )
        pipeline = Pipeline(ops)
        filtered = pipeline.without("trim")
        self.assertEqual((ops[0], ops[2]), filtered.operations)


if __name__ == "__main__":
    unittest.main()