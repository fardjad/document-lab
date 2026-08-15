from io import BytesIO
import unittest

from PIL import Image

from infrastructure.image_processor.operations.rotate import RotateExecutor
from application.view.ports.rendered_region import RenderedRegion


def region_bytes(width: int = 4, height: int = 3, color=(255, 0, 0, 255)) -> bytes:
    image = Image.new("RGBA", (width, height), color)
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class RotateExecutorTests(unittest.TestCase):
    def test_validate_canonicalizes_degrees_mod_360(self) -> None:
        self.assertEqual({"degrees": 90}, RotateExecutor().validate({"degrees": 90}))
        self.assertEqual({"degrees": 0}, RotateExecutor().validate({"degrees": 360}))
        self.assertEqual({"degrees": 90}, RotateExecutor().validate({"degrees": 450}))

    def test_validate_rejects_non_multiple_of_90(self) -> None:
        with self.assertRaises(ValueError):
            RotateExecutor().validate({"degrees": 45})

    def test_validate_rejects_non_int(self) -> None:
        with self.assertRaises(ValueError):
            RotateExecutor().validate({"degrees": 90.0})

    def test_validate_rejects_bool(self) -> None:
        with self.assertRaises(ValueError):
            RotateExecutor().validate({"degrees": True})

    def test_render_0_degrees_returns_unchanged(self) -> None:
        region = RenderedRegion(region_bytes(4, 3), 4, 3)
        result = RotateExecutor().render(region, {"degrees": 0})
        self.assertEqual(4, result.width)
        self.assertEqual(3, result.height)

    def test_render_90_swaps_dimensions(self) -> None:
        region = RenderedRegion(region_bytes(4, 3), 4, 3)
        result = RotateExecutor().render(region, {"degrees": 90})
        self.assertEqual(3, result.width)
        self.assertEqual(4, result.height)

    def test_render_180_preserves_dimensions(self) -> None:
        region = RenderedRegion(region_bytes(4, 3), 4, 3)
        result = RotateExecutor().render(region, {"degrees": 180})
        self.assertEqual(4, result.width)
        self.assertEqual(3, result.height)

    def test_render_270_swaps_dimensions(self) -> None:
        region = RenderedRegion(region_bytes(4, 3), 4, 3)
        result = RotateExecutor().render(region, {"degrees": 270})
        self.assertEqual(3, result.width)
        self.assertEqual(4, result.height)

    def test_render_90_preserves_pixels(self) -> None:
        image = Image.new("RGBA", (2, 3))
        image.putdata([(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255), (255, 255, 0, 255), (255, 0, 255, 255), (0, 255, 255, 255)])
        output = BytesIO()
        image.save(output, "PNG")
        region = RenderedRegion(output.getvalue(), 2, 3)
        result = RotateExecutor().render(region, {"degrees": 90})
        with Image.open(BytesIO(result.image)) as result_image:
            self.assertEqual("RGBA", result_image.mode)
            self.assertEqual((3, 2), result_image.size)
            self.assertEqual((255, 0, 255, 255), result_image.getpixel((0, 0)))
            self.assertEqual((255, 0, 0, 255), result_image.getpixel((2, 0)))


if __name__ == "__main__":
    unittest.main()