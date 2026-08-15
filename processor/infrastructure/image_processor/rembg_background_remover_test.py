import unittest
from unittest import mock

from infrastructure.image_processor.rembg_background_remover import RembgBackgroundRemover
from model.project import BackgroundRemoval


class RembgBackgroundRemoverTests(unittest.TestCase):
    def test_passes_settings_to_rembg_and_caches_session_per_model(self) -> None:
        with mock.patch("infrastructure.image_processor.rembg_background_remover.remove") as remove, mock.patch("infrastructure.image_processor.rembg_background_remover.new_session") as new_session:
            remove.return_value = b"png"
            new_session.return_value = "session"
            remover = RembgBackgroundRemover()
            settings = BackgroundRemoval(model="u2net", alpha_matting=True, alpha_matting_foreground_threshold=200, alpha_matting_background_threshold=20, alpha_matting_erode_size=15, post_process_mask=True)
            result = remover.remove(b"png", settings)
            remover.remove(b"png", settings)
            self.assertEqual(b"png", result)
            new_session.assert_called_once_with("u2net")
            kwargs = remove.call_args.kwargs
            self.assertEqual("session", kwargs["session"])
            self.assertTrue(kwargs["alpha_matting"])
            self.assertEqual(200, kwargs["alpha_matting_foreground_threshold"])
            self.assertEqual(20, kwargs["alpha_matting_background_threshold"])
            self.assertEqual(15, kwargs["alpha_matting_erode_size"])
            self.assertTrue(kwargs["post_process_mask"])
            self.assertTrue(kwargs["force_return_bytes"])

    def test_rejects_non_image_result(self) -> None:
        with mock.patch("infrastructure.image_processor.rembg_background_remover.remove") as remove, mock.patch("infrastructure.image_processor.rembg_background_remover.new_session") as new_session:
            remove.return_value = None
            new_session.return_value = "session"
            with self.assertRaisesRegex(ValueError, "Background removal produced no image"):
                RembgBackgroundRemover().remove(b"png", BackgroundRemoval())


if __name__ == "__main__":
    unittest.main()
