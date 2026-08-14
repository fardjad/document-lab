from dataclasses import dataclass

try:
    from model.project import RegionTrim
except ImportError:
    from ...model.project import RegionTrim


@dataclass(frozen=True)
class AnalysisResult:
    suggestion: float | RegionTrim | None
    confidence: float | None
    reason: str
