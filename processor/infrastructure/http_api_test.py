from io import BytesIO
from pathlib import Path
import tempfile
import unittest
import json
import re

import httpx

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from infrastructure.http_api import create_app
from application.view.usecases.invoke_helper import InvokeHelper
from application.project.usecases.create_project import CreateProject
from application.project.usecases.delete_project import DeleteProject
from application.project.usecases.list_projects import ListProjects
from application.project.usecases.read_project_image import ReadProjectImage
from application.project.usecases.read_project_image_size import ReadProjectImageSize
from application.project.usecases.update_project import UpdateProject
from application.project.usecases.rename_project import RenameProject
from application.view.usecases.delete_view import DeleteView
from application.view.usecases.list_views import ListViews
from application.view.usecases.create_view import CreateView
from application.view.usecases.update_view import UpdateView
from application.view.usecases.render_view import RenderView
from infrastructure.file_store.filesystem_project_source import FilesystemProjectStore
from infrastructure.image_processor.opencv_view_analyzer import OpenCVDocumentAnalyzer
from infrastructure.image_processor.operation_registry import OperationRegistryImpl
from config.extension_registry import ExtensionRegistryConfig
from infrastructure.image_processor.http_extension import HttpExtensionDiscovery


class PassthroughRemover:
    def remove(self, image: bytes, settings) -> bytes:
        return image


def extension_transport(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/health":
        return httpx.Response(200)
    if request.url.path == "/operations":
        operations = []
        for kind in ("crop", "rotate", "straighten", "trim", "remove_background"):
            helpers = []
            if kind in ("straighten", "trim"):
                helper = "auto_straighten" if kind == "straighten" else "auto_trim"
                helpers = [{"name": helper, "schema_url": f"/operations/{kind}/helpers/{helper}/schema.json", "invoke_url": f"/operations/{kind}/helpers/{helper}/invoke"}]
            operations.append({"kind": kind, "schema_url": f"/operations/{kind}/schema.json", "render_url": f"/operations/{kind}/render", "helpers": helpers})
        return httpx.Response(200, json={"operations": operations})
    if request.url.path.endswith("/helpers/auto_straighten/schema.json") or request.url.path.endswith("/helpers/auto_trim/schema.json"):
        return httpx.Response(200, json={"type": "object", "properties": {}, "required": [], "x-hint-require-image": True})
    if request.url.path.endswith("schema.json"):
        kind = request.url.path.split("/")[2]
        properties = {"degrees": {"type": "integer", "multipleOf": 90, "default": 0}} if kind == "rotate" else {"angle": {"type": "number", "default": 0.0}} if kind == "straighten" else {edge: {"type": "integer", "default": 0} for edge in ("top", "right", "bottom", "left")} if kind == "trim" else {"x": {"type": "number", "default": 0}, "y": {"type": "number", "default": 0}, "width": {"type": "number", "default": 1}, "height": {"type": "number", "default": 1}} if kind == "crop" else {"model": {"type": "string", "enum": ["birefnet-general", "u2net"], "default": "birefnet-general"}}
        return httpx.Response(200, json={"type": "object", "properties": properties, "required": list(properties), "x-hint-require-image": True})
    if request.url.path.endswith("/render"):
        match = re.search(rb'"options"\r?\n\r?\n(\{.*?\})', request.content, re.S)
        options = json.loads(match.group(1)) if match else {}
        width, height = 120, 90
        if request.url.path.endswith("/crop/render"):
            width, height = round(width * options.get("width", 1)), round(height * options.get("height", 1))
        if request.url.path.endswith("/rotate/render") and options.get("degrees", 0) % 180:
            width, height = 50, 60
        if request.url.path.endswith("/trim/render") and options.get("top", 0) >= 90:
            return httpx.Response(422, json={"detail": "Region trim removes entire output"})
        image = Image.new("RGBA", (width, height), "white")
        output = BytesIO()
        image.save(output, "PNG")
        return httpx.Response(200, content=output.getvalue(), headers={"content-type": "image/png", "x-image-width": str(width), "x-image-height": str(height)})
    if "/helpers/" in request.url.path:
        if request.url.path.endswith("auto_straighten/invoke"):
            return httpx.Response(200, json={"options": {"angle": 0.1}})
        return httpx.Response(200, json={"options": {"top": 0, "right": 0, "bottom": 0, "left": 0}})
    return httpx.Response(404)


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
        analyzer = OpenCVDocumentAnalyzer()
        registry_path = root / "extensions.yaml"
        registry_path.write_text("sources:\n  - discovery_url: http://extension.test/operations\n")
        discovery = HttpExtensionDiscovery(registry_path, httpx.Client(transport=httpx.MockTransport(extension_transport)))
        registry = OperationRegistryImpl(discovery.load())
        self.client = TestClient(create_app(ListProjects(store), reader, ["http://test"], CreateProject(store, store), UpdateProject(store, store), DeleteProject(store, store), ListViews(store), CreateView(store), UpdateView(store, registry), DeleteView(store), RenderView(store, reader, sizes, registry), InvokeHelper(store, reader, sizes, registry), registry, rename_project=RenameProject(store, store)))

    def test_reload_operations_replaces_registry_contents(self) -> None:
        reloaded = self.client.post("/api/operations/reload")
        self.assertEqual(501, reloaded.status_code)

    def test_project_lifecycle_end_to_end(self) -> None:
        created = self.client.post("/api/projects", files={"image": ("scan.png", png(), "image/png")})
        self.assertEqual(201, created.status_code)
        self.assertEqual(["scan"], self.client.get("/api/projects").json())
        self.assertEqual(png(), self.client.get("/api/projects/scan/image").content)
        duplicate = self.client.post("/api/projects", files={"image": ("scan.png", png(), "image/png")})
        self.assertEqual(422, duplicate.status_code)
        replaced = self.client.put("/api/projects/scan", files={"image": ("image.png", png(), "image/png")})
        self.assertEqual(204, replaced.status_code)
        missing = self.client.put("/api/projects/nope", files={"image": ("image.png", png(), "image/png")})
        self.assertEqual(404, missing.status_code)
        deleted = self.client.delete("/api/projects/scan")
        self.assertEqual(204, deleted.status_code)
        self.assertEqual([], self.client.get("/api/projects").json())
        self.assertEqual(404, self.client.delete("/api/projects/scan").status_code)

    def test_project_path_traversal_is_404(self) -> None:
        self.assertEqual(404, self.client.get("/api/projects/..%2Foutside/views").status_code)

    def test_project_rename_persists_display_name_without_changing_id(self) -> None:
        self.client.post("/api/projects", files={"image": ("scan.png", png(), "image/png")})
        response = self.client.put("/api/projects/scan/name", json={"name": "  Receipts  "})
        self.assertEqual(200, response.status_code)
        self.assertEqual({"id": "scan", "name": "Receipts"}, response.json())
        self.assertEqual([{"id": "scan", "name": "Receipts"}], self.client.get("/api/projects/details").json())
        self.assertEqual(422, self.client.put("/api/projects/scan/name", json={"name": "\n"}).status_code)

    def test_view_crud_with_pipeline_round_trip(self) -> None:
        self.client.post("/api/projects", files={"image": ("scan.png", png(), "image/png")})
        view = self.client.post("/api/projects/scan/views", json={"name": "Card"}).json()
        self.assertEqual(1, view["id"])
        self.assertEqual(PIPELINE, view["pipeline"])
        body = {"name": "Card", "pipeline": [{"kind": "rotate", "options": {"degrees": 90}}, {"kind": "straighten", "options": {"angle": 1.5}}, {"kind": "trim", "options": {"top": 2, "right": 0, "bottom": 1, "left": 0}}, {"kind": "remove_background", "options": {"model": "u2net", "alpha_matting": False, "alpha_matting_foreground_threshold": 240, "alpha_matting_background_threshold": 10, "alpha_matting_erode_size": 10, "post_process_mask": False}}]}
        updated = self.client.put("/api/projects/scan/views/1", json=body)
        self.assertEqual(200, updated.status_code)
        persisted = self.client.get("/api/projects/scan/views").json()[0]
        self.assertEqual(body["pipeline"], persisted["pipeline"])
        invalid = self.client.put("/api/projects/scan/views/1", json={"name": "Card", "pipeline": [{"kind": "rotate", "options": {"degrees": 45}}, {"kind": "trim", "options": {"top": 0, "right": 0, "bottom": 0, "left": 0}}]})
        self.assertEqual(422, invalid.status_code)
        extra = self.client.put("/api/projects/scan/views/1", json={"name": "Card", "pipeline": [{"kind": "rotate", "options": {"degrees": 90}, "unknown": True}]})
        self.assertEqual(422, extra.status_code)
        self.assertEqual(404, self.client.delete("/api/projects/scan/views/9").status_code)
        self.assertEqual(204, self.client.delete("/api/projects/scan/views/1").status_code)
        self.assertEqual([], self.client.get("/api/projects/scan/views").json())

    def test_render_download_and_preview_pipeline_override(self) -> None:
        self.client.post("/api/projects", files={"image": ("scan.png", png(), "image/png")})
        self.client.post("/api/projects/scan/views", json={"name": "Card"})
        download = self.client.get("/api/projects/scan/views/1/render")
        self.assertEqual(200, download.status_code)
        self.assertEqual("image/png", download.headers["content-type"])
        self.assertIn("attachment", download.headers["content-disposition"])
        with Image.open(BytesIO(download.content)) as image:
            self.assertEqual((120, 90), image.size)
        preview = self.client.post("/api/projects/scan/views/1/render", json={"pipeline": [{"kind": "crop", "options": {"x": 0, "y": 0, "width": 0.5, "height": 0.5555555555555556}}, {"kind": "rotate", "options": {"degrees": 90}}]})
        self.assertEqual(200, preview.status_code)
        self.assertNotIn("content-disposition", preview.headers)
        with Image.open(BytesIO(preview.content)) as image:
            self.assertEqual((50, 60), image.size)
        self.assertEqual(404, self.client.get("/api/projects/scan/views/9/render").status_code)
        oversize = self.client.post("/api/projects/scan/views/1/render", json={"pipeline": [{"kind": "trim", "options": {"top": 500, "right": 0, "bottom": 0, "left": 0}}]})
        self.assertEqual(422, oversize.status_code)

    def test_auto_straighten_and_trim_suggestions(self) -> None:
        catalog = {item["kind"]: item for item in self.client.get("/api/operations").json()}
        self.assertEqual(["birefnet-general", "u2net"], catalog["remove_background"]["schema"]["model"].get("enum"))
        self.assertEqual({"auto_straighten"}, {helper["name"] for helper in catalog["straighten"]["helpers"]})
        self.assertEqual({"auto_trim"}, {helper["name"] for helper in catalog["trim"]["helpers"]})
        self.assertEqual({}, catalog["trim"]["helpers"][0]["schema"])
        source = Image.new("RGB", (160, 100), "white")
        ImageDraw.Draw(source).rectangle((40, 30, 119, 69), fill="black")
        source = source.rotate(6, fillcolor="white")
        output = BytesIO()
        source.save(output, "PNG")
        self.client.post("/api/projects", files={"image": ("scan.png", output.getvalue(), "image/png")})
        self.client.post("/api/projects/scan/views", json={"name": "Card"})
        self.client.put("/api/projects/scan/views/1", json={"name": "Card", "pipeline": [{"kind": "straighten", "options": {"angle": 0}}, {"kind": "trim", "options": {"top": 0, "right": 0, "bottom": 0, "left": 0}}]})
        straighten = self.client.post("/api/projects/scan/views/1/pipeline/0/helpers/auto_straighten")
        self.assertEqual(200, straighten.status_code)
        self.assertIsInstance(straighten.json()["options"]["angle"], float)
        trim = self.client.post("/api/projects/scan/views/1/pipeline/1/helpers/auto_trim")
        self.assertEqual(200, trim.status_code)
        self.assertEqual({"top", "right", "bottom", "left"}, set(trim.json()["options"]))
        self.assertEqual(404, self.client.post("/api/projects/scan/views/9/pipeline/1/helpers/auto_trim").status_code)
        self.assertEqual(422, self.client.post("/api/projects/scan/views/1/pipeline/0/helpers/auto_trim").status_code)

    def test_non_png_upload_rejected(self) -> None:
        response = self.client.post("/api/projects", files={"image": ("scan.jpg", b"\xff\xd8\xff\xe0", "image/jpeg")})
        self.assertEqual(422, response.status_code)
        self.assertEqual([], self.client.get("/api/projects").json())


if __name__ == "__main__":
    unittest.main()
