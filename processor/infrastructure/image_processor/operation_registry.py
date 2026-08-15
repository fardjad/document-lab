try:
    from application.region.ports.operation_registry import OperationExecutor
except ImportError:
    from ...application.region.ports.operation_registry import OperationExecutor


class OperationRegistryImpl:
    """Concrete registry mapping operation kind strings to executor instances."""

    def __init__(self, executors) -> None:
        self._executors = {executor.kind: executor for executor in executors}

    def get(self, kind: str) -> OperationExecutor:
        executor = self._executors.get(kind)
        if executor is None:
            raise ValueError(f"Unknown operation kind: {kind}")
        return executor

    def kinds(self) -> tuple[str, ...]:
        return tuple(self._executors.keys())