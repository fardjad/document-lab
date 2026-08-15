import unittest

from application.view.usecases.render_view import ViewRenderError, RenderView
from model.operation import Operation
from model.pipeline import Pipeline
from model.project import ProjectId, ProjectImage, ProjectNotFound
from model.view import View, ProjectViews, ViewNotFound
from model.rendered_region import RenderedRegion


class FakeViewStore:
    def read_project_views(self, project_id: ProjectId) -> ProjectViews:
        return ProjectViews(2, (View(1, "x", Pipeline((Operation("rotate", {"degrees": 90}), Operation("straighten", {"angle": 1.5}), Operation("trim", {"top": 1})))),))


class FakeImageSizes:
    def read(self, raw_project_id: str) -> tuple[int, int]:
        return (100, 100)


class FakeReader:
    def read(self, raw_project_id: str) -> ProjectImage:
        return ProjectImage(b"source")


class FakeImageSizes:
    def read(self, raw_project_id: str) -> tuple[int, int]:
        return (100, 100)


class RecordingExecutor:
    kind = "recording"

    def __init__(self) -> None:
        self.render_calls = []
        self.validate_calls = []

    def validate(self, options: dict) -> dict:
        self.validate_calls.append(options)
        return options

    def render(self, view: RenderedRegion, options: dict) -> RenderedRegion:
        self.render_calls.append((view, options))
        return RenderedRegion(view.image + b"_" + str(options).encode(), view.width, view.height)


class FailingExecutor:
    kind = "failing"

    def validate(self, options: dict) -> dict:
        return options

    def render(self, view: RenderedRegion, options: dict) -> RenderedRegion:
        raise RuntimeError("boom")


class FakeRegistry:
    def __init__(self, executor) -> None:
        self._executor = executor

    def get(self, kind: str):
        return self._executor

    def kinds(self) -> tuple[str, ...]:
        return (self._executor.kind,)


class RenderViewTests(unittest.TestCase):
    def test_render_loads_view_and_applies_pipeline_operations(self) -> None:
        executor = RecordingExecutor()
        registry = FakeRegistry(executor)
        result = RenderView(FakeViewStore(), FakeReader(), FakeImageSizes(), registry).render("project", 1)
        self.assertEqual((100, 100), (executor.render_calls[0][0].width, executor.render_calls[0][0].height))
        # three operations: rotate, straighten, trim
        self.assertEqual(3, len(executor.render_calls))
        self.assertEqual(b"source_{'degrees': 90}_{'angle': 1.5}_{'top': 1}", result)

    def test_preview_renders_with_override_pipeline(self) -> None:
        executor = RecordingExecutor()
        registry = FakeRegistry(executor)
        override = Pipeline((Operation("remove_background", {"model": "u2net"}),))
        result = RenderView(FakeViewStore(), FakeReader(), FakeImageSizes(), registry).preview("project", 1, override)
        self.assertEqual(1, len(executor.render_calls))
        self.assertEqual({"model": "u2net"}, executor.render_calls[0][1])
        self.assertTrue(result.startswith(b"source"))

    def test_missing_view_and_project_are_reported(self) -> None:
        usecase = RenderView(FakeViewStore(), FakeReader(), FakeImageSizes(), FakeRegistry(RecordingExecutor()))
        with self.assertRaises(ViewNotFound):
            usecase.render("project", 9)
        with self.assertRaises(ProjectNotFound):
            usecase.render("../nope", 1)

    def test_render_failure_is_wrapped(self) -> None:
        with self.assertRaisesRegex(ViewRenderError, "Unable to render view"):
            RenderView(FakeViewStore(), FakeReader(), FakeImageSizes(), FakeRegistry(FailingExecutor())).render("project", 1)


if __name__ == "__main__":
    unittest.main()
