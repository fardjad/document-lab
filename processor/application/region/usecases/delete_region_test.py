import unittest

from application.region.usecases.delete_region import DeleteRegion
from model.project import ProjectId, ProjectNotFound
from model.region import CropRectangle, CropRegion, ProjectRegions, RegionNotFound


class FakeRegionStore:
    def __init__(self) -> None:
        self.value = ProjectRegions(3, (CropRegion(1, "Region 1", CropRectangle(0, 0, 1, 1)), CropRegion(2, "Region 2", CropRectangle(0, 0, 1, 1))))

    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions:
        return self.value

    def write_project_regions(self, project_id: ProjectId, regions: ProjectRegions) -> None:
        self.value = regions


class DeleteRegionTests(unittest.TestCase):
    def test_removes_region_and_keeps_next_id(self) -> None:
        store = FakeRegionStore()
        DeleteRegion(store).delete("project", 1)
        self.assertEqual((2,), tuple(item.id for item in store.value.regions))
        self.assertEqual(3, store.value.next_region_id)

    def test_rejects_missing_region(self) -> None:
        with self.assertRaises(RegionNotFound):
            DeleteRegion(FakeRegionStore()).delete("project", 9)

    def test_rejects_invalid_project_id(self) -> None:
        with self.assertRaises(ProjectNotFound):
            DeleteRegion(FakeRegionStore()).delete("../nope", 1)


if __name__ == "__main__":
    unittest.main()
