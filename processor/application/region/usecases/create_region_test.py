import unittest

from application.region.usecases.create_region import CreateRegion
from model.pipeline import Pipeline
from model.project import ProjectId, ProjectNotFound
from model.region import CropRectangle, CropRegion, ProjectRegions


class FakeImageSizes:
    size = (100, 100)

    def read(self, raw_project_id: str) -> tuple[int, int]:
        return self.size


class FakeRegionStore:
    def __init__(self) -> None:
        self.value = ProjectRegions(1)

    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions:
        return self.value

    def write_project_regions(self, project_id: ProjectId, regions: ProjectRegions) -> None:
        self.value = regions


class CreateRegionTests(unittest.TestCase):
    def test_creates_region_with_identity_pipeline_and_sequential_ids(self) -> None:
        store = FakeRegionStore()
        first = CreateRegion(store, FakeImageSizes()).create("project", CropRectangle(0, 0, 0.1, 0.2))
        second = CreateRegion(store, FakeImageSizes()).create("project", CropRectangle(0, 0, 0.5, 0.5))
        self.assertEqual((1, 2), (first.id, second.id))
        self.assertEqual("Region 2", second.name)
        self.assertEqual(Pipeline(), first.pipeline)

    def test_persists_created_region(self) -> None:
        store = FakeRegionStore()
        created = CreateRegion(store, FakeImageSizes()).create("project", CropRectangle(0, 0, 0.1, 0.2))
        self.assertEqual(created, store.value.find(created.id))

    def test_rejects_rectangle_outside_image(self) -> None:
        store = FakeRegionStore()
        with self.assertRaisesRegex(ValueError, "^Crop rectangle outside image$"):
            CreateRegion(store, FakeImageSizes()).create("project", CropRectangle(0.5, 0, 0.6, 0.5))
        self.assertEqual(ProjectRegions(1), store.value)

    def test_rejects_invalid_project_id(self) -> None:
        with self.assertRaises(ProjectNotFound):
            CreateRegion(FakeRegionStore(), FakeImageSizes()).create("../nope", CropRectangle(0, 0, 1, 1))


if __name__ == "__main__":
    unittest.main()