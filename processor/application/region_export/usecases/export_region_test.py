import unittest

from application.region_export.usecases.export_region import RegionExport
from model.project import BackgroundRemoval, CropRectangle, CropRegion, ProjectId, ProjectImage, ProjectRegions, RegionNotFound


class Source:
    def read_project_image(self, project_id: ProjectId) -> ProjectImage:
        return ProjectImage(b"source")


class Store:
    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions:
        return ProjectRegions(2, (CropRegion(1, "x", CropRectangle(0, 0, 1, 1)),))


class Renderer:
    def render(self, image: ProjectImage, crop: CropRegion) -> bytes:
        return image.data + bytes([crop.id])


class StoreWithRemoval:
    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions:
        return ProjectRegions(2, (CropRegion(1, "x", CropRectangle(0, 0, 1, 1), background_removal=BackgroundRemoval(model="u2net")),))


class Remover:
    def __init__(self) -> None:
        self.calls = []

    def remove(self, image: bytes, settings: BackgroundRemoval) -> bytes:
        self.calls.append(settings.model)
        return b"clean-" + image


class RegionExportTests(unittest.TestCase):
    def test_loads_selected_region_and_delegates_render(self) -> None:
        self.assertEqual(b"source\x01", RegionExport(Source(), Store(), Renderer()).export("project", 1))

    def test_missing_region_is_reported(self) -> None:
        with self.assertRaisesRegex(RegionNotFound, "^Region not found$"):
            RegionExport(Source(), Store(), Renderer()).export("project", 2)

    def test_applies_persisted_background_removal_after_render(self) -> None:
        remover = Remover()
        self.assertEqual(b"clean-source\x01", RegionExport(Source(), StoreWithRemoval(), Renderer(), remover).export("project", 1))
        self.assertEqual(["u2net"], remover.calls)

    def test_without_persisted_background_removal_renders_unchanged(self) -> None:
        remover = Remover()
        self.assertEqual(b"source\x01", RegionExport(Source(), Store(), Renderer(), remover).export("project", 1))
        self.assertEqual([], remover.calls)


if __name__ == "__main__":
    unittest.main()
