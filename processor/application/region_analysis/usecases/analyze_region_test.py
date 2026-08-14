import unittest

from application.region_analysis.results import AnalysisResult
from application.region_analysis.usecases.analyze_region import RegionAnalysis
from model.project import CropRectangle, CropRegion, ProjectId, ProjectImage, ProjectRegions, RegionTrim


class Source:
    def read_project_image(self, project_id: ProjectId) -> ProjectImage:
        return ProjectImage(b"unchanged")


class Store:
    def __init__(self) -> None:
        self.writes = 0

    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions:
        return ProjectRegions(2, (CropRegion(1, "r", CropRectangle(0, 0, 1, 1)),))

    def write_project_regions(self, project_id, regions) -> None:
        self.writes += 1


class Analyzer:
    def analyze(self, image: ProjectImage, region: CropRegion, operation: str) -> AnalysisResult:
        return AnalysisResult(RegionTrim(left=1) if operation == "trim" else 2.0, 0.8, "test")


class AnalyzeRegionTests(unittest.TestCase):
    def test_returns_suggestion_without_persisting(self) -> None:
        store = Store()
        result = RegionAnalysis(Source(), store, Analyzer()).analyze("project", 1, "trim")
        self.assertEqual(RegionTrim(left=1), result.suggestion)
        self.assertEqual(0, store.writes)


if __name__ == "__main__":
    unittest.main()
