try:
    from application.project_access.ports.project_source import ProjectSource
    from application.region_management.ports.project_region_store import ProjectRegionStore
    from application.region_analysis.ports.region_analyzer import RegionAnalyzer
    from application.region_analysis.results import AnalysisResult
    from model.project import ProjectId, ProjectNotFound, RegionNotFound
except ImportError:
    from ...project_access.ports.project_source import ProjectSource
    from ...region_management.ports.project_region_store import ProjectRegionStore
    from ..ports.region_analyzer import RegionAnalyzer
    from ..results import AnalysisResult
    from ....model.project import ProjectId, ProjectNotFound, RegionNotFound


class RegionAnalysis:
    def __init__(self, source: ProjectSource, regions: ProjectRegionStore, analyzer: RegionAnalyzer) -> None:
        self._source = source
        self._regions = regions
        self._analyzer = analyzer

    def analyze(self, raw_project_id: str, region_id: int, operation: str) -> AnalysisResult:
        try:
            project_id = ProjectId(raw_project_id)
        except ValueError as error:
            raise ProjectNotFound("Project not found") from error
        regions = self._regions.read_project_regions(project_id)
        region = next((item for item in regions.regions if item.id == region_id), None)
        if region is None:
            raise RegionNotFound("Region not found")
        return self._analyzer.analyze(self._source.read_project_image(project_id), region, operation)
