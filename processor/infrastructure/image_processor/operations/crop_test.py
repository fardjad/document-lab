from io import BytesIO
import unittest

from PIL import Image

from infrastructure.image_processor.operations.crop import CropExecutor, CROP_SPEC, validate_crop
from application.view.ports.rendered_region import RenderedRegion


def region_bytes(width: int = 100, height: int = 100, color=(255, 0, 0, 255)) -> bytes:
    image = Image.new("RGBA", (width, height), color)
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class CropSpecTests(unittest.TestCase):
    def test_validate_accepts_valid_normalized_rectangle(self) -> None:
        options = {"x": 0.25, "y": 0.1, "width": 0.5, "height": 0.75}
        self.assertEqual(options, validate_crop(options))
        self.assertIs(CROP_SPEC.validate, validate_crop)

    def test_validate_rejects_negative_position(self) -> None:
        for key in ("x", "y"):
            options = {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5}
            options[key] = -0.01
            with self.subTest(key=key), self.assertRaises(ValueError):
                CropExecutor().validate(options)

    def test_validate_rejects_non_positive_size(self) -> None:
        for key in ("width", "height"):
            options = {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5}
            options[key] = 0
            with self.subTest(key=key), self.assertRaises(ValueError):
                CropExecutor().validate(options)

    def test_validate_rejects_rectangle_outside_normalized_bounds(self) -> None:
        for key, value in (("x", 0.6), ("y", 0.6)):
            options = {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5}
            options[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                CropExecutor().validate(options)

    def test_validate_rejects_bool_and_non_real_values(self) -> None:
        for key, value in (("x", True), ("y", "0.1"), ("width", object()), ("height", None)):
            options = {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5}
            options[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                CropExecutor().validate(options)

    def test_validate_rejects_non_finite_values(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            options = {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5}
            options["x"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                CropExecutor().validate(options)


class CropExecutorTests(unittest.TestCase):
    def test_render_sub_region_has_expected_dimensions(self) -> None:
        region = RenderedRegion(region_bytes(), 100, 100)
        result = CropExecutor().render(region, {"x": 0.25, "y": 0.25, "width": 0.5, "height": 0.5})
        self.assertEqual(50, result.width)
        self.assertEqual(50, result.height)
        with Image.open(BytesIO(result.image)) as image:
            self.assertEqual((50, 50), image.size)

    def test_render_full_region_preserves_dimensions(self) -> None:
        region = RenderedRegion(region_bytes(), 100, 100)
        result = CropExecutor().render(region, {"x": 0, "y": 0, "width": 1, "height": 1})
        self.assertEqual(100, result.width)
        self.assertEqual(100, result.height)

    def test_render_zero_origin_full_size_is_identity_dimensions(self) -> None:
        region = RenderedRegion(region_bytes(), 100, 100)
        result = CropExecutor().render(region, {"x": 0, "y": 0, "width": 1, "height": 1})
        self.assertEqual((100, 100), (result.width, result.height))


if __name__ == "__main__":
    unittest.main()
