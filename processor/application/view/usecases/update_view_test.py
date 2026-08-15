import unittest

from application.view.usecases.update_view import UpdateView
from model.operation import Operation
from application.view.ports.operation_spec import OperationSpec
from model.pipeline import Pipeline
from model.project import ProjectId, ProjectNotFound
from model.project import Project, ProjectImage
from model.view import View, ViewNotFound


class FakeImageSizes:
    size = (100, 100)

    def read(self, raw_project_id: str) -> tuple[int, int]:
        return self.size


class FakeViewStore:
    def __init__(self) -> None:
        self.value = Project(ProjectId("project"), ProjectImage(b""), 2, (View(1, "Region 1"),))

    def read_project_views(self, project_id: ProjectId) -> Project:
        return self.value

    def write_project_views(self, project_id: ProjectId, views: Project) -> None:
        self.value = views


class AcceptingExecutor:
    kind = "accepting"

    def validate(self, options: dict) -> dict:
        return options

    def render(self, view, options: dict):
        return view


class FailingValidateExecutor:
    kind = "failing-validate"

    def validate(self, options: dict) -> dict:
        raise ValueError("Invalid option")

    def render(self, view, options: dict):
        return view


class FakeRegistry:
    def __init__(self, executor) -> None:
        self._executor = executor

    def get(self, kind: str):
        return self._executor

    def kinds(self) -> tuple[str, ...]:
        return (self._executor.kind,)

    def spec_for(self, kind: str):
        return OperationSpec(kind, {}, self._executor.validate)


class UpdateViewTests(unittest.TestCase):
    def test_persists_name_and_pipeline(self) -> None:
        store = FakeViewStore()
        pipeline = Pipeline((Operation("rotate", {"degrees": 90}), Operation("straighten", {"angle": 1.2}), Operation("trim", {"left": 1}), Operation("remove_background", {"model": "u2net"})))
        updated = UpdateView(store, FakeRegistry(AcceptingExecutor())).update("project", 1, "Renamed", pipeline)
        self.assertEqual(pipeline, updated.pipeline)
        self.assertEqual("Renamed", updated.name)
        self.assertEqual(updated, store.value.find_view(1))

    def test_strips_whitespace_from_name(self) -> None:
        store = FakeViewStore()
        updated = UpdateView(store, FakeRegistry(AcceptingExecutor())).update("project", 1, "  Renamed  ", Pipeline())
        self.assertEqual("Renamed", updated.name)

    def test_rejects_missing_view(self) -> None:
        with self.assertRaises(ViewNotFound):
            UpdateView(FakeViewStore(), FakeRegistry(AcceptingExecutor())).update("project", 9, "x", Pipeline())

    def test_rejects_invalid_project_id(self) -> None:
        with self.assertRaises(ProjectNotFound):
            UpdateView(FakeViewStore(), FakeRegistry(AcceptingExecutor())).update("../nope", 1, "x", Pipeline())

    def test_validates_operation_options_before_save(self) -> None:
        store = FakeViewStore()
        pipeline = Pipeline((Operation("rotate", {"degrees": 999}),))
        with self.assertRaisesRegex(ValueError, "Invalid option"):
            UpdateView(store, FakeRegistry(FailingValidateExecutor())).update("project", 1, "x", pipeline)
        self.assertEqual("Region 1", store.value.find_view(1).name)


if __name__ == "__main__":
    unittest.main()
