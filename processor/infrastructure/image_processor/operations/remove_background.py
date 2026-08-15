from io import BytesIO

from PIL import Image

try:
    from application.view.ports.rendered_region import RenderedRegion
    from application.view.ports.operation_spec import OperationSpec
except ImportError:
    from ....application.view.ports.rendered_region import RenderedRegion
    from ....application.view.ports.operation_spec import OperationSpec


BACKGROUND_REMOVAL_MODELS = ("birefnet-general", "birefnet-portrait", "isnet-general", "isnet-anime", "u2net", "silueta")

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

REMOVE_BACKGROUND_DEFAULTS = {"model": "birefnet-general", "alpha_matting": False, "alpha_matting_foreground_threshold": 128, "alpha_matting_background_threshold": 128, "alpha_matting_erode_size": 10, "post_process_mask": False}
REMOVE_BACKGROUND_SPEC = OperationSpec("remove_background", {
    "model": {"type": "select", "label": "Model", "description": "Background removal model", "control": "dropdown", "options": list(BACKGROUND_REMOVAL_MODELS), "default": "birefnet-general", "required": True},
    "alpha_matting": {"type": "bool", "label": "Alpha matting", "description": "Enable alpha matting for finer edges", "control": "checkbox", "default": False, "required": True},
    "alpha_matting_foreground_threshold": {"type": "int", "label": "Foreground threshold", "description": "Alpha matting foreground threshold", "control": "number", "min": 0, "max": 255, "step": 1, "default": 128, "required": True},
    "alpha_matting_background_threshold": {"type": "int", "label": "Background threshold", "description": "Alpha matting background threshold", "control": "number", "min": 0, "max": 255, "step": 1, "default": 128, "required": True},
    "alpha_matting_erode_size": {"type": "int", "label": "Erode size", "description": "Alpha matting erode size", "control": "number", "min": 1, "max": 100, "step": 1, "default": 10, "required": True},
    "post_process_mask": {"type": "bool", "label": "Clean mask", "description": "Post-process the mask", "control": "checkbox", "default": False, "required": True},
}, _remove_background, "Remove Background", "Remove the background from the image", "AutoFixHigh", REMOVE_BACKGROUND_DEFAULTS)


class RemoveBackgroundOperation:
    """Background removal executor.

    Validates the background removal option schema (absorbing the old
    ``BackgroundRemoval`` dataclass validation) and delegates the actual
    removal to an injected background remover collaborator.
    """

    kind = "remove_background"
    spec = REMOVE_BACKGROUND_SPEC
    helpers = ()

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
