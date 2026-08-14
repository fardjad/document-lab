from io import BytesIO
import unittest

from PIL import Image

from infrastructure.image_processor.pillow_region_renderer import PillowRegionRenderer
from model.project import CropRectangle, CropRegion, ProjectImage, RegionTrim


def image_bytes() -> bytes:
    image = Image.new("RGBA", (2, 3))
    image.putdata([(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255), (255, 255, 0, 255), (255, 0, 255, 255), (0, 255, 255, 255)])
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class PillowRegionRendererTests(unittest.TestCase):
    def test_clockwise_quarter_turn_preserves_exact_pixels(self) -> None:
        rendered = PillowRegionRenderer().render(ProjectImage(image_bytes()), CropRegion(1, "x", CropRectangle(0, 0, 1, 1), 90))
        with Image.open(BytesIO(rendered)) as image:
            self.assertEqual("RGBA", image.mode)
            self.assertEqual((3, 2), image.size)
            self.assertEqual((255, 0, 255, 255), image.getpixel((0, 0)))
            self.assertEqual((255, 0, 0, 255), image.getpixel((2, 0)))

    def test_trim_applies_after_rotation_and_source_bytes_stay_unchanged(self) -> None:
        source = image_bytes()
        rendered = PillowRegionRenderer().render(ProjectImage(source), CropRegion(1, "x", CropRectangle(0, 0, 1, 1), 90, 0.0, RegionTrim(top=1, right=1)))
        self.assertEqual(source, image_bytes())
        with Image.open(BytesIO(rendered)) as image:
            self.assertEqual((2, 1), image.size)

    def test_straighten_creates_transparent_expanded_canvas(self) -> None:
        rendered = PillowRegionRenderer().render(ProjectImage(image_bytes()), CropRegion(1, "x", CropRectangle(0, 0, 1, 1), straighten=10.0))
        with Image.open(BytesIO(rendered)) as image:
            self.assertEqual("RGBA", image.mode)
            self.assertTrue(any(image.getpixel((x, y))[3] == 0 for x in range(image.width) for y in range(image.height)))


if __name__ == "__main__":
    unittest.main()
