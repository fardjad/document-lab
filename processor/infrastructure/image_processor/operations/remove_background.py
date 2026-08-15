from io import BytesIO

from PIL import Image

try:
    from model.rendered_region import RenderedRegion
except ImportError:
    from ....model.rendered_region import RenderedRegion


BACKGROUND_REMOVAL_MODELS = ("birefnet-general", "isnet-general-use", "u2net", "u2netp", "silueta")


class RemoveBackgroundExecutor:
    """Background removal executor.

    Validates the background removal option schema (absorbing the old
    ``BackgroundRemoval`` dataclass validation) and delegates the actual
    removal to an injected background remover collaborator.
    """

    kind = "remove_background"

    def __init__(self, background_remover=None) -> None:
        self._background_remover = background_remover

    def validate(self, options: dict) -> dict:
        model = options.get("model", "birefnet-general")
        if not isinstance(model, str) or model not in BACKGROUND_REMOVAL_MODELS:
            raise ValueError("Invalid background removal model")
        alpha_matting = options.get("alpha_matting", False)
        post_process_mask = options.get("post_process_mask", False)
        if not isinstance(alpha_matting, bool) or not isinstance(post_process_mask, bool):
            raise ValueError("Invalid background removal flag")
        foreground_threshold = options.get("alpha_matting_foreground_threshold", 240)
        background_threshold = options.get("alpha_matting_background_threshold", 10)
        for threshold in (foreground_threshold, background_threshold):
            if isinstance(threshold, bool) or not isinstance(threshold, int) or not 0 <= threshold <= 255:
                raise ValueError("Invalid background removal threshold")
        erode_size = options.get("alpha_matting_erode_size", 10)
        if isinstance(erode_size, bool) or not isinstance(erode_size, int) or not 1 <= erode_size <= 100:
            raise ValueError("Invalid background removal erode size")
        return {
            "model": model,
            "alpha_matting": alpha_matting,
            "alpha_matting_foreground_threshold": foreground_threshold,
            "alpha_matting_background_threshold": background_threshold,
            "alpha_matting_erode_size": erode_size,
            "post_process_mask": post_process_mask,
        }

    def render(self, region: RenderedRegion, options: dict) -> RenderedRegion:
        if self._background_remover is None:
            raise ValueError("Background removal unavailable")
        removed = self._background_remover.remove(region.image, options)
        with Image.open(BytesIO(removed)) as result:
            result = result.convert("RGBA")
            output = BytesIO()
            result.save(output, format="PNG")
            return RenderedRegion(output.getvalue(), region.width, region.height)