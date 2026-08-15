import unittest

from application.region.usecases.update_region import UpdateRegion
from model.operation import Operation
from model.pipeline import Pipeline
from model.project import ProjectId, ProjectNotFound
from model.region import CropRectangle, CropRegion, ProjectRegions, RegionNotFound


class FakeImageSizes:
    size = (100, 100)

    def read(self, raw_project_id: str) -> tuple[int, int]:
        return self.size


class FakeRegionStore:
    def __init__(self) -> None:
        self.value = ProjectRegions(2, (CropRegion(1, "Region 1", CropRectangle(0, 0, 0.1, 0.2)),))

    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions:
        return self.value

    def write_project_regions(self, project_id: ProjectId, regions: ProjectRegions) -> None:
        self.value = regions


class AcceptingExecutor:
    kind = "accepting"

    def validate(self, options: dict) -> dict:
        return options

    def render(self, region, options: dict):
        return region


class FailingValidateExecutor:
    kind = "failing-validate"

    def validate(self, options: dict) -> dict:
        raise ValueError("Invalid option")

    def render(self, region, options: dict):
        return region


class FakeRegistry:
    def __init__(self, executor) -> None:
        self._executor = executor

    def get(self, kind: str):
        return self._executor

    def kinds(self) -> tuple[str, ...]:
        return (self._executor.kind,)


class UpdateRegionTests(unittest.TestCase):
    def test_persists_name_rectangle_and_pipeline(self) -> None:
        store = FakeRegionStore()
        pipeline = Pipeline((Operation("rotate", {"degrees": 90}), Operation("straighten", {"angle": 1.2}), Operation("trim", {"left": 1}), Operation("remove_background", {"model": "u2net"})))
        updated = UpdateRegion(store, FakeImageSizes(), FakeRegistry(AcceptingExecutor())).update("project", 1, "Renamed", CropRectangle(0, 0, 0.1, 0.2), pipeline)
        self.assertEqual(pipeline, updated.pipeline)
        self.assertEqual("Renamed", updated.name)
        self.assertEqual(updated, store.value.find(1))

    def test_strips_whitespace_from_name(self) -> None:
        store = FakeRegionStore()
        updated = UpdateRegion(store, FakeImageSizes(), FakeRegistry(AcceptingExecutor())).update("project", 1, "  Renamed  ", CropRectangle(0, 0, 0.1, 0.2), Pipeline())
        self.assertEqual("Renamed", updated.name)

    def test_rejects_rectangle_outside_image(self) -> None:
        with self.assertRaisesRegex(ValueError, "^Crop rectangle outside image$"):
            UpdateRegion(FakeRegionStore(), FakeImageSizes(), FakeRegistry(AcceptingExecutor())).update("project", 1, "Outside", CropRectangle(0, 0, 1.5, 1), Pipeline())

    def test_rejects_missing_region(self) -> None:
        with self.assertRaises(RegionNotFound):
            UpdateRegion(FakeRegionStore(), FakeImageSizes(), FakeRegistry(AcceptingExecutor())).update("project", 9, "x", CropRectangle(0, 0, 1, 1), Pipeline())

    def test_rejects_invalid_project_id(self) -> None:
        with self.assertRaises(ProjectNotFound):
            UpdateRegion(FakeRegionStore(), FakeImageSizes(), FakeRegistry(AcceptingExecutor())).update("../nope", 1, "x", CropRectangle(0, 0, 1, 1), Pipeline())

    def test_validates_operation_options_before_save(self) -> None:
        store = FakeRegionStore()
        pipeline = Pipeline((Operation("rotate", {"degrees": 999}),))
        with self.assertRaisesRegex(ValueError, "Invalid option"):
            UpdateRegion(store, FakeImageSizes(), FakeRegistry(FailingValidateExecutor())).update("project", 1, "x", CropRectangle(0, 0, 0.1, 0.2), pipeline)
        self.assertEqual("Region 1", store.value.find(1).name)


if __name__ == "__main__":
    unittest.main()