from typing import Protocol

try:
    from application.region_analysis.results import AnalysisResult
    from model.project import CropRegion, ProjectImage
except ImportError:
    from ..results import AnalysisResult
    from ....model.project import CropRegion, ProjectImage


class RegionAnalyzer(Protocol):
    def analyze(self, image: ProjectImage, region: CropRegion, operation: str) -> AnalysisResult: ...
