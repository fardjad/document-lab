import unittest

from model.operation_spec import OperationSpec


class OperationSpecTests(unittest.TestCase):
    def test_constructs_generic_spec(self):
        spec = OperationSpec("example", {"value": "int"}, lambda options: options)
        self.assertEqual("example", spec.kind)
        self.assertEqual({"value": "int"}, spec.schema)

    def test_rejects_invalid_types(self):
        with self.assertRaises(ValueError):
            OperationSpec("", {}, lambda options: options)
        with self.assertRaises(ValueError):
            OperationSpec("example", [], lambda options: options)
        with self.assertRaises(ValueError):
            OperationSpec("example", {}, None)

    def test_validate_options_forwards_and_returns_result(self):
        seen = {}

        def validator(options):
            seen["options"] = options
            return {"canonical": True}

        options = {"raw": 1}
        result = OperationSpec("example", {}, validator).validate_options(options)
        self.assertEqual(options, seen["options"])
        self.assertEqual({"canonical": True}, result)

    def test_validate_options_rejects_bad_input_and_result(self):
        spec = OperationSpec("example", {}, lambda options: options)
        with self.assertRaises(ValueError):
            spec.validate_options([])
        with self.assertRaises(ValueError):
            OperationSpec("example", {}, lambda options: None).validate_options({})


if __name__ == "__main__":
    unittest.main()
