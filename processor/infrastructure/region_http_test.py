import unittest

from fastapi.testclient import TestClient

from application.project_access.usecases.project_queries import ProjectQueries
from application.region_management.usecases.region_commands import RegionCommands
from infrastructure.http_api import create_app
from model.project import ProjectId, ProjectImage, ProjectRegions


class FakeStore:
    def __init__(self) -> None:
        self.value = ProjectRegions(1)

    def list_project_ids(self) -> list[ProjectId]:
        return [ProjectId("project")]

    def read_project_image(self, project_id: ProjectId) -> ProjectImage:
        raise AssertionError

    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions:
        return self.value

    def write_project_regions(self, project_id: ProjectId, regions: ProjectRegions) -> None:
        self.value = regions

    def read_project_image_size(self, project_id: ProjectId) -> tuple[int, int]:
        return 100, 100


class RegionHttpTests(unittest.TestCase):
    def test_invalid_rectangle_is_422_and_region_cors_methods_are_allowed(self) -> None:
        store = FakeStore()
        client = TestClient(create_app(ProjectQueries(store), ["http://allowed.test"], RegionCommands(store)))
        response = client.post("/api/projects/project/regions", json={"rectangle": {"x": 0, "y": 0, "width": 0, "height": 1}})
        self.assertEqual(422, response.status_code)
        preflight = client.options("/api/projects/project/regions", headers={"Origin": "http://allowed.test", "Access-Control-Request-Method": "POST"})
        self.assertIn("POST", preflight.headers.get("access-control-allow-methods", ""))

    def test_rectangle_only_post_gets_backend_name(self) -> None:
        store = FakeStore()
        client = TestClient(create_app(ProjectQueries(store), [], RegionCommands(store)))
        response = client.post("/api/projects/project/regions", json={"rectangle": {"x": 0, "y": 0, "width": 1, "height": 1}})
        self.assertEqual(201, response.status_code)
        self.assertEqual("Region 1", response.json()["name"])
        self.assertEqual(0, response.json()["rotation"])

    def test_put_requires_and_returns_rotation(self) -> None:
        store = FakeStore()
        client = TestClient(create_app(ProjectQueries(store), [], RegionCommands(store)))
        client.post("/api/projects/project/regions", json={"rectangle": {"x": 0, "y": 0, "width": 1, "height": 1}})
        response = client.put("/api/projects/project/regions/1", json={"name": "Turned", "rotation": 90, "straighten": 0, "trim": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "rectangle": {"x": 0, "y": 0, "width": 1, "height": 1}})
        self.assertEqual(200, response.status_code)
        self.assertEqual(90, response.json()["rotation"])
        self.assertEqual(0.0, response.json()["straighten"])
        self.assertEqual({"top": 0, "right": 0, "bottom": 0, "left": 0}, response.json()["trim"])
        self.assertEqual(422, client.put("/api/projects/project/regions/1", json={"name": "Missing", "rectangle": {"x": 0, "y": 0, "width": 1, "height": 1}}).status_code)
        self.assertEqual(422, client.put("/api/projects/project/regions/1", json={"name": "Invalid", "rotation": 45, "straighten": 0.0, "trim": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "rectangle": {"x": 0, "y": 0, "width": 1, "height": 1}}).status_code)
        self.assertEqual(422, client.put("/api/projects/project/regions/1", json={"name": "Invalid trim", "rotation": 0, "straighten": 0.0, "trim": {"top": -1, "right": 0, "bottom": 0, "left": 0}, "rectangle": {"x": 0, "y": 0, "width": 1, "height": 1}}).status_code)
        for value in (True, "0"):
            with self.subTest(value=value):
                self.assertEqual(422, client.put("/api/projects/project/regions/1", json={"name": "Invalid straighten", "rotation": 0, "straighten": value, "trim": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "rectangle": {"x": 0, "y": 0, "width": 1, "height": 1}}).status_code)

    def test_create_rejects_name_field(self) -> None:
        store = FakeStore()
        client = TestClient(create_app(ProjectQueries(store), [], RegionCommands(store)))
        response = client.post("/api/projects/project/regions", json={"name": "Unwanted", "rectangle": {"x": 0, "y": 0, "width": 1, "height": 1}})
        self.assertEqual(422, response.status_code)


if __name__ == "__main__":
    unittest.main()
