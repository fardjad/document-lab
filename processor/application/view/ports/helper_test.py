import unittest

from application.view.ports.helper import Helper
from application.view.ports.operation_spec import OperationSpec
from application.view.ports.rendered_region import RenderedRegion


class HelperTests(unittest.TestCase):
    def test_constructs_with_valid_values(self):
        spec = OperationSpec("example", {}, lambda options: options)
        helper = Helper("suggest", spec, lambda rendered, invocation, current: current)

        self.assertEqual("suggest", helper.name)
        self.assertIs(spec, helper.invocation_spec)

    def test_rejects_invalid_types(self):
        spec = OperationSpec("example", {}, lambda options: options)
        valid = lambda rendered, invocation, current: current

        with self.assertRaises(ValueError):
            Helper("", spec, valid)
        with self.assertRaises(ValueError):
            Helper("suggest", object(), valid)
        with self.assertRaises(ValueError):
            Helper("suggest", spec, None)

    def test_invoke_helper_forwards_and_returns_result(self):
        seen = {}
        rendered = RenderedRegion(b"image", 10, 20)
        invocation = {"amount": 2}
        current = {"kind": "trim"}

        def invoker(actual_rendered, actual_invocation, actual_current):
            seen.update(rendered=actual_rendered, invocation=actual_invocation, current=actual_current)
            return {"updated": True}

        helper = Helper("suggest", OperationSpec("example", {}, lambda options: options), invoker)

        self.assertEqual({"updated": True}, helper.invoke_helper(rendered, invocation, current))
        self.assertIs(rendered, seen["rendered"])
        self.assertIs(invocation, seen["invocation"])
        self.assertIs(current, seen["current"])

    def test_invoke_helper_rejects_invalid_result(self):
        helper = Helper("suggest", OperationSpec("example", {}, lambda options: options), lambda *_: [])

        with self.assertRaises(ValueError):
            helper.invoke_helper(RenderedRegion(b"image", 1, 1), {}, {})


if __name__ == "__main__":
    unittest.main()
