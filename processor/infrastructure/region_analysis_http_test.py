import unittest

from fastapi.testclient import TestClient

from application.project_access.usecases.project_queries import ProjectQueries
from application.region_management.usecases.region_commands import RegionCommands
from infrastructure.http_api import create_app
from model.project import CropRectangle, CropRegion, ProjectId, ProjectImage, ProjectRegions, RegionTrim


class Store:
    def __init__(self) -> None:
        self.writes = 0

    def list_project_ids(self):
        return [ProjectId("project")]

    def read_project_image(self, project_id):
        return ProjectImage(b"image")

    def read_project_image_size(self, project_id):
        return 10, 10

    def read_project_regions(self, project_id):
        return ProjectRegions(2, (CropRegion(1, "r", CropRectangle(0, 0, 1, 1)),))

    def write_project_regions(self, project_id, regions):
        self.writes += 1


class Analysis:
    def analyze(self, project_id, region_id, operation):
        from application.region_analysis.results import AnalysisResult
        return AnalysisResult(RegionTrim(top=1), 0.9, "detected")


class RegionAnalysisHttpTests(unittest.TestCase):
    def test_analysis_schema_and_non_write_behavior(self) -> None:
        store = Store()
        client = TestClient(create_app(ProjectQueries(store), [], RegionCommands(store), region_analysis=Analysis()))
        response = client.post("/api/projects/project/regions/1/analysis", json={"operation": "trim"})
        self.assertEqual(200, response.status_code)
        self.assertEqual({"top": 1, "right": 0, "bottom": 0, "left": 0}, response.json()["suggestion"])
        self.assertEqual(0, store.writes)
        self.assertEqual(422, client.post("/api/projects/project/regions/1/analysis", json={"operation": "unknown"}).status_code)
        self.assertEqual(422, client.post("/api/projects/project/regions/1/analysis", json={"operation": "trim", "extra": 1}).status_code)


if __name__ == "__main__":
    unittest.main()
