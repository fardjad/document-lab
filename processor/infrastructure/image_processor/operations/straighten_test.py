from io import BytesIO
import unittest

from PIL import Image

from infrastructure.image_processor.operations.straighten import StraightenExecutor
from model.rendered_region import RenderedRegion


def region_bytes(width: int = 4, height: int = 4, color=(255, 0, 0, 255)) -> bytes:
    image = Image.new("RGBA", (width, height), color)
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class StraightenExecutorTests(unittest.TestCase):
    def test_validate_canonicalizes_angle_to_tenths(self) -> None:
        self.assertEqual({"angle": 1.5}, StraightenExecutor().validate({"angle": 1.52}))
        self.assertEqual({"angle": -3.2}, StraightenExecutor().validate({"angle": -3.24}))

    def test_validate_normalizes_zero(self) -> None:
        self.assertEqual({"angle": 0.0}, StraightenExecutor().validate({"angle": 0}))
        self.assertEqual({"angle": 0.0}, StraightenExecutor().validate({"angle": 0.04}))

    def test_validate_rejects_abs_over_45(self) -> None:
        with self.assertRaises(ValueError):
            StraightenExecutor().validate({"angle": 45.1})
        with self.assertRaises(ValueError):
            StraightenExecutor().validate({"angle": -45.1})

    def test_validate_rejects_non_real(self) -> None:
        with self.assertRaises(ValueError):
            StraightenExecutor().validate({"angle": "x"})

    def test_validate_rejects_bool(self) -> None:
        with self.assertRaises(ValueError):
            StraightenExecutor().validate({"angle": True})

    def test_render_zero_angle_returns_unchanged(self) -> None:
        region = RenderedRegion(region_bytes(4, 3), 4, 3)
        result = StraightenExecutor().render(region, {"angle": 0.0})
        self.assertEqual(4, result.width)
        self.assertEqual(3, result.height)

    def test_render_nonzero_angle_expands_canvas(self) -> None:
        import math

        region = RenderedRegion(region_bytes(100, 100), 100, 100)
        result = StraightenExecutor().render(region, {"angle": 10.0})
        rad = math.radians(10)
        expected_w = math.ceil(100 * abs(math.cos(rad)) + 100 * abs(math.sin(rad)))
        expected_h = math.ceil(100 * abs(math.sin(rad)) + 100 * abs(math.cos(rad)))
        self.assertEqual(expected_w, result.width)
        self.assertEqual(expected_h, result.height)

    def test_render_creates_transparent_padding(self) -> None:
        region = RenderedRegion(region_bytes(10, 10), 10, 10)
        result = StraightenExecutor().render(region, {"angle": 10.0})
        with Image.open(BytesIO(result.image)) as image:
            self.assertEqual("RGBA", image.mode)
            self.assertTrue(any(image.getpixel((x, y))[3] == 0 for x in range(image.width) for y in range(image.height)))


if __name__ == "__main__":
    unittest.main()