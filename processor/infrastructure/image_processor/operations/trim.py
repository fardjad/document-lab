from io import BytesIO

from PIL import Image

try:
    from application.view.ports.helper import Helper
    from application.view.ports.rendered_region import RenderedRegion
    from application.view.ports.operation_spec import OperationSpec
except ImportError:
    from ....application.view.ports.helper import Helper
    from ....application.view.ports.rendered_region import RenderedRegion
    from ....application.view.ports.operation_spec import OperationSpec


def _trim(options: dict) -> dict:
    for edge in ("top", "right", "bottom", "left"):
        value = options.get(edge)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("Invalid trim edge")
    return {edge: options[edge] for edge in ("top", "right", "bottom", "left")}


TRIM_DEFAULTS = {edge: 0 for edge in ("top", "right", "bottom", "left")}
TRIM_SPEC = OperationSpec("trim", {edge: {"type": "int", "label": edge.title(), "description": f"Pixels to trim from {edge}", "control": "number", "min": 0, "step": 1, "default": 0, "required": True} for edge in ("top", "right", "bottom", "left")}, _trim, "Trim", "Remove pixels from the image edges", "ContentCut", TRIM_DEFAULTS)
AUTO_TRIM_INVOCATION_SPEC = OperationSpec("auto_trim", {}, lambda options: {}, "Auto-detect trim", "Automatically detect image borders", "AutoFixHigh", {})


class TrimOperation:
    """Border-trimming executor.

    Crops pixels from each edge. Rejects trim that would remove the entire
    output.
    """

    kind = "trim"
    spec = TRIM_SPEC

    def __init__(self, analyzer=None) -> None:
        self._analyzer = analyzer
        self.helpers = (Helper("auto_trim", AUTO_TRIM_INVOCATION_SPEC, self._auto_trim, "Auto-detect trim", "Automatically detect image borders"),)

    def _auto_trim(self, rendered: RenderedRegion, invocation_options: dict, current_options: dict) -> dict:
        result = self._analyzer.detect_trim(rendered.image)
        if result.suggestion is None:
            return dict(current_options)
        return dict(result.suggestion.options)

    def validate(self, options: dict) -> dict:
        return TRIM_SPEC.validate_options(options)

    def render(self, region: RenderedRegion, options: dict) -> RenderedRegion:
        top = options["top"]
        right = options["right"]
        bottom = options["bottom"]
        left = options["left"]
        final_width = region.width - left - right
        final_height = region.height - top - bottom
        if final_width <= 0 or final_height <= 0:
            raise ValueError("Region trim removes entire output")
        with Image.open(BytesIO(region.image)) as image:
            image = image.convert("RGBA")
            cropped = image.crop((left, top, region.width - right, region.height - bottom))
            output = BytesIO()
            cropped.save(output, format="PNG")
            return RenderedRegion(output.getvalue(), final_width, final_height)
