import unittest

from application.region_export.usecases.export_region import RegionExport
from model.project import CropRectangle, CropRegion, ProjectId, ProjectImage, ProjectRegions, RegionNotFound


class Source:
    def read_project_image(self, project_id: ProjectId) -> ProjectImage:
        return ProjectImage(b"source")


class Store:
    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions:
        return ProjectRegions(2, (CropRegion(1, "x", CropRectangle(0, 0, 1, 1)),))


class Renderer:
    def render(self, image: ProjectImage, crop: CropRegion) -> bytes:
        return image.data + bytes([crop.id])


class RegionExportTests(unittest.TestCase):
    def test_loads_selected_region_and_delegates_render(self) -> None:
        self.assertEqual(b"source\x01", RegionExport(Source(), Store(), Renderer()).export("project", 1))

    def test_missing_region_is_reported(self) -> None:
        with self.assertRaisesRegex(RegionNotFound, "^Region not found$"):
            RegionExport(Source(), Store(), Renderer()).export("project", 2)


if __name__ == "__main__":
    unittest.main()
