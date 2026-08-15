import unittest

from application.region.usecases.render_region import RegionRenderError, RenderRegion
from model.operation import Operation
from model.pipeline import Pipeline
from model.project import ProjectId, ProjectImage, ProjectNotFound
from model.region import CropRectangle, CropRegion, ProjectRegions, RegionNotFound
from model.rendered_region import RenderedRegion


class FakeRegionStore:
    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions:
        return ProjectRegions(2, (CropRegion(1, "x", CropRectangle(0, 0, 1, 1), Pipeline((Operation("rotate", {"degrees": 90}), Operation("straighten", {"angle": 1.5}), Operation("trim", {"top": 1})))),))


class FakeReader:
    def read(self, raw_project_id: str) -> ProjectImage:
        return ProjectImage(b"source")


class FakeCropper:
    def __init__(self) -> None:
        self.calls = []

    def crop(self, image: bytes, rectangle: CropRectangle) -> RenderedRegion:
        self.calls.append((image, rectangle))
        return RenderedRegion(image, 10, 10)


class RecordingExecutor:
    kind = "recording"

    def __init__(self) -> None:
        self.render_calls = []
        self.validate_calls = []

    def validate(self, options: dict) -> dict:
        self.validate_calls.append(options)
        return options

    def render(self, region: RenderedRegion, options: dict) -> RenderedRegion:
        self.render_calls.append((region, options))
        return RenderedRegion(region.image + b"_" + str(options).encode(), region.width, region.height)


class FailingExecutor:
    kind = "failing"

    def validate(self, options: dict) -> dict:
        return options

    def render(self, region: RenderedRegion, options: dict) -> RenderedRegion:
        raise RuntimeError("boom")


class FakeRegistry:
    def __init__(self, executor) -> None:
        self._executor = executor

    def get(self, kind: str):
        return self._executor

    def kinds(self) -> tuple[str, ...]:
        return (self._executor.kind,)


class RenderRegionTests(unittest.TestCase):
    def test_render_loads_region_crops_and_folds_operations(self) -> None:
        cropper = FakeCropper()
        executor = RecordingExecutor()
        registry = FakeRegistry(executor)
        result = RenderRegion(FakeRegionStore(), FakeReader(), cropper, registry).render("project", 1)
        self.assertEqual(b"source", cropper.calls[0][0])
        # three operations: rotate, straighten, trim
        self.assertEqual(3, len(executor.render_calls))
        self.assertEqual(b"source_{'degrees': 90}_{'angle': 1.5}_{'top': 1}", result)

    def test_preview_renders_with_override_pipeline(self) -> None:
        cropper = FakeCropper()
        executor = RecordingExecutor()
        registry = FakeRegistry(executor)
        override = Pipeline((Operation("remove_background", {"model": "u2net"}),))
        result = RenderRegion(FakeRegionStore(), FakeReader(), cropper, registry).preview("project", 1, override)
        self.assertEqual(1, len(executor.render_calls))
        self.assertEqual({"model": "u2net"}, executor.render_calls[0][1])
        self.assertTrue(result.startswith(b"source"))

    def test_missing_region_and_project_are_reported(self) -> None:
        usecase = RenderRegion(FakeRegionStore(), FakeReader(), FakeCropper(), FakeRegistry(RecordingExecutor()))
        with self.assertRaises(RegionNotFound):
            usecase.render("project", 9)
        with self.assertRaises(ProjectNotFound):
            usecase.render("../nope", 1)

    def test_render_failure_is_wrapped(self) -> None:
        with self.assertRaisesRegex(RegionRenderError, "Unable to render region"):
            RenderRegion(FakeRegionStore(), FakeReader(), FakeCropper(), FakeRegistry(FailingExecutor())).render("project", 1)


if __name__ == "__main__":
    unittest.main()