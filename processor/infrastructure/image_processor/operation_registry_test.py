import unittest

from infrastructure.image_processor.operation_registry import OperationRegistryImpl
from infrastructure.image_processor.operations.rotate import RotateExecutor
from infrastructure.image_processor.operations.straighten import StraightenExecutor
from infrastructure.image_processor.operations.trim import TrimExecutor


class OperationRegistryImplTests(unittest.TestCase):
    def test_get_returns_registered_executor(self) -> None:
        registry = OperationRegistryImpl([RotateExecutor(), StraightenExecutor(), TrimExecutor()])
        self.assertIsInstance(registry.get("rotate"), RotateExecutor)
        self.assertIsInstance(registry.get("straighten"), StraightenExecutor)
        self.assertIsInstance(registry.get("trim"), TrimExecutor)

    def test_get_unknown_kind_raises(self) -> None:
        registry = OperationRegistryImpl([RotateExecutor()])
        with self.assertRaisesRegex(ValueError, "Unknown operation kind"):
            registry.get("nonexistent")

    def test_kinds_returns_all_registered(self) -> None:
        registry = OperationRegistryImpl([RotateExecutor(), StraightenExecutor(), TrimExecutor()])
        self.assertEqual(("rotate", "straighten", "trim"), registry.kinds())

    def test_empty_registry_returns_empty_tuple(self) -> None:
        self.assertEqual((), OperationRegistryImpl([]).kinds())


if __name__ == "__main__":
    unittest.main()