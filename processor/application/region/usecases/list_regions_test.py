import unittest

from application.region.usecases.list_regions import ListRegions
from model.project import ProjectId, ProjectNotFound
from model.region import CropRectangle, CropRegion, ProjectRegions


class FakeRegionStore:
    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions:
        return ProjectRegions(2, (CropRegion(1, "Region 1", CropRectangle(0, 0, 1, 1)),))


class ListRegionsTests(unittest.TestCase):
    def test_lists_regions_of_project(self) -> None:
        regions = ListRegions(FakeRegionStore()).list("project")
        self.assertEqual((1,), tuple(item.id for item in regions.regions))

    def test_rejects_invalid_project_id(self) -> None:
        with self.assertRaises(ProjectNotFound):
            ListRegions(FakeRegionStore()).list("../nope")


if __name__ == "__main__":
    unittest.main()
