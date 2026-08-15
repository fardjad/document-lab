import unittest

from application.auto_processing.usecases.auto_straighten_region import AutoStraightenRegion
from application.auto_processing.results import AutoProcessingResult
from model.operation import Operation
from model.pipeline import Pipeline
from model.project import ProjectId, ProjectImage, ProjectNotFound
from model.region import CropRectangle, CropRegion, ProjectRegions, RegionNotFound
from model.rendered_region import RenderedRegion


class FakeRegionStore:
    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions:
        return ProjectRegions(2, (CropRegion(1, "r", CropRectangle(0, 0, 1, 1), Pipeline((Operation("straighten", {"angle": 1.0}), Operation("trim", {"left": 2}), Operation("rotate", {"degrees": 90})))),))


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


class FakeStraightener:
    def __init__(self) -> None:
        self.calls = []

    def detect_skew(self, rendered: bytes) -> AutoProcessingResult:
        self.calls.append(rendered)
        return AutoProcessingResult(2.0, 0.8, "test")


class AutoStraightenRegionTests(unittest.TestCase):
    def test_returns_suggestion_without_persisting(self) -> None:
        straightener = FakeStraightener()
        result = AutoStraightenRegion(FakeRegionStore(), FakeReader(), FakeCropper(), FakeRegistry(PassThroughExecutor()), straightener).suggest("project", 1)
        self.assertEqual(2.0, result.suggestion)
        # straighten and trim are removed before rendering, so only rotate remains
        self.assertEqual(b"unchanged", straightener.calls[0])

    def test_rejects_missing_region(self) -> None:
        with self.assertRaises(RegionNotFound):
            AutoStraightenRegion(FakeRegionStore(), FakeReader(), FakeCropper(), FakeRegistry(PassThroughExecutor()), FakeStraightener()).suggest("project", 9)

    def test_rejects_invalid_project_id(self) -> None:
        with self.assertRaises(ProjectNotFound):
            AutoStraightenRegion(FakeRegionStore(), FakeReader(), FakeCropper(), FakeRegistry(PassThroughExecutor()), FakeStraightener()).suggest("../nope", 1)


if __name__ == "__main__":
    unittest.main()