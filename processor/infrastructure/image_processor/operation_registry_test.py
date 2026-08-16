import unittest

from infrastructure.image_processor.operation_registry import OperationRegistryImpl


class Operation:
    def __init__(self, kind):
        self.kind = kind


class OperationRegistryImplTests(unittest.TestCase):
    def test_get_returns_registered_executor(self) -> None:
        operations = [Operation("rotate"), Operation("straighten"), Operation("trim")]
        registry = OperationRegistryImpl(operations)
        self.assertIs(registry.get("rotate"), operations[0])
        self.assertIs(registry.get("straighten"), operations[1])
        self.assertIs(registry.get("trim"), operations[2])

    def test_get_unknown_kind_raises(self) -> None:
        registry = OperationRegistryImpl([Operation("rotate")])
        with self.assertRaisesRegex(ValueError, "Unknown operation kind"):
            registry.get("nonexistent")

    def test_kinds_returns_all_registered(self) -> None:
        registry = OperationRegistryImpl([Operation("rotate"), Operation("straighten"), Operation("trim")])
        self.assertEqual(("rotate", "straighten", "trim"), registry.kinds())

    def test_empty_registry_returns_empty_tuple(self) -> None:
        self.assertEqual((), OperationRegistryImpl([]).kinds())


if __name__ == "__main__":
    unittest.main()
