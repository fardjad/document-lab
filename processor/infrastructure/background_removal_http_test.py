import unittest

from fastapi.testclient import TestClient

from application.project_access.usecases.project_queries import ProjectQueries
from application.region_background.usecases.remove_background import BackgroundRemovalError
from application.region_management.usecases.region_commands import RegionCommands
from infrastructure.http_api import create_app
from model.project import BackgroundRemoval, ProjectId, ProjectImage, ProjectNotFound, ProjectRegions, RegionNotFound


class Store:
    def __init__(self) -> None:
        from model.project import CropRectangle, CropRegion
        self.value = ProjectRegions(2, (CropRegion(1, "Region 1", CropRectangle(0, 0, 1, 1)),))

    def list_project_ids(self):
        return [ProjectId("project")]

    def read_project_image(self, project_id):
        return ProjectImage(b"src")

    def read_project_image_size(self, project_id):
        return (10, 10)

    def read_project_regions(self, project_id):
        return self.value

    def write_project_regions(self, project_id, regions):
        self.value = regions


class Preview:
    def __init__(self, failing: str | None = None) -> None:
        self.failing = failing

    def preview(self, project_id, region_id, settings):
        if self.failing == "project":
            raise ProjectNotFound("Project not found")
        if self.failing == "region":
            raise RegionNotFound("Region not found")
        if self.failing == "render":
            raise BackgroundRemovalError("Unable to render region")
        return b"png"


def _body(**overrides) -> dict:
    payload = {"model": "u2net", "alpha_matting": False, "alpha_matting_foreground_threshold": 240, "alpha_matting_background_threshold": 10, "alpha_matting_erode_size": 10, "post_process_mask": False}
    payload.update(overrides)
    return payload


def _client(preview: Preview | None, store: Store | None = None) -> TestClient:
    store = store or Store()
    return TestClient(create_app(ProjectQueries(store), [], RegionCommands(store), None, None, preview))


class BackgroundRemovalHttpTests(unittest.TestCase):
    def test_preview_returns_png(self) -> None:
        response = _client(Preview()).post("/api/projects/project/regions/1/background-removal/preview", json=_body())
        self.assertEqual(200, response.status_code)
        self.assertEqual(b"png", response.content)
        self.assertEqual("image/png", response.headers["content-type"])

    def test_preview_rejects_invalid_model_and_threshold(self) -> None:
        for body in (_body(model="nope"), _body(alpha_matting_foreground_threshold=999)):
            with self.subTest(body=body):
                self.assertEqual(422, _client(Preview()).post("/api/projects/project/regions/1/background-removal/preview", json=body).status_code)

    def test_preview_maps_errors(self) -> None:
        for failing, status in (("project", 404), ("region", 404), ("render", 422)):
            with self.subTest(failing=failing):
                self.assertEqual(status, _client(Preview(failing=failing)).post("/api/projects/project/regions/1/background-removal/preview", json=_body()).status_code)

    def test_put_persists_and_clears_background_removal(self) -> None:
        store = Store()
        client = _client(Preview(), store)
        put_body = {"name": "Region 1", "rotation": 0, "straighten": 0.0, "trim": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "rectangle": {"x": 0, "y": 0, "width": 1, "height": 1}}
        response = client.put("/api/projects/project/regions/1", json={**put_body, "background_removal": _body(model="u2net")})
        self.assertEqual(200, response.status_code)
        self.assertEqual("u2net", response.json()["background_removal"]["model"])
        self.assertEqual("u2net", store.value.regions[0].background_removal.model)
        cleared = client.put("/api/projects/project/regions/1", json={**put_body, "background_removal": None})
        self.assertIsNone(cleared.json()["background_removal"])
        self.assertIsNone(store.value.regions[0].background_removal)


if __name__ == "__main__":
    unittest.main()
