import unittest

from application.view.ports.rendered_region import RenderedRegion


class RenderedRegionTests(unittest.TestCase):
    def test_accepts_valid_values(self) -> None:
        region = RenderedRegion(b"\x89PNG", 100, 200)
        self.assertEqual(b"\x89PNG", region.image)
        self.assertEqual(100, region.width)
        self.assertEqual(200, region.height)

    def test_rejects_non_bytes_image(self) -> None:
        for value in ("not bytes", 42, None, True):
            with self.subTest(image=value), self.assertRaisesRegex(ValueError, "Invalid rendered region image"):
                RenderedRegion(value, 100, 100)  # type: ignore[arg-type]

    def test_rejects_non_positive_width(self) -> None:
        for value in (0, -1, True, 1.5, "10"):
            with self.subTest(width=value), self.assertRaisesRegex(ValueError, "Invalid rendered region width"):
                RenderedRegion(b"x", value, 100)  # type: ignore[arg-type]

    def test_rejects_non_positive_height(self) -> None:
        for value in (0, -1, True, 1.5, "10"):
            with self.subTest(height=value), self.assertRaisesRegex(ValueError, "Invalid rendered region height"):
                RenderedRegion(b"x", 100, value)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()