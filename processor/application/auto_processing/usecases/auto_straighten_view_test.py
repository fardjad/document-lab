import unittest

from application.auto_processing.usecases.auto_straighten_view import AutoStraightenView
from application.auto_processing.results import AutoProcessingResult
from model.operation import Operation
from model.pipeline import Pipeline
from model.project import ProjectId, ProjectImage, ProjectNotFound
from model.view import View, ProjectViews, ViewNotFound
from model.rendered_region import RenderedRegion


class FakeViewStore:
    def read_project_views(self, project_id: ProjectId) -> ProjectViews:
        return ProjectViews(2, (View(1, "r", Pipeline((Operation("straighten", {"angle": 1.0}), Operation("trim", {"left": 2}), Operation("rotate", {"degrees": 90})))),))


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


class FakeStraightener:
    def __init__(self) -> None:
        self.calls = []

    def detect_skew(self, rendered: bytes) -> AutoProcessingResult:
        self.calls.append(rendered)
        return AutoProcessingResult(2.0, 0.8, "test")


class AutoStraightenViewTests(unittest.TestCase):
    def test_returns_suggestion_without_persisting(self) -> None:
        straightener = FakeStraightener()
        result = AutoStraightenView(FakeViewStore(), FakeReader(), FakeImageSizes(), FakeRegistry(PassThroughExecutor()), straightener).suggest("project", 1)
        self.assertEqual(2.0, result.suggestion)
        # straighten and trim are removed before rendering, so only rotate remains
        self.assertEqual(b"unchanged", straightener.calls[0])

    def test_rejects_missing_view(self) -> None:
        with self.assertRaises(ViewNotFound):
            AutoStraightenView(FakeViewStore(), FakeReader(), FakeImageSizes(), FakeRegistry(PassThroughExecutor()), FakeStraightener()).suggest("project", 9)

    def test_rejects_invalid_project_id(self) -> None:
        with self.assertRaises(ProjectNotFound):
            AutoStraightenView(FakeViewStore(), FakeReader(), FakeImageSizes(), FakeRegistry(PassThroughExecutor()), FakeStraightener()).suggest("../nope", 1)


if __name__ == "__main__":
    unittest.main()