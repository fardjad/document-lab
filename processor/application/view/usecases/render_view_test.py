import unittest

from application.view.usecases.render_view import ViewRenderError, RenderView, cache_key_for_step
from model.operation import Operation
from model.pipeline import Pipeline
from model.project import ProjectId, ProjectImage, ProjectNotFound
from model.project import Project, ProjectImage
from model.view import View, ViewNotFound
from application.view.ports.rendered_region import RenderedRegion


class FakeViewStore:
    def read_project_views(self, project_id: ProjectId) -> Project:
        return Project(ProjectId("project"), ProjectImage(b""), 2, (View(1, "x", Pipeline((Operation("rotate", {"degrees": 90}), Operation("straighten", {"angle": 1.5}), Operation("trim", {"top": 1})))),))


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


class RecordingCache:
    def __init__(self) -> None:
        self.get_calls = []
        self.put_calls = []
        self.values = {}

    def get(self, project_id: ProjectId, cache_key: str):
        self.get_calls.append((project_id, cache_key))
        return self.values.get((project_id, cache_key))

    def put(self, project_id: ProjectId, cache_key: str, rendered: RenderedRegion) -> None:
        self.put_calls.append((project_id, cache_key, rendered))
        self.values[(project_id, cache_key)] = rendered

    def cleanup(self, project_id: ProjectId) -> None:
        pass


class RenderViewTests(unittest.TestCase):
    def test_cache_key_is_stable_for_same_operations(self) -> None:
        operations = (Operation("rotate", {"degrees": 90}),)
        self.assertEqual(cache_key_for_step(operations, 0), cache_key_for_step(operations, 0))

    def test_cache_key_changes_when_options_change(self) -> None:
        first = (Operation("rotate", {"degrees": 90}),)
        second = (Operation("rotate", {"degrees": 180}),)
        self.assertNotEqual(cache_key_for_step(first, 0), cache_key_for_step(second, 0))

    def test_cache_key_excludes_disabled_operations(self) -> None:
        with_disabled = (Operation("rotate", {"degrees": 90}, False), Operation("trim", {"top": 1}))
        without_disabled = (Operation("trim", {"top": 1}),)
        self.assertEqual(cache_key_for_step(with_disabled, 1), cache_key_for_step(without_disabled, 0))

    def test_cache_key_changes_for_later_pipeline_step(self) -> None:
        operations = (Operation("rotate", {"degrees": 90}), Operation("trim", {"top": 1}))
        self.assertNotEqual(cache_key_for_step(operations, 0), cache_key_for_step(operations, 1))

    def test_render_checks_cache_for_each_step_and_reuses_hits(self) -> None:
        executor = RecordingExecutor()
        cache = RecordingCache()
        usecase = RenderView(FakeViewStore(), FakeReader(), FakeImageSizes(), FakeRegistry(executor), cache)

        first = usecase.render("project", 1)
        self.assertEqual(3, len(cache.get_calls))
        self.assertEqual(3, len(cache.put_calls))
        self.assertEqual(3, len(executor.render_calls))

        second = usecase.render("project", 1)
        self.assertEqual(first, second)
        self.assertEqual(6, len(cache.get_calls))
        self.assertEqual(3, len(cache.put_calls))
        self.assertEqual(3, len(executor.render_calls))

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

    def test_render_skips_disabled_operations(self) -> None:
        executor = RecordingExecutor()
        registry = FakeRegistry(executor)
        view_store = FakeViewStore()
        view_store.read_project_views = lambda project_id: Project(
            ProjectId("project"),
            ProjectImage(b""),
            2,
            (View(1, "x", Pipeline((Operation("rotate", {"degrees": 90}, False), Operation("trim", {"top": 1})))),),
        )
        result = RenderView(view_store, FakeReader(), FakeImageSizes(), registry).render("project", 1)
        self.assertEqual(1, len(executor.render_calls))
        self.assertEqual(b"source_{'top': 1}", result)

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
