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


if __name__ == "__main__":
    unittest.main()
