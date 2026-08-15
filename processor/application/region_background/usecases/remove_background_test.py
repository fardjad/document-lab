import unittest

from application.region_background.usecases.remove_background import BackgroundRemovalError, RegionBackgroundRemoval
from model.project import BackgroundRemoval, CropRectangle, CropRegion, ProjectId, ProjectImage, ProjectRegions, ProjectNotFound, RegionNotFound


class Source:
    def read_project_image(self, project_id: ProjectId) -> ProjectImage:
        return ProjectImage(b"source")


class Store:
    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions:
        return ProjectRegions(2, (CropRegion(1, "Region 1", CropRectangle(0, 0, 1, 1)),))


class Renderer:
    def render(self, image: ProjectImage, crop: CropRegion) -> bytes:
        return image.data + bytes([crop.id])


class Remover:
    def __init__(self, failing: bool = False) -> None:
        self.calls = []
        self.failing = failing

    def remove(self, image: bytes, settings: BackgroundRemoval) -> bytes:
        self.calls.append((image, settings))
        if self.failing:
            raise RuntimeError("boom")
        return b"clean-" + image


class RegionBackgroundRemovalTests(unittest.TestCase):
    def test_renders_region_then_applies_settings(self) -> None:
        remover = Remover()
        settings = BackgroundRemoval(model="u2net")
        result = RegionBackgroundRemoval(Source(), Store(), Renderer(), remover).preview("project", 1, settings)
        self.assertEqual(b"clean-source\x01", result)
        self.assertEqual([(b"source\x01", settings)], remover.calls)

    def test_missing_region_is_reported(self) -> None:
        with self.assertRaises(RegionNotFound):
            RegionBackgroundRemoval(Source(), Store(), Renderer(), Remover()).preview("project", 9, BackgroundRemoval())

    def test_invalid_project_id_is_reported(self) -> None:
        with self.assertRaises(ProjectNotFound):
            RegionBackgroundRemoval(Source(), Store(), Renderer(), Remover()).preview("../nope", 1, BackgroundRemoval())

    def test_removal_failure_is_wrapped(self) -> None:
        with self.assertRaisesRegex(BackgroundRemovalError, "Unable to remove background"):
            RegionBackgroundRemoval(Source(), Store(), Renderer(), Remover(failing=True)).preview("project", 1, BackgroundRemoval())


if __name__ == "__main__":
    unittest.main()
