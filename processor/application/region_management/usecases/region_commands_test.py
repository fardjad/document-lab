import unittest

from application.region_management.usecases.region_commands import RegionCommands
from model.project import CropRectangle, CropRegion, ProjectId, ProjectRegions, RegionTrim


class FakeStore:
    def __init__(self) -> None:
        self.value = ProjectRegions(1)
        self.image_size: tuple[int, int] = (100, 100)

    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions:
        return self.value

    def write_project_regions(self, project_id: ProjectId, regions: ProjectRegions) -> None:
        self.value = regions

    def read_project_image_size(self, project_id: ProjectId) -> tuple[int, int]:
        return self.image_size


class RegionCommandsTests(unittest.TestCase):
    def test_create_update_delete_allocates_nonreused_ids(self) -> None:
        store = FakeStore()
        commands = RegionCommands(store)
        rectangle = CropRectangle(0, 0, 0.1, 0.2)
        first = commands.create_region("project", rectangle)
        updated = commands.update_region("project", first.id, "Renamed", rectangle, 90, 1.2, RegionTrim(left=1))
        self.assertEqual(1.2, updated.straighten)
        self.assertEqual(1, updated.trim.left)
        commands.delete_region("project", first.id)
        second = commands.create_region("project", rectangle)
        self.assertEqual((1, 2), (first.id, second.id))
        self.assertEqual("Region 2", second.name)

    def test_rejects_trim_that_empties_transformed_output(self) -> None:
        store = FakeStore()
        store.image_size = (1, 1)
        commands = RegionCommands(store)
        commands.create_region("project", CropRectangle(0, 0, 1, 1))
        with self.assertRaisesRegex(ValueError, "^Region trim removes entire output$"):
            commands.update_region("project", 1, "Empty", CropRectangle(0, 0, 1, 1), 0, 0.0, RegionTrim(top=1))

    def test_accepts_normalized_rectangle_with_trim_after_combined_transform(self) -> None:
        store = FakeStore()
        store.image_size = (1200, 800)
        commands = RegionCommands(store)
        commands.create_region("project", CropRectangle(0, 0, 0.35, 0.325))
        updated = commands.update_region("project", 1, "Trimmed", CropRectangle(0, 0, 0.35, 0.325), 90, 12.3, RegionTrim(top=1))
        self.assertEqual(1, updated.trim.top)


if __name__ == "__main__":
    unittest.main()
