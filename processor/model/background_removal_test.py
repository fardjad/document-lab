import unittest

from model.project import BACKGROUND_REMOVAL_MODELS, BackgroundRemoval, CropRectangle, CropRegion


class BackgroundRemovalTests(unittest.TestCase):
    def test_defaults_are_valid(self) -> None:
        settings = BackgroundRemoval()
        self.assertEqual("birefnet-general", settings.model)
        self.assertFalse(settings.alpha_matting)
        self.assertEqual(240, settings.alpha_matting_foreground_threshold)
        self.assertEqual(10, settings.alpha_matting_background_threshold)
        self.assertEqual(10, settings.alpha_matting_erode_size)
        self.assertFalse(settings.post_process_mask)

    def test_rejects_invalid_model(self) -> None:
        for value in ("nope", 0, None):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Invalid background removal model"):
                BackgroundRemoval(model=value)  # type: ignore[arg-type]

    def test_rejects_non_boolean_flags(self) -> None:
        for value in (0, "false"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Invalid background removal flag"):
                BackgroundRemoval(alpha_matting=value)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "Invalid background removal flag"):
            BackgroundRemoval(post_process_mask="yes")  # type: ignore[arg-type]

    def test_rejects_out_of_range_thresholds(self) -> None:
        for value in (-1, 256, True, "10"):
            with self.subTest(foreground=value), self.assertRaisesRegex(ValueError, "Invalid background removal threshold"):
                BackgroundRemoval(alpha_matting_foreground_threshold=value)  # type: ignore[arg-type]
            with self.subTest(background=value), self.assertRaisesRegex(ValueError, "Invalid background removal threshold"):
                BackgroundRemoval(alpha_matting_background_threshold=value)  # type: ignore[arg-type]

    def test_rejects_out_of_range_erode_size(self) -> None:
        for value in (0, 101, True, 5.0):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Invalid background removal erode size"):
                BackgroundRemoval(alpha_matting_erode_size=value)  # type: ignore[arg-type]

    def test_allowlist_covers_supported_models(self) -> None:
        self.assertEqual(("birefnet-general", "isnet-general-use", "u2net", "u2netp", "silueta"), BACKGROUND_REMOVAL_MODELS)
        for model in BACKGROUND_REMOVAL_MODELS:
            self.assertEqual(model, BackgroundRemoval(model=model).model)

    def test_region_accepts_optional_background_removal(self) -> None:
        rectangle = CropRectangle(0, 0, 1, 1)
        self.assertIsNone(CropRegion(1, "Region 1", rectangle).background_removal)
        settings = BackgroundRemoval(model="u2net")
        self.assertEqual(settings, CropRegion(1, "Region 1", rectangle, background_removal=settings).background_removal)
        with self.assertRaisesRegex(ValueError, "Invalid background removal"):
            CropRegion(1, "Region 1", rectangle, background_removal="u2net")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
