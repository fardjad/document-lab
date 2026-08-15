from pathlib import Path
import tempfile
import unittest

from infrastructure.file_store.filesystem_project_source import FilesystemProjectStore
from model.project import BackgroundRemoval, CropRectangle, CropRegion, ProjectId, ProjectRegions


class FilesystemRegionsTests(unittest.TestCase):
    def test_yaml_round_trip_and_missing_file_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            store = FilesystemProjectStore(root)
            self.assertEqual(ProjectRegions(1), store.read_project_regions(ProjectId("project")))
            value = ProjectRegions(2, (CropRegion(1, "Region 1", CropRectangle(1, 2, 3, 4)),))
            store.write_project_regions(ProjectId("project"), value)
            self.assertEqual(value, store.read_project_regions(ProjectId("project")))
            self.assertIn("version: 1", (project / "project.yaml").read_text())

    def test_malformed_yaml_does_not_get_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            metadata = project / "project.yaml"
            metadata.write_text("version: 9\n")
            with self.assertRaises(ValueError):
                FilesystemProjectStore(root).read_project_regions(ProjectId("project"))
            self.assertEqual("version: 9\n", metadata.read_text())

    def test_legacy_yaml_without_rotation_reads_as_zero_and_writes_rotation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            metadata = project / "project.yaml"
            metadata.write_text("version: 1\nnext_region_id: 2\nregions:\n- id: 1\n  name: Region 1\n  rectangle: {x: 0, y: 0, width: 1, height: 1}\n")
            store = FilesystemProjectStore(Path(directory))
            value = store.read_project_regions(ProjectId("project"))
            self.assertEqual(0, value.regions[0].rotation)
            store.write_project_regions(ProjectId("project"), value)
            self.assertIn("rotation: 0", metadata.read_text())
            self.assertIn("straighten: 0.0", metadata.read_text())


    def test_background_removal_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "project").mkdir()
            store = FilesystemProjectStore(root)
            removal = BackgroundRemoval(model="isnet-general-use", alpha_matting=True, alpha_matting_foreground_threshold=200, alpha_matting_background_threshold=20, alpha_matting_erode_size=15, post_process_mask=True)
            value = ProjectRegions(2, (CropRegion(1, "Region 1", CropRectangle(1, 2, 3, 4), background_removal=removal),))
            store.write_project_regions(ProjectId("project"), value)
            self.assertEqual(value, store.read_project_regions(ProjectId("project")))

    def test_legacy_yaml_without_background_removal_reads_as_none(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            (project / "project.yaml").write_text("version: 1\nnext_region_id: 2\nregions:\n- id: 1\n  name: Region 1\n  rectangle: {x: 0, y: 0, width: 1, height: 1}\n")
            value = FilesystemProjectStore(Path(directory)).read_project_regions(ProjectId("project"))
            self.assertIsNone(value.regions[0].background_removal)


if __name__ == "__main__":
    unittest.main()
