import unittest

from application.auto_processing.usecases.auto_trim_view import AutoTrimView
from application.auto_processing.results import AutoProcessingResult
from model.operation import Operation
from model.pipeline import Pipeline
from model.project import ProjectId, ProjectImage, ProjectNotFound
from model.view import View, ProjectViews, ViewNotFound
from model.rendered_region import RenderedRegion


class FakeViewStore:
    def read_project_views(self, project_id: ProjectId) -> ProjectViews:
        return ProjectViews(2, (View(1, "r", Pipeline((Operation("rotate", {"degrees": 90}), Operation("trim", {"left": 2})))),))


class FakeImageSizes:
    def read(self, raw_project_id: str) -> tuple[int, int]:
        return (100, 100)


class FakeReader:
    def read(self, raw_project_id: str) -> ProjectImage:
        return ProjectImage(b"unchanged")


class PassThroughExecutor:
    kind = "passthrough"

    def validate(self, options: dict) -> dict:
        return options

    def render(self, view: RenderedRegion, options: dict) -> RenderedRegion:
        return view


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


class AutoTrimViewTests(unittest.TestCase):
    def test_returns_suggestion_without_persisting(self) -> None:
        trimmer = FakeTrimmer()
        result = AutoTrimView(FakeViewStore(), FakeReader(), FakeImageSizes(), FakeRegistry(PassThroughExecutor()), trimmer).suggest("project", 1)
        self.assertEqual(Operation("trim", {"left": 1}), result.suggestion)
        self.assertEqual(b"unchanged", trimmer.calls[0])

    def test_rejects_missing_view(self) -> None:
        with self.assertRaises(ViewNotFound):
            AutoTrimView(FakeViewStore(), FakeReader(), FakeImageSizes(), FakeRegistry(PassThroughExecutor()), FakeTrimmer()).suggest("project", 9)

    def test_rejects_invalid_project_id(self) -> None:
        with self.assertRaises(ProjectNotFound):
            AutoTrimView(FakeViewStore(), FakeReader(), FakeImageSizes(), FakeRegistry(PassThroughExecutor()), FakeTrimmer()).suggest("../nope", 1)


if __name__ == "__main__":
    unittest.main()