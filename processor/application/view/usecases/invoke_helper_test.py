import unittest

from application.view.usecases.invoke_helper import InvokeHelper
from application.view.ports.helper import Helper
from application.view.ports.operation_spec import OperationSpec
from application.view.ports.rendered_region import RenderedRegion
from application.view.usecases.render_view import cache_key_for_step
from model.pipeline import Pipeline
from model.project import Project, ProjectId, ProjectImage, ProjectNotFound
from model.operation import Operation
from model.view import View, ViewNotFound


class FakeStore:
    def read_project_views(self, project_id):
        return Project(ProjectId("project"), ProjectImage(b""), 2, (View(1, "view", Pipeline((Operation("rotate", {"degrees": 90}), Operation("trim", {"left": 2})))),))


class FakeReader:
    def read(self, project_id):
        return ProjectImage(b"source")


class FakeSizes:
    def read(self, project_id):
        return (100, 100)


class FakeOperation:
    kind = "trim"

    def __init__(self, helper, default_options=None):
        self.helpers = (helper,)
        self.spec = OperationSpec(self.kind, {}, lambda options: options, default_options=default_options or {})
        self.rendered = []

    def render(self, rendered, options):
        self.rendered.append((rendered, options))
        return RenderedRegion(rendered.image + b"_rendered", rendered.width, rendered.height)


class FakeRegistry:
    def __init__(self, operation):
        self.operation = operation

    def get(self, kind):
        return self.operation

    def kinds(self):
        return (self.operation.kind,)


class FakeCache:
    def __init__(self, cached=None):
        self.cached = cached
        self.get_calls = []
        self.put_calls = []

    def get(self, project_id, view_id, cache_key):
        self.get_calls.append((project_id, view_id, cache_key))
        return self.cached

    def put(self, project_id, view_id, cache_key, rendered):
        self.put_calls.append((project_id, view_id, cache_key, rendered))


class InvokeHelperTests(unittest.TestCase):
    def test_validates_invokes_and_returns_updated_options_after_partial_render(self):
        validated = []
        calls = []

        def validate(options):
            validated.append(options)
            return {"threshold": options["threshold"] + 1}

        def invoke(rendered, invocation_options, current_options):
            calls.append((rendered, invocation_options, current_options))
            return {"left": 3}

        helper = Helper("auto_trim", OperationSpec("auto_trim", {}, validate), invoke)
        operation = FakeOperation(helper)
        result = InvokeHelper(FakeStore(), FakeReader(), FakeSizes(), FakeRegistry(operation)).invoke("project", 1, 1, "auto_trim", {"threshold": 2})

        self.assertEqual({"left": 3}, result)
        self.assertEqual([{"threshold": 2}], validated)
        self.assertEqual(b"source_rendered", calls[0][0].image)
        self.assertEqual({"threshold": 3}, calls[0][1])
        self.assertEqual({"left": 2}, calls[0][2])

    def test_uses_cached_prefix_without_rendering_prior_operations(self):
        calls = []

        def invoke(rendered, invocation_options, current_options):
            calls.append(rendered)
            return current_options

        helper = Helper("auto_trim", OperationSpec("auto_trim", {}, lambda options: options), invoke)
        operation = FakeOperation(helper)
        operations = FakeStore().read_project_views(ProjectId("project")).find_view(1).pipeline.operations
        cached = RenderedRegion(b"cached", 80, 80)
        cache = FakeCache(cached)
        usecase = InvokeHelper(FakeStore(), FakeReader(), FakeSizes(), FakeRegistry(operation), cache)

        usecase.invoke("project", 1, 1, "auto_trim", {})

        self.assertEqual([cached], calls)
        self.assertEqual([], operation.rendered)
        self.assertEqual(
            [(ProjectId("project"), 1, cache_key_for_step(operations, 0))],
            cache.get_calls,
        )
        self.assertEqual([], cache.put_calls)

    def test_rejects_helpers_that_do_not_belong_to_an_existing_pipeline_operation(self):
        helper = Helper("auto_trim", OperationSpec("auto_trim", {}, lambda options: options), lambda rendered, invocation, current: current)
        usecase = InvokeHelper(FakeStore(), FakeReader(), FakeSizes(), FakeRegistry(FakeOperation(helper)))

        with self.assertRaisesRegex(ValueError, "Operation index out of range"):
            usecase.invoke("project", 1, 2, "auto_trim", {})
        with self.assertRaisesRegex(ValueError, "Unknown helper"):
            usecase.invoke("project", 1, 0, "missing", {})

    def test_rejects_missing_helper_and_invalid_view_or_project(self):
        helper = Helper("other", OperationSpec("other", {}, lambda options: options), lambda rendered, invocation, current: current)
        usecase = InvokeHelper(FakeStore(), FakeReader(), FakeSizes(), FakeRegistry(FakeOperation(helper)))
        with self.assertRaises(ValueError):
            usecase.invoke("project", 1, 1, "missing", {})
        with self.assertRaises(ViewNotFound):
            usecase.invoke("project", 9, 1, "other", {})
        with self.assertRaises(ProjectNotFound):
            usecase.invoke("../nope", 1, 1, "other", {})


if __name__ == "__main__":
    unittest.main()
