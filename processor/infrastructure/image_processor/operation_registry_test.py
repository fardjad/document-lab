import unittest

from infrastructure.image_processor.operation_registry import OperationRegistryImpl
from infrastructure.image_processor.operations.rotate import RotateOperation
from infrastructure.image_processor.operations.straighten import StraightenOperation
from infrastructure.image_processor.operations.trim import TrimOperation


class OperationRegistryImplTests(unittest.TestCase):
    def test_get_returns_registered_executor(self) -> None:
        registry = OperationRegistryImpl([RotateOperation(), StraightenOperation(), TrimOperation()])
        self.assertIsInstance(registry.get("rotate"), RotateOperation)
        self.assertIsInstance(registry.get("straighten"), StraightenOperation)
        self.assertIsInstance(registry.get("trim"), TrimOperation)

    def test_get_unknown_kind_raises(self) -> None:
        registry = OperationRegistryImpl([RotateOperation()])
        with self.assertRaisesRegex(ValueError, "Unknown operation kind"):
            registry.get("nonexistent")

    def test_kinds_returns_all_registered(self) -> None:
        registry = OperationRegistryImpl([RotateOperation(), StraightenOperation(), TrimOperation()])
        self.assertEqual(("rotate", "straighten", "trim"), registry.kinds())

    def test_empty_registry_returns_empty_tuple(self) -> None:
        self.assertEqual((), OperationRegistryImpl([]).kinds())


if __name__ == "__main__":
    unittest.main()