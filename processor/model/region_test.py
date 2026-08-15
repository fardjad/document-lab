import unittest

from model.operation import Operation
from model.pipeline import Pipeline
from model.region import CropRectangle, CropRegion, ProjectRegions, RegionNotFound


class CropRectangleTests(unittest.TestCase):
    def test_rejects_non_finite_or_non_positive_values(self) -> None:
        for x, y, width, height in ((float("nan"), 0, 1, 1), (0, float("inf"), 1, 1), (0, 0, 0, 1), (0, 0, 1, -1), (-0.1, 0, 1, 1)):
            with self.subTest(rectangle=(x, y, width, height)), self.assertRaises(ValueError):
                CropRectangle(x, y, width, height)

    def test_within_image_checks_normalized_bounds(self) -> None:
        self.assertTrue(CropRectangle(0, 0, 1, 1).within_image(100, 100))
        self.assertFalse(CropRectangle(0.5, 0, 0.6, 1).within_image(100, 100))


class CropRegionTests(unittest.TestCase):
    def test_strips_surrounding_whitespace_from_name(self) -> None:
        self.assertEqual("Receipt", CropRegion(1, "  Receipt  ", CropRectangle(0, 0, 1, 1)).name)

    def test_rejects_blank_or_unprintable_names(self) -> None:
        for name in ("", "   ", "x" * 101, "bad\nname"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                CropRegion(1, name, CropRectangle(0, 0, 1, 1))

    def test_with_pipeline_rebinds_only_pipeline(self) -> None:
        region = CropRegion(1, "Receipt", CropRectangle(0, 0, 0.5, 0.5))
        pipeline = Pipeline((Operation("rotate", {"degrees": 90}),))
        rebound = region.with_pipeline(pipeline)
        self.assertEqual(pipeline, rebound.pipeline)
        self.assertEqual((region.id, region.name, region.rectangle), (rebound.id, rebound.name, rebound.rectangle))

    def test_default_pipeline_is_empty(self) -> None:
        self.assertEqual(Pipeline(), CropRegion(1, "x", CropRectangle(0, 0, 1, 1)).pipeline)

    def test_region_requires_pipeline(self) -> None:
        rectangle = CropRectangle(0, 0, 1, 1)
        with self.assertRaisesRegex(ValueError, "Invalid region pipeline"):
            CropRegion(1, "Region 1", rectangle, pipeline={"rotate": 90})  # type: ignore[arg-type]


class ProjectRegionsTests(unittest.TestCase):
    def test_find_returns_matching_or_none(self) -> None:
        regions = ProjectRegions(2, (CropRegion(1, "a", CropRectangle(0, 0, 1, 1)),))
        self.assertEqual(1, regions.find(1).id)
        self.assertIsNone(regions.find(9))

    def test_add_assigns_next_id_and_never_reuses(self) -> None:
        regions = ProjectRegions(5)
        added = regions.add(CropRegion(5, "Region 5", CropRectangle(0, 0, 1, 1)))
        self.assertEqual(6, added.next_region_id)
        removed = added.remove(5)
        self.assertEqual(6, removed.next_region_id)
        recreated = removed.add(CropRegion(6, "Region 6", CropRectangle(0, 0, 1, 1)))
        self.assertEqual(7, recreated.next_region_id)

    def test_add_rejects_duplicate_ids(self) -> None:
        regions = ProjectRegions(2, (CropRegion(1, "a", CropRectangle(0, 0, 1, 1)),))
        with self.assertRaises(ValueError):
            regions.add(CropRegion(1, "dup", CropRectangle(0, 0, 1, 1)))

    def test_replace_swaps_by_id(self) -> None:
        first = CropRegion(1, "a", CropRectangle(0, 0, 1, 1))
        second = CropRegion(2, "b", CropRectangle(0, 0, 1, 1))
        updated = CropRegion(1, "renamed", CropRectangle(0, 0, 0.5, 0.5))
        regions = ProjectRegions(3, (first, second))
        replaced = regions.replace(updated)
        self.assertEqual((updated, second), replaced.regions)
        with self.assertRaises(RegionNotFound):
            ProjectRegions(1).replace(updated)

    def test_remove_deletes_by_id(self) -> None:
        first = CropRegion(1, "a", CropRectangle(0, 0, 1, 1))
        second = CropRegion(2, "b", CropRectangle(0, 0, 1, 1))
        regions = ProjectRegions(3, (first, second))
        self.assertEqual((second,), regions.remove(1).regions)
        with self.assertRaises(RegionNotFound):
            regions.remove(9)

    def test_rejects_next_id_not_after_existing_ids(self) -> None:
        with self.assertRaises(ValueError):
            ProjectRegions(1, (CropRegion(1, "a", CropRectangle(0, 0, 1, 1)),))


if __name__ == "__main__":
    unittest.main()