from dataclasses import dataclass

try:
    from model.operation import Operation
except ImportError:
    from .operation import Operation


@dataclass(frozen=True)
class Pipeline:
    """An ordered list of operations applied to a rendered region.

    Operations are generic ``Operation(kind, options)`` values. The order is
    defined by the list, not fixed. An empty pipeline is an identity transform.
    """

    operations: tuple[Operation, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "operations", tuple(self.operations))
        if any(not isinstance(item, Operation) for item in self.operations):
            raise ValueError("Invalid pipeline operations")

    def without(self, *kinds: str) -> "Pipeline":
        """A pipeline with operations of the given kinds filtered out."""

        return Pipeline(tuple(op for op in self.operations if op.kind not in kinds))