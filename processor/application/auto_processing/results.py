from dataclasses import dataclass

try:
    from model.operation import Operation
except ImportError:
    from ...model.operation import Operation


@dataclass(frozen=True)
class AutoProcessingResult:
    suggestion: float | Operation | None
    confidence: float | None
    reason: str