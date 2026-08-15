from typing import Protocol

try:
    from application.auto_processing.results import AutoProcessingResult
except ImportError:
    from ..results import AutoProcessingResult


class DocumentStraightener(Protocol):
    """Outbound contract for detecting document skew."""

    def detect_skew(self, rendered: bytes) -> AutoProcessingResult: ...


class DocumentTrimmer(Protocol):
    """Outbound contract for detecting external background to trim."""

    def detect_trim(self, rendered: bytes) -> AutoProcessingResult: ...