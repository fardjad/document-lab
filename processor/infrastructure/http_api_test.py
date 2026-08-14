import unittest

from fastapi.testclient import TestClient

from application.project_access.ports.project_source import ProjectSource
from application.project_access.usecases.project_queries import ProjectQueries
from application.region_management.usecases.region_commands import RegionCommands
from infrastructure.http_api import create_app
from model.project import ProjectId, ProjectImage, ProjectNotFound
from model.project import ProjectRegions


class FakeProjectSource(ProjectSource):
    def list_project_ids(self) -> list[ProjectId]:
        return [ProjectId("zebra"), ProjectId("Alpha")]

    def read_project_image(self, project_id: ProjectId) -> ProjectImage:
        if project_id.value != "Alpha":
            raise ProjectNotFound("Project image not found")
        return ProjectImage(b"png bytes")


class FakeRegionStore:
    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions:
        return ProjectRegions(1)

    def write_project_regions(self, project_id: ProjectId, regions: ProjectRegions) -> None:
        pass


def test_client() -> TestClient:
    store = FakeRegionStore()
    return TestClient(create_app(ProjectQueries(FakeProjectSource()), ["http://allowed.test"], RegionCommands(store)))


class HttpApiTests(unittest.TestCase):
    def test_lists_projects_as_sorted_json(self) -> None:
        self.assertEqual(["Alpha", "zebra"], test_client().get("/api/projects").json())

    def test_returns_original_bytes_as_png(self) -> None:
        response = test_client().get("/api/projects/Alpha/image")
        self.assertEqual(200, response.status_code)
        self.assertEqual(b"png bytes", response.content)
        self.assertEqual("image/png", response.headers["content-type"])

    def test_returns_exact_missing_project_payload(self) -> None:
        response = test_client().get("/api/projects/missing/image")
        self.assertEqual(404, response.status_code)
        self.assertEqual({"detail": "Project image not found"}, response.json())

    def test_returns_exact_invalid_id_payload(self) -> None:
        response = test_client().get("/api/projects/bad%20project/image")
        self.assertEqual(404, response.status_code)
        self.assertEqual({"detail": "Project not found"}, response.json())

    def test_allows_configured_cors_origin(self) -> None:
        response = test_client().get("/api/projects", headers={"Origin": "http://allowed.test"})
        self.assertEqual("http://allowed.test", response.headers.get("access-control-allow-origin"))

    def test_rejects_unconfigured_cors_origin(self) -> None:
        response = test_client().get("/api/projects", headers={"Origin": "http://blocked.test"})
        self.assertNotIn("access-control-allow-origin", response.headers)


if __name__ == "__main__":
    unittest.main()
