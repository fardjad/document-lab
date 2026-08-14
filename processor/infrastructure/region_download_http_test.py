import unittest

from fastapi.testclient import TestClient

from application.project_access.usecases.project_queries import ProjectQueries
from application.region_management.usecases.region_commands import RegionCommands
from application.region_export.usecases.export_region import RegionExport
from infrastructure.http_api import create_app
from model.project import ProjectId, ProjectImage, ProjectRegions, CropRectangle, CropRegion


class Store:
    def list_project_ids(self):
        return [ProjectId("project")]

    def read_project_image(self, project_id):
        return ProjectImage(b"not used")

    def read_project_image_size(self, project_id):
        return (10, 10)

    def read_project_regions(self, project_id):
        return ProjectRegions(2, (CropRegion(1, "Region 1", CropRectangle(0, 0, 1, 1)),))

    def write_project_regions(self, project_id, regions):
        pass


class Export:
    def export(self, project_id, region_id):
        if project_id != "project":
            from model.project import ProjectNotFound
            raise ProjectNotFound("Project not found")
        if region_id != 1:
            from model.project import RegionNotFound
            raise RegionNotFound("Region not found")
        return b"png"


class RegionDownloadHttpTests(unittest.TestCase):
    def test_download_returns_png_attachment(self) -> None:
        store = Store()
        client = TestClient(create_app(ProjectQueries(store), [], RegionCommands(store), Export()))
        response = client.get("/api/projects/project/regions/1/download")
        self.assertEqual(200, response.status_code)
        self.assertEqual(b"png", response.content)
        self.assertEqual("image/png", response.headers["content-type"])
        self.assertEqual('attachment; filename="project-region-1.png"', response.headers["content-disposition"])

    def test_missing_region_is_404(self) -> None:
        store = Store()
        response = TestClient(create_app(ProjectQueries(store), [], RegionCommands(store), Export())).get("/api/projects/project/regions/2/download")
        self.assertEqual(404, response.status_code)


if __name__ == "__main__":
    unittest.main()
