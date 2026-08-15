import unittest

from application.auto_processing.usecases.auto_straighten_view import AutoStraightenView
from application.auto_processing.usecases.invoke_helper import InvokeHelper


class AutoStraightenViewTests(unittest.TestCase):
    def test_is_compatibility_name_for_generic_helper_use_case(self) -> None:
        self.assertTrue(issubclass(AutoStraightenView, InvokeHelper))


if __name__ == "__main__":
    unittest.main()
