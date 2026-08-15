import unittest

from application.auto_processing.usecases.auto_trim_view import AutoTrimView
from application.auto_processing.usecases.invoke_helper import InvokeHelper


class AutoTrimViewTests(unittest.TestCase):
    def test_is_compatibility_name_for_generic_helper_use_case(self) -> None:
        self.assertTrue(issubclass(AutoTrimView, InvokeHelper))


if __name__ == "__main__":
    unittest.main()
