from io import BytesIO
import unittest

from PIL import Image, ImageDraw

from infrastructure.image_processor.opencv_region_analyzer import OpenCVRegionAnalyzer
from model.project import CropRectangle, CropRegion, ProjectImage, RegionTrim


def png(background: str = "white", document: bool = True) -> bytes:
    image = Image.new("RGB", (100, 80), background)
    if document:
        ImageDraw.Draw(image).rectangle((20, 15, 79, 64), fill="black")
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class OpenCVRegionAnalyzerTests(unittest.TestCase):
    def test_trim_detects_solid_external_background(self) -> None:
        result = OpenCVRegionAnalyzer().analyze(ProjectImage(png()), CropRegion(1, "r", CropRectangle(0, 0, 1, 1)), "trim")
        self.assertEqual(RegionTrim(15, 20, 15, 20), result.suggestion)
        self.assertIsNotNone(result.confidence)

    def test_blank_image_returns_unavailable_result(self) -> None:
        result = OpenCVRegionAnalyzer().analyze(ProjectImage(png(document=False)), CropRegion(1, "r", CropRectangle(0, 0, 1, 1)), "trim")
        self.assertIsNone(result.suggestion)
        self.assertIsNotNone(result.reason)

    def test_straighten_returns_absolute_tenth_degree_suggestion(self) -> None:
        image = Image.new("RGB", (200, 100), "white")
        ImageDraw.Draw(image).rectangle((30, 30, 170, 70), fill="black")
        image = image.rotate(8, fillcolor="white")
        output = BytesIO()
        image.save(output, "PNG")
        result = OpenCVRegionAnalyzer().analyze(ProjectImage(output.getvalue()), CropRegion(1, "r", CropRectangle(0, 0, 1, 1)), "straighten")
        self.assertEqual(8.0, result.suggestion)

    def test_trim_uses_transparent_rotation_padding_and_keeps_card(self) -> None:
        image = Image.new("RGB", (100, 80), (180, 180, 180))
        ImageDraw.Draw(image).rectangle((20, 15, 79, 64), fill=(20, 80, 180))
        output = BytesIO()
        image.save(output, "PNG")
        result = OpenCVRegionAnalyzer().analyze(ProjectImage(output.getvalue()), CropRegion(1, "r", CropRectangle(0, 0, 1, 1), straighten=10), "trim")
        self.assertIsInstance(result.suggestion, RegionTrim)
        self.assertEqual(18, result.suggestion.top)
        self.assertGreater(result.suggestion.left, 0)

    def test_edge_speck_does_not_expand_trim_bounds(self) -> None:
        image = Image.new("RGB", (100, 80), "white")
        drawing = ImageDraw.Draw(image)
        drawing.rectangle((20, 15, 79, 64), fill="black")
        drawing.point((2, 2), fill="black")
        output = BytesIO()
        image.save(output, "PNG")
        result = OpenCVRegionAnalyzer().analyze(ProjectImage(output.getvalue()), CropRegion(1, "r", CropRectangle(0, 0, 1, 1)), "trim")
        self.assertEqual(RegionTrim(15, 20, 15, 20), result.suggestion)


if __name__ == "__main__":
    unittest.main()
