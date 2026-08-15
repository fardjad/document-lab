from pathlib import Path
import tempfile
import unittest

from infrastructure.file_store.filesystem_project_source import FilesystemProjectStore
from model.operation import Operation
from model.pipeline import Pipeline
from model.project import ProjectId, ProjectImage, ProjectNotFound
from model.region import CropRectangle, CropRegion, ProjectRegions

PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + b"\x00\x00\x00\x01\x00\x00\x00\x01" + b"\x08\x06\x00\x00\x00"


class FilesystemRegionsTests(unittest.TestCase):
    def _project(self, root: Path) -> Path:
        project = root / "project"
        project.mkdir()
        return project

    def test_yaml_round_trip_and_missing_file_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            store = FilesystemProjectStore(root)
            self.assertEqual(ProjectRegions(1), store.read_project_regions(ProjectId("project")))
            pipeline = Pipeline((Operation("rotate", {"degrees": 90}), Operation("straighten", {"angle": 1.5}), Operation("trim", {"top": 2, "right": 0, "bottom": 0, "left": 3}), Operation("remove_background", {"model": "u2net"})))
            value = ProjectRegions(2, (CropRegion(1, "Region 1", CropRectangle(1, 2, 3, 4), pipeline),))
            store.write_project_regions(ProjectId("project"), value)
            self.assertEqual(value, store.read_project_regions(ProjectId("project")))
            text = (root / "project" / "project.yaml").read_text()
            self.assertIn("version: 3", text)
            self.assertIn("pipeline:", text)

    def test_empty_pipeline_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            store = FilesystemProjectStore(root)
            value = ProjectRegions(2, (CropRegion(1, "Region 1", CropRectangle(0, 0, 1, 1), Pipeline()),))
            store.write_project_regions(ProjectId("project"), value)
            self.assertEqual(value, store.read_project_regions(ProjectId("project")))

    def test_malformed_yaml_does_not_get_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = self._project(root)
            metadata = project / "project.yaml"
            metadata.write_text("version: 9\n")
            with self.assertRaises(ValueError):
                FilesystemProjectStore(root).read_project_regions(ProjectId("project"))
            self.assertEqual("version: 9\n", metadata.read_text())

    def test_v2_yaml_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            (project / "project.yaml").write_text("version: 2\nnext_region_id: 2\nregions:\n- id: 1\n  name: Region 1\n  pipeline: {rotate: {degrees: 90}}\n  rectangle: {x: 0, y: 0, width: 1, height: 1}\n")
            with self.assertRaises(ValueError):
                FilesystemProjectStore(Path(directory)).read_project_regions(ProjectId("project"))

    def test_v1_yaml_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            (project / "project.yaml").write_text("version: 1\nnext_region_id: 2\nregions:\n- id: 1\n  name: Region 1\n  rotation: 90\n  rectangle: {x: 0, y: 0, width: 1, height: 1}\n")
            with self.assertRaises(ValueError):
                FilesystemProjectStore(Path(directory)).read_project_regions(ProjectId("project"))

    def test_pipeline_with_extra_keys_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            (project / "project.yaml").write_text("version: 3\nnext_region_id: 2\nregions:\n- id: 1\n  name: Region 1\n  pipeline:\n    - kind: rotate\n      options: {degrees: 90}\n      unknown: {}\n  rectangle: {x: 0, y: 0, width: 1, height: 1}\n")
            with self.assertRaises(ValueError):
                FilesystemProjectStore(Path(directory)).read_project_regions(ProjectId("project"))


class FilesystemProjectWriterTests(unittest.TestCase):
    def test_create_and_delete_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = FilesystemProjectStore(root)
            store.create_project(ProjectId("fresh"), ProjectImage(PNG_HEADER))
            self.assertEqual([ProjectId("fresh")], store.list_project_ids())
            self.assertEqual(PNG_HEADER, (root / "fresh" / "image.png").read_bytes())
            store.delete_project(ProjectId("fresh"))
            self.assertEqual([], store.list_project_ids())
            with self.assertRaises(ProjectNotFound):
                store.delete_project(ProjectId("fresh"))

    def test_create_rejects_existing_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = FilesystemProjectStore(root)
            store.create_project(ProjectId("fresh"), ProjectImage(PNG_HEADER))
            with self.assertRaises(FileExistsError):
                store.create_project(ProjectId("fresh"), ProjectImage(PNG_HEADER))

    def test_replace_image_resets_regions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = FilesystemProjectStore(root)
            store.create_project(ProjectId("p"), ProjectImage(PNG_HEADER))
            store.write_project_regions(ProjectId("p"), ProjectRegions(2, (CropRegion(1, "R", CropRectangle(0, 0, 1, 1)),)))
            store.replace_project_image(ProjectId("p"), ProjectImage(PNG_HEADER + b"more"))
            self.assertEqual(ProjectRegions(1), store.read_project_regions(ProjectId("p")))
            self.assertEqual(PNG_HEADER + b"more", (root / "p" / "image.png").read_bytes())


if __name__ == "__main__":
    unittest.main()