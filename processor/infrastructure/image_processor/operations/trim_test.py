from io import BytesIO
import unittest

from PIL import Image

from infrastructure.image_processor.operations.trim import TrimOperation
from application.view.ports.rendered_region import RenderedRegion


def region_bytes(width: int = 4, height: int = 4, color=(255, 0, 0, 255)) -> bytes:
    image = Image.new("RGBA", (width, height), color)
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class TrimOperationTests(unittest.TestCase):
    def test_validate_passes_valid_edges(self) -> None:
        options = {"top": 1, "right": 2, "bottom": 3, "left": 4}
        result = TrimOperation().validate(options)
        self.assertEqual(options, result)

    def test_validate_zeros_are_valid(self) -> None:
        self.assertEqual({"top": 0, "right": 0, "bottom": 0, "left": 0}, TrimOperation().validate({"top": 0, "right": 0, "bottom": 0, "left": 0}))

    def test_validate_rejects_negative(self) -> None:
        with self.assertRaises(ValueError):
            TrimOperation().validate({"top": -1, "right": 0, "bottom": 0, "left": 0})

    def test_validate_rejects_non_int(self) -> None:
        with self.assertRaises(ValueError):
            TrimOperation().validate({"top": 1.0, "right": 0, "bottom": 0, "left": 0})

    def test_validate_rejects_bool(self) -> None:
        with self.assertRaises(ValueError):
            TrimOperation().validate({"top": True, "right": 0, "bottom": 0, "left": 0})

    def test_render_trims_correctly(self) -> None:
        region = RenderedRegion(region_bytes(10, 10), 10, 10)
        result = TrimOperation().render(region, {"top": 1, "right": 2, "bottom": 3, "left": 4})
        self.assertEqual(4, result.width)
        self.assertEqual(6, result.height)
        with Image.open(BytesIO(result.image)) as image:
            self.assertEqual((4, 6), image.size)

    def test_render_all_zeros_returns_unchanged_dimensions(self) -> None:
        region = RenderedRegion(region_bytes(10, 10), 10, 10)
        result = TrimOperation().render(region, {"top": 0, "right": 0, "bottom": 0, "left": 0})
        self.assertEqual(10, result.width)
        self.assertEqual(10, result.height)

    def test_render_removing_entire_output_is_rejected(self) -> None:
        region = RenderedRegion(region_bytes(10, 10), 10, 10)
        with self.assertRaisesRegex(ValueError, "Region trim removes entire output"):
            TrimOperation().render(region, {"top": 0, "right": 5, "bottom": 0, "left": 5})

    def test_render_removing_entire_output_height_rejected(self) -> None:
        region = RenderedRegion(region_bytes(10, 10), 10, 10)
        with self.assertRaisesRegex(ValueError, "Region trim removes entire output"):
            TrimOperation().render(region, {"top": 10, "right": 0, "bottom": 0, "left": 0})


if __name__ == "__main__":
    unittest.main()