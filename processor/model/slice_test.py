import unittest

from model.project import CropRectangle, CropSlice, ProjectSlices


class SliceModelTests(unittest.TestCase):
    def test_rectangle_requires_positive_finite_dimensions(self) -> None:
        with self.assertRaises(ValueError):
            CropRectangle(0, 0, 0, 1)
        with self.assertRaises(ValueError):
            CropRectangle(0, 0, float("nan"), 1)

    def test_slice_name_is_printable_and_bounded(self) -> None:
        with self.assertRaises(ValueError):
            CropSlice(1, "\n", CropRectangle(0, 0, 1, 1))
        with self.assertRaises(ValueError):
            CropSlice(1, "x" * 101, CropRectangle(0, 0, 1, 1))

    def test_project_slices_requires_next_id_after_existing_ids(self) -> None:
        item = CropSlice(1, "Slice 1", CropRectangle(0, 0, 1, 1))
        with self.assertRaises(ValueError):
            ProjectSlices(1, (item,))

    def test_rotation_defaults_and_canonicalizes(self) -> None:
        rectangle = CropRectangle(0, 0, 1, 1)
        self.assertEqual(0, CropSlice(1, "Slice 1", rectangle).rotation)
        self.assertEqual(270, CropSlice(1, "Slice 1", rectangle, -90).rotation)
        self.assertEqual((90, 180, 270), tuple(CropSlice(1, "Slice 1", rectangle, value).rotation for value in (90, 180, 270)))
        self.assertEqual(0, CropSlice(1, "Slice 1", rectangle, 360).rotation)

    def test_rotation_requires_integer_multiples_of_90(self) -> None:
        rectangle = CropRectangle(0, 0, 1, 1)
        for value in (True, 45, 45.0, "90"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                CropSlice(1, "Slice 1", rectangle, value)  # type: ignore[arg-type]

    def test_straighten_canonicalizes_and_validates(self) -> None:
        rectangle = CropRectangle(0, 0, 1, 1)
        self.assertEqual(1.2, CropSlice(1, "Slice 1", rectangle, straighten=1.20000000001).straighten)
        self.assertEqual(0.0, CropSlice(1, "Slice 1", rectangle, straighten=-0.0).straighten)
        for value in (45.1, float("inf"), float("nan"), True, "1.0", 1.23):
            with self.subTest(value=value), self.assertRaises(ValueError):
                CropSlice(1, "Slice 1", rectangle, straighten=value)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
