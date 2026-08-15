from io import BytesIO
import unittest

from PIL import Image

from infrastructure.image_processor.operations.remove_background import RemoveBackgroundOperation
from application.view.ports.rendered_region import RenderedRegion


def region_bytes(width: int = 4, height: int = 4, color=(255, 0, 0, 255)) -> bytes:
    image = Image.new("RGBA", (width, height), color)
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class PassthroughRemover:
    """Fake background remover that returns the input bytes unchanged."""

    def remove(self, image: bytes, settings) -> bytes:
        return image


class RemoveBackgroundOperationTests(unittest.TestCase):
    def test_validate_defaults(self) -> None:
        result = RemoveBackgroundOperation().validate({})
        self.assertEqual("birefnet-general", result["model"])
        self.assertFalse(result["alpha_matting"])
        self.assertEqual(240, result["alpha_matting_foreground_threshold"])
        self.assertEqual(10, result["alpha_matting_background_threshold"])
        self.assertEqual(10, result["alpha_matting_erode_size"])
        self.assertFalse(result["post_process_mask"])

    def test_validate_valid_options(self) -> None:
        options = {
            "model": "u2net",
            "alpha_matting": True,
            "alpha_matting_foreground_threshold": 200,
            "alpha_matting_background_threshold": 20,
            "alpha_matting_erode_size": 15,
            "post_process_mask": True,
        }
        result = RemoveBackgroundOperation().validate(options)
        self.assertEqual(options, result)

    def test_validate_rejects_invalid_model(self) -> None:
        with self.assertRaises(ValueError):
            RemoveBackgroundOperation().validate({"model": "unknown"})

    def test_validate_rejects_bool_flags_not_bool(self) -> None:
        with self.assertRaises(ValueError):
            RemoveBackgroundOperation().validate({"alpha_matting": "yes"})

    def test_validate_rejects_threshold_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            RemoveBackgroundOperation().validate({"alpha_matting_foreground_threshold": 256})

    def test_validate_rejects_threshold_bool(self) -> None:
        with self.assertRaises(ValueError):
            RemoveBackgroundOperation().validate({"alpha_matting_foreground_threshold": True})

    def test_validate_rejects_erode_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            RemoveBackgroundOperation().validate({"alpha_matting_erode_size": 0})
        with self.assertRaises(ValueError):
            RemoveBackgroundOperation().validate({"alpha_matting_erode_size": 101})

    def test_render_with_passthrough_preserves_dimensions(self) -> None:
        region = RenderedRegion(region_bytes(4, 4), 4, 4)
        executor = RemoveBackgroundOperation(PassthroughRemover())
        result = executor.render(region, RemoveBackgroundOperation().validate({}))
        self.assertEqual(4, result.width)
        self.assertEqual(4, result.height)
        with Image.open(BytesIO(result.image)) as result_image:
            self.assertEqual("RGBA", result_image.mode)
            self.assertEqual((4, 4), result_image.size)

    def test_render_without_collaborator_is_rejected(self) -> None:
        region = RenderedRegion(region_bytes(4, 4), 4, 4)
        with self.assertRaisesRegex(ValueError, "Background removal unavailable"):
            RemoveBackgroundOperation().render(region, {})


if __name__ == "__main__":
    unittest.main()