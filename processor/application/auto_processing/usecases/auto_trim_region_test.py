import unittest

from application.auto_processing.usecases.auto_trim_region import AutoTrimRegion
from application.auto_processing.results import AutoProcessingResult
from model.operation import Operation
from model.pipeline import Pipeline
from model.project import ProjectId, ProjectImage, ProjectNotFound
from model.region import CropRectangle, CropRegion, ProjectRegions, RegionNotFound
from model.rendered_region import RenderedRegion


class FakeRegionStore:
    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions:
        return ProjectRegions(2, (CropRegion(1, "r", CropRectangle(0, 0, 1, 1), Pipeline((Operation("rotate", {"degrees": 90}), Operation("trim", {"left": 2})))),))


class FakeReader:
    def read(self, raw_project_id: str) -> ProjectImage:
        return ProjectImage(b"unchanged")


class FakeCropper:
    def crop(self, image: bytes, rectangle: CropRectangle) -> RenderedRegion:
        return RenderedRegion(image, 10, 10)


class PassThroughExecutor:
    kind = "passthrough"

    def validate(self, options: dict) -> dict:
        return options

    def render(self, region: RenderedRegion, options: dict) -> RenderedRegion:
        return region


class FakeRegistry:
    def __init__(self, executor) -> None:
        self._executor = executor

    def get(self, kind: str):
        return self._executor

    def kinds(self) -> tuple[str, ...]:
        return (self._executor.kind,)


class FakeTrimmer:
    def __init__(self) -> None:
        self.calls = []

    def detect_trim(self, rendered: bytes) -> AutoProcessingResult:
        self.calls.append(rendered)
        return AutoProcessingResult(Operation("trim", {"left": 1}), 0.8, "test")


class AutoTrimRegionTests(unittest.TestCase):
    def test_returns_suggestion_without_persisting(self) -> None:
        trimmer = FakeTrimmer()
        result = AutoTrimRegion(FakeRegionStore(), FakeReader(), FakeCropper(), FakeRegistry(PassThroughExecutor()), trimmer).suggest("project", 1)
        self.assertEqual(Operation("trim", {"left": 1}), result.suggestion)
        self.assertEqual(b"unchanged", trimmer.calls[0])

    def test_rejects_missing_region(self) -> None:
        with self.assertRaises(RegionNotFound):
            AutoTrimRegion(FakeRegionStore(), FakeReader(), FakeCropper(), FakeRegistry(PassThroughExecutor()), FakeTrimmer()).suggest("project", 9)

    def test_rejects_invalid_project_id(self) -> None:
        with self.assertRaises(ProjectNotFound):
            AutoTrimRegion(FakeRegionStore(), FakeReader(), FakeCropper(), FakeRegistry(PassThroughExecutor()), FakeTrimmer()).suggest("../nope", 1)


if __name__ == "__main__":
    unittest.main()