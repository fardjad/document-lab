from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from infrastructure.http_api import create_app
from application.auto_processing.usecases.auto_straighten_region import AutoStraightenRegion
from application.auto_processing.usecases.auto_trim_region import AutoTrimRegion
from application.project.usecases.create_project import CreateProject
from application.project.usecases.delete_project import DeleteProject
from application.project.usecases.import_project import ImportProject
from application.project.usecases.list_projects import ListProjects
from application.project.usecases.read_project_image import ReadProjectImage
from application.project.usecases.read_project_image_size import ReadProjectImageSize
from application.project.usecases.update_project import UpdateProject
from application.region.usecases.delete_region import DeleteRegion
from application.region.usecases.list_regions import ListRegions
from application.region.usecases.create_region import CreateRegion
from application.region.usecases.update_region import UpdateRegion
from application.region.usecases.render_region import RenderRegion
from infrastructure.file_store.filesystem_project_source import FilesystemProjectStore
from infrastructure.image_processor.opencv_region_analyzer import OpenCVDocumentAnalyzer
from infrastructure.image_processor.operation_registry import OperationRegistryImpl
from infrastructure.image_processor.operations.remove_background import RemoveBackgroundExecutor
from infrastructure.image_processor.operations.rotate import RotateExecutor
from infrastructure.image_processor.operations.straighten import StraightenExecutor
from infrastructure.image_processor.operations.trim import TrimExecutor
from infrastructure.image_processor.pillow_region_cropper import PillowRegionCropper


class PassthroughRemover:
    def remove(self, image: bytes, settings) -> bytes:
        return image


def png() -> bytes:
    image = Image.new("RGB", (120, 90), "white")
    ImageDraw.Draw(image).rectangle((30, 20, 89, 69), fill="black")
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


PIPELINE = []


class HttpApiIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._directory.cleanup)
        root = Path(self._directory.name)
        store = FilesystemProjectStore(root)
        reader = ReadProjectImage(store)
        sizes = ReadProjectImageSize(store)
        registry = OperationRegistryImpl([RotateExecutor(), StraightenExecutor(), TrimExecutor(), RemoveBackgroundExecutor(PassthroughRemover())])
        cropper = PillowRegionCropper()
        analyzer = OpenCVDocumentAnalyzer()
        self.client = TestClient(create_app(ListProjects(store), reader, ["http://test"], CreateProject(store, store), UpdateProject(store, store), DeleteProject(store, store), ImportProject(store, store), ListRegions(store), CreateRegion(store, sizes), UpdateRegion(store, sizes, registry), DeleteRegion(store), RenderRegion(store, reader, cropper, registry), AutoStraightenRegion(store, reader, cropper, registry, analyzer), AutoTrimRegion(store, reader, cropper, registry, analyzer)))

    def test_project_lifecycle_end_to_end(self) -> None:
        created = self.client.post("/api/projects", params={"project_id": "scan"}, files={"image": ("image.png", png(), "image/png")})
        self.assertEqual(201, created.status_code)
        self.assertEqual(["scan"], self.client.get("/api/projects").json())
        self.assertEqual(png(), self.client.get("/api/projects/scan/image").content)
        duplicate = self.client.post("/api/projects", params={"project_id": "scan"}, files={"image": ("image.png", png(), "image/png")})
        self.assertEqual(422, duplicate.status_code)
        replaced = self.client.put("/api/projects/scan", files={"image": ("image.png", png(), "image/png")})
        self.assertEqual(204, replaced.status_code)
        missing = self.client.put("/api/projects/nope", files={"image": ("image.png", png(), "image/png")})
        self.assertEqual(404, missing.status_code)
        deleted = self.client.delete("/api/projects/scan")
        self.assertEqual(204, deleted.status_code)
        self.assertEqual([], self.client.get("/api/projects").json())
        self.assertEqual(404, self.client.delete("/api/projects/scan").status_code)

    def test_import_stub_is_501(self) -> None:
        response = self.client.post("/api/projects/import", files={"image": ("image.png", png(), "image/png")})
        self.assertEqual(501, response.status_code)

    def test_project_path_traversal_is_404(self) -> None:
        self.assertEqual(404, self.client.get("/api/projects/..%2Foutside/regions").status_code)

    def test_region_crud_with_pipeline_round_trip(self) -> None:
        self.client.post("/api/projects", params={"project_id": "scan"}, files={"image": ("image.png", png(), "image/png")})
        region = self.client.post("/api/projects/scan/regions", json={"rectangle": {"x": 0.25, "y": 0.2, "width": 0.5, "height": 0.55}}).json()
        self.assertEqual(1, region["id"])
        self.assertEqual(PIPELINE, region["pipeline"])
        body = {"name": "Card", "rectangle": region["rectangle"], "pipeline": {"operations": [{"kind": "rotate", "options": {"degrees": 90}}, {"kind": "straighten", "options": {"angle": 1.5}}, {"kind": "trim", "options": {"top": 2, "right": 0, "bottom": 1, "left": 0}}, {"kind": "remove_background", "options": {"model": "u2net", "alpha_matting": False, "alpha_matting_foreground_threshold": 240, "alpha_matting_background_threshold": 10, "alpha_matting_erode_size": 10, "post_process_mask": False}}]}}
        updated = self.client.put("/api/projects/scan/regions/1", json=body)
        self.assertEqual(200, updated.status_code)
        persisted = self.client.get("/api/projects/scan/regions").json()[0]
        self.assertEqual(body["pipeline"]["operations"], persisted["pipeline"])
        invalid = self.client.put("/api/projects/scan/regions/1", json={"name": "Card", "rectangle": region["rectangle"], "pipeline": {"operations": [{"kind": "rotate", "options": {"degrees": 45}}, {"kind": "trim", "options": {"top": 0, "right": 0, "bottom": 0, "left": 0}}]}})
        self.assertEqual(422, invalid.status_code)
        extra = self.client.put("/api/projects/scan/regions/1", json={"name": "Card", "rectangle": region["rectangle"], "pipeline": {"operations": [{"kind": "rotate", "options": {"degrees": 90}, "unknown": True}]}})
        self.assertEqual(422, extra.status_code)
        self.assertEqual(404, self.client.delete("/api/projects/scan/regions/9").status_code)
        self.assertEqual(204, self.client.delete("/api/projects/scan/regions/1").status_code)
        self.assertEqual([], self.client.get("/api/projects/scan/regions").json())

    def test_render_download_and_preview_pipeline_override(self) -> None:
        self.client.post("/api/projects", params={"project_id": "scan"}, files={"image": ("image.png", png(), "image/png")})
        self.client.post("/api/projects/scan/regions", json={"rectangle": {"x": 0.25, "y": 0.2, "width": 0.5, "height": 0.55}})
        download = self.client.get("/api/projects/scan/regions/1/render")
        self.assertEqual(200, download.status_code)
        self.assertEqual("image/png", download.headers["content-type"])
        self.assertIn("attachment", download.headers["content-disposition"])
        with Image.open(BytesIO(download.content)) as image:
            self.assertEqual((60, 50), image.size)
        preview = self.client.post("/api/projects/scan/regions/1/render", json={"operations": [{"kind": "rotate", "options": {"degrees": 90}}]})
        self.assertEqual(200, preview.status_code)
        self.assertNotIn("content-disposition", preview.headers)
        with Image.open(BytesIO(preview.content)) as image:
            self.assertEqual((50, 60), image.size)
        self.assertEqual(404, self.client.get("/api/projects/scan/regions/9/render").status_code)
        oversize = self.client.post("/api/projects/scan/regions/1/render", json={"operations": [{"kind": "trim", "options": {"top": 500, "right": 0, "bottom": 0, "left": 0}}]})
        self.assertEqual(422, oversize.status_code)

    def test_auto_straighten_and_trim_suggestions(self) -> None:
        source = Image.new("RGB", (160, 100), "white")
        ImageDraw.Draw(source).rectangle((40, 30, 119, 69), fill="black")
        source = source.rotate(6, fillcolor="white")
        output = BytesIO()
        source.save(output, "PNG")
        self.client.post("/api/projects", params={"project_id": "scan"}, files={"image": ("image.png", output.getvalue(), "image/png")})
        self.client.post("/api/projects/scan/regions", json={"rectangle": {"x": 0, "y": 0, "width": 1, "height": 1}})
        straighten = self.client.post("/api/projects/scan/regions/1/auto/straighten")
        self.assertEqual(200, straighten.status_code)
        self.assertIsInstance(straighten.json()["suggestion"], float)
        trim = self.client.post("/api/projects/scan/regions/1/auto/trim")
        self.assertEqual(200, trim.status_code)
        self.assertEqual({"kind", "options"}, set(trim.json()["suggestion"]))
        self.assertEqual("trim", trim.json()["suggestion"]["kind"])
        self.assertEqual({"top", "right", "bottom", "left"}, set(trim.json()["suggestion"]["options"]))
        self.assertEqual(404, self.client.post("/api/projects/scan/regions/9/auto/trim").status_code)

    def test_non_png_upload_rejected(self) -> None:
        response = self.client.post("/api/projects", params={"project_id": "scan"}, files={"image": ("image.jpg", b"\xff\xd8\xff\xe0", "image/jpeg")})
        self.assertEqual(422, response.status_code)
        self.assertEqual([], self.client.get("/api/projects").json())


if __name__ == "__main__":
    unittest.main()