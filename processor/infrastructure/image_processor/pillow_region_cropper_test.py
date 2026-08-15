from io import BytesIO
import unittest

from PIL import Image

from infrastructure.image_processor.pillow_region_cropper import PillowRegionCropper
from model.region import CropRectangle


def image_bytes(width: int = 100, height: int = 80, color=(255, 0, 0, 255)) -> bytes:
    image = Image.new("RGBA", (width, height), color)
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class PillowRegionCropperTests(unittest.TestCase):
    def test_full_rectangle_crops_entire_image(self) -> None:
        result = PillowRegionCropper().crop(image_bytes(100, 80), CropRectangle(0, 0, 1, 1))
        self.assertEqual(100, result.width)
        self.assertEqual(80, result.height)
        with Image.open(BytesIO(result.image)) as cropped:
            self.assertEqual("RGBA", cropped.mode)
            self.assertEqual((100, 80), cropped.size)

    def test_half_rectangle_crops_half(self) -> None:
        result = PillowRegionCropper().crop(image_bytes(100, 80), CropRectangle(0, 0, 0.5, 0.5))
        self.assertEqual(50, result.width)
        self.assertEqual(40, result.height)

    def test_offset_rectangle_crops_correct_region(self) -> None:
        image = Image.new("RGBA", (100, 80))
        for x in range(100):
            for y in range(80):
                if x >= 50:
                    image.putpixel((x, y), (0, 255, 0, 255))
                else:
                    image.putpixel((x, y), (255, 0, 0, 255))
        output = BytesIO()
        image.save(output, "PNG")
        result = PillowRegionCropper().crop(output.getvalue(), CropRectangle(0.5, 0, 0.5, 1))
        self.assertEqual(50, result.width)
        self.assertEqual(80, result.height)
        with Image.open(BytesIO(result.image)) as cropped:
            self.assertEqual((0, 255, 0, 255), cropped.getpixel((0, 0)))


if __name__ == "__main__":
    unittest.main()