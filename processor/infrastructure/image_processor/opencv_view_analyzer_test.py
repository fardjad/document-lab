from io import BytesIO
import unittest

from PIL import Image, ImageDraw

from infrastructure.image_processor.opencv_view_analyzer import OpenCVDocumentAnalyzer


def png(background: str = "white", document: bool = True) -> bytes:
    image = Image.new("RGB", (100, 80), background)
    if document:
        ImageDraw.Draw(image).rectangle((20, 15, 79, 64), fill="black")
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class OpenCVDocumentAnalyzerTests(unittest.TestCase):
    def test_detect_trim_solid_external_background(self) -> None:
        result = OpenCVDocumentAnalyzer().detect_trim(png())
        self.assertIsInstance(result.suggestion, object)
        self.assertEqual((15, 20, 15, 20), (result.suggestion.options["top"], result.suggestion.options["right"], result.suggestion.options["bottom"], result.suggestion.options["left"]))
        self.assertIsNotNone(result.confidence)

    def test_detect_trim_blank_image_returns_unavailable(self) -> None:
        result = OpenCVDocumentAnalyzer().detect_trim(png(document=False))
        self.assertIsNone(result.suggestion)
        self.assertIsNotNone(result.reason)

    def test_detect_skew_returns_absolute_tenth_degree_suggestion(self) -> None:
        image = Image.new("RGB", (200, 100), "white")
        ImageDraw.Draw(image).rectangle((30, 30, 170, 70), fill="black")
        image = image.rotate(8, fillcolor="white")
        output = BytesIO()
        image.save(output, "PNG")
        result = OpenCVDocumentAnalyzer().detect_skew(output.getvalue())
        self.assertEqual(8.0, result.suggestion)

    def test_detect_skew_works_on_rotated_padded_image(self) -> None:
        image = Image.new("RGB", (100, 80), (180, 180, 180))
        ImageDraw.Draw(image).rectangle((20, 15, 79, 64), fill=(20, 80, 180))
        image = image.rotate(10, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(180, 180, 180))
        output = BytesIO()
        image.save(output, "PNG")
        result = OpenCVDocumentAnalyzer().detect_trim(output.getvalue())
        self.assertIsInstance(result.suggestion, object)
        self.assertGreater(result.suggestion.options["left"], 0)

    def test_edge_speck_does_not_expand_trim_bounds(self) -> None:
        image = Image.new("RGB", (100, 80), "white")
        drawing = ImageDraw.Draw(image)
        drawing.rectangle((20, 15, 79, 64), fill="black")
        drawing.point((2, 2), fill="black")
        output = BytesIO()
        image.save(output, "PNG")
        result = OpenCVDocumentAnalyzer().detect_trim(output.getvalue())
        self.assertEqual((15, 20, 15, 20), (result.suggestion.options["top"], result.suggestion.options["right"], result.suggestion.options["bottom"], result.suggestion.options["left"]))


if __name__ == "__main__":
    unittest.main()