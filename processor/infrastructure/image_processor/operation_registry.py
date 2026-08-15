try:
    from application.view.ports.operation_registry import OperationExecutor
    from model.operation_spec import OperationSpec
except ImportError:
    from ...application.view.ports.operation_registry import OperationExecutor
    from ...model.operation_spec import OperationSpec


class OperationRegistryImpl:
    """Concrete registry mapping operation kind strings to executor instances."""

    def __init__(self, executors, specs=None) -> None:
        self._executors = {executor.kind: executor for executor in executors}
        self._specs = ({executor.kind: executor.spec for executor in executors if hasattr(executor, "spec")}
                       if specs is None else {spec.kind: spec for spec in specs})

    def get(self, kind: str) -> OperationExecutor:
        executor = self._executors.get(kind)
        if executor is None:
            raise ValueError(f"Unknown operation kind: {kind}")
        return executor

    def kinds(self) -> tuple[str, ...]:
        return tuple(self._executors.keys())

    def spec_for(self, kind: str) -> OperationSpec:
        spec = self._specs.get(kind)
        if spec is None:
            raise ValueError(f"Unknown operation kind: {kind}")
        return spec
