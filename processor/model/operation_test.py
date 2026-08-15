import unittest

from model.operation import Operation


class OperationTests(unittest.TestCase):
    def test_accepts_valid_kind_and_options(self) -> None:
        op = Operation("rotate", {"degrees": 90})
        self.assertEqual("rotate", op.kind)
        self.assertEqual({"degrees": 90}, op.options)

    def test_defaults_to_empty_options(self) -> None:
        op = Operation("trim")
        self.assertEqual({}, op.options)

    def test_rejects_empty_kind(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid operation kind"):
            Operation("")  # type: ignore[arg-type]

    def test_rejects_non_string_kind(self) -> None:
        for value in (90, None, True):
            with self.subTest(kind=value), self.assertRaisesRegex(ValueError, "Invalid operation kind"):
                Operation(value)  # type: ignore[arg-type]

    def test_rejects_non_dict_options(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid operation options"):
            Operation("rotate", [("degrees", 90)])  # type: ignore[arg-type]

    def test_options_are_copied(self) -> None:
        original = {"degrees": 90}
        op = Operation("rotate", original)
        original["degrees"] = 180
        self.assertEqual(90, op.options["degrees"])


if __name__ == "__main__":
    unittest.main()