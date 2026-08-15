from io import BytesIO

from PIL import Image

try:
    from model.rendered_region import RenderedRegion
    from model.operation_spec import OperationSpec
except ImportError:
    from ....model.rendered_region import RenderedRegion
    from ....model.operation_spec import OperationSpec


BACKGROUND_REMOVAL_MODELS = ("birefnet-general", "isnet-general-use", "u2net", "u2netp", "silueta")

def _remove_background(options: dict) -> dict:
    model = options.get("model", "birefnet-general")
    if not isinstance(model, str) or model not in BACKGROUND_REMOVAL_MODELS: raise ValueError("Invalid background removal model")
    alpha_matting, post_process_mask = options.get("alpha_matting", False), options.get("post_process_mask", False)
    if not isinstance(alpha_matting, bool) or not isinstance(post_process_mask, bool): raise ValueError("Invalid background removal flag")
    foreground, background = options.get("alpha_matting_foreground_threshold", 240), options.get("alpha_matting_background_threshold", 10)
    if any(isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 255 for v in (foreground, background)): raise ValueError("Invalid background removal threshold")
    erode = options.get("alpha_matting_erode_size", 10)
    if isinstance(erode, bool) or not isinstance(erode, int) or not 1 <= erode <= 100: raise ValueError("Invalid background removal erode size")
    return {"model": model, "alpha_matting": alpha_matting, "alpha_matting_foreground_threshold": foreground, "alpha_matting_background_threshold": background, "alpha_matting_erode_size": erode, "post_process_mask": post_process_mask}

REMOVE_BACKGROUND_SPEC = OperationSpec("remove_background", {"model": BACKGROUND_REMOVAL_MODELS}, _remove_background)


class RemoveBackgroundExecutor:
    """Background removal executor.

    Validates the background removal option schema (absorbing the old
    ``BackgroundRemoval`` dataclass validation) and delegates the actual
    removal to an injected background remover collaborator.
    """

    kind = "remove_background"
    spec = REMOVE_BACKGROUND_SPEC

    def __init__(self, background_remover=None) -> None:
        self._background_remover = background_remover

    def validate(self, options: dict) -> dict:
        return REMOVE_BACKGROUND_SPEC.validate_options(options)

    def render(self, region: RenderedRegion, options: dict) -> RenderedRegion:
        if self._background_remover is None:
            raise ValueError("Background removal unavailable")
        removed = self._background_remover.remove(region.image, options)
        with Image.open(BytesIO(removed)) as result:
            result = result.convert("RGBA")
            output = BytesIO()
            result.save(output, format="PNG")
            return RenderedRegion(output.getvalue(), region.width, region.height)
