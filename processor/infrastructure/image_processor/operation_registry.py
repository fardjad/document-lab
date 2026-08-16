try:
    from application.view.ports.operation_registry import Operation
    from application.view.ports.operation_spec import OperationSpec
except ImportError:
    from ...application.view.ports.operation_registry import Operation
    from ...application.view.ports.operation_spec import OperationSpec


class OperationRegistryImpl:
    """Concrete registry mapping operation kind strings to operation instances."""

    def __init__(self, operations, specs=None) -> None:
        self._operations = {operation.kind: operation for operation in operations}

    def replace(self, operations) -> None:
        """Atomically replace registered operations after an extension reload."""
        self._operations = {operation.kind: operation for operation in operations}

    def get(self, kind: str) -> Operation:
        operation = self._operations.get(kind)
        if operation is None:
            raise ValueError(f"Unknown operation kind: {kind}")
        return operation

    def kinds(self) -> tuple[str, ...]:
        return tuple(self._operations.keys())

    def spec_for(self, kind: str) -> OperationSpec:
        return self.get(kind).spec
