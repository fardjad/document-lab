import unittest

from fastapi.testclient import TestClient

from application.project_access.usecases.project_queries import ProjectQueries
from application.slice_management.usecases.slice_commands import SliceCommands
from infrastructure.http_api import create_app
from model.project import ProjectId, ProjectImage, ProjectSlices


class FakeStore:
    def __init__(self) -> None:
        self.value = ProjectSlices(1)

    def list_project_ids(self) -> list[ProjectId]:
        return [ProjectId("project")]

    def read_project_image(self, project_id: ProjectId) -> ProjectImage:
        raise AssertionError

    def read_project_slices(self, project_id: ProjectId) -> ProjectSlices:
        return self.value

    def write_project_slices(self, project_id: ProjectId, slices: ProjectSlices) -> None:
        self.value = slices


class SliceHttpTests(unittest.TestCase):
    def test_invalid_rectangle_is_422_and_slice_cors_methods_are_allowed(self) -> None:
        store = FakeStore()
        client = TestClient(create_app(ProjectQueries(store), ["http://allowed.test"], SliceCommands(store)))
        response = client.post("/api/projects/project/slices", json={"rectangle": {"x": 0, "y": 0, "width": 0, "height": 1}})
        self.assertEqual(422, response.status_code)
        preflight = client.options("/api/projects/project/slices", headers={"Origin": "http://allowed.test", "Access-Control-Request-Method": "POST"})
        self.assertIn("POST", preflight.headers.get("access-control-allow-methods", ""))

    def test_rectangle_only_post_gets_backend_name(self) -> None:
        store = FakeStore()
        client = TestClient(create_app(ProjectQueries(store), [], SliceCommands(store)))
        response = client.post("/api/projects/project/slices", json={"rectangle": {"x": 0, "y": 0, "width": 1, "height": 1}})
        self.assertEqual(201, response.status_code)
        self.assertEqual("Slice 1", response.json()["name"])
        self.assertEqual(0, response.json()["rotation"])

    def test_put_requires_and_returns_rotation(self) -> None:
        store = FakeStore()
        client = TestClient(create_app(ProjectQueries(store), [], SliceCommands(store)))
        client.post("/api/projects/project/slices", json={"rectangle": {"x": 0, "y": 0, "width": 1, "height": 1}})
        response = client.put("/api/projects/project/slices/1", json={"name": "Turned", "rotation": 90, "rectangle": {"x": 0, "y": 0, "width": 1, "height": 1}})
        self.assertEqual(200, response.status_code)
        self.assertEqual(90, response.json()["rotation"])
        self.assertEqual(422, client.put("/api/projects/project/slices/1", json={"name": "Missing", "rectangle": {"x": 0, "y": 0, "width": 1, "height": 1}}).status_code)
        self.assertEqual(422, client.put("/api/projects/project/slices/1", json={"name": "Invalid", "rotation": 45, "rectangle": {"x": 0, "y": 0, "width": 1, "height": 1}}).status_code)

    def test_create_rejects_name_field(self) -> None:
        store = FakeStore()
        client = TestClient(create_app(ProjectQueries(store), [], SliceCommands(store)))
        response = client.post("/api/projects/project/slices", json={"name": "Unwanted", "rectangle": {"x": 0, "y": 0, "width": 1, "height": 1}})
        self.assertEqual(422, response.status_code)


if __name__ == "__main__":
    unittest.main()
