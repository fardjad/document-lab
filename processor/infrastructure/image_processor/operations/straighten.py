import math
from io import BytesIO
from numbers import Real

from PIL import Image

try:
    from application.view.ports.helper import Helper
    from application.view.ports.rendered_region import RenderedRegion
    from application.view.ports.operation_spec import OperationSpec
except ImportError:
    from ....application.view.ports.helper import Helper
    from ....application.view.ports.rendered_region import RenderedRegion
    from ....application.view.ports.operation_spec import OperationSpec


def _straighten(options: dict) -> dict:
    angle = options.get("angle")
    if isinstance(angle, bool) or not isinstance(angle, Real) or not math.isfinite(angle) or abs(angle) > 45:
        raise ValueError("Invalid straighten angle")
    canonical = round(angle * 10) / 10
    return {"angle": 0.0 if canonical == 0 else canonical}


STRAIGHTEN_SPEC = OperationSpec("straighten", {"angle": {"type": "float", "label": "Angle", "description": "Deskew angle in degrees", "control": "slider", "min": -45, "max": 45, "step": 0.1, "default": 0.0, "required": True}}, _straighten, "Straighten", "Correct the image's skew angle", "Straighten", {"angle": 0.0})

AUTO_STRAIGHTEN_INVOCATION_SPEC = OperationSpec("auto_straighten", {}, lambda options: {}, "Auto-detect angle", "Automatically detect and correct skew angle", "AutoFixHigh", {})


class StraightenOperation:
    """Fine-angle straightening executor.

    Rotates the rendered region by a small angle (up to 45 degrees in tenths)
    with BICUBIC resampling and transparent expansion padding.
    """

    kind = "straighten"
    spec = STRAIGHTEN_SPEC

    def __init__(self, analyzer=None) -> None:
        self._analyzer = analyzer
        self.helpers = (Helper("auto_straighten", AUTO_STRAIGHTEN_INVOCATION_SPEC, self._auto_straighten, "Auto-detect angle", "Automatically detect and correct skew angle"),)

    def _auto_straighten(self, rendered: RenderedRegion, invocation_options: dict, current_options: dict) -> dict:
        result = self._analyzer.detect_skew(rendered.image)
        if result.suggestion is None:
            return dict(current_options)
        return {"angle": result.suggestion}

    def validate(self, options: dict) -> dict:
        return STRAIGHTEN_SPEC.validate_options(options)

    def render(self, region: RenderedRegion, options: dict) -> RenderedRegion:
        angle = options["angle"]
        if angle == 0:
            return RenderedRegion(region.image, region.width, region.height)
        with Image.open(BytesIO(region.image)) as image:
            image = image.convert("RGBA")
            rad = math.radians(-angle)
            cos_a = abs(math.cos(rad))
            sin_a = abs(math.sin(rad))
            new_w = math.ceil(region.width * cos_a + region.height * sin_a)
            new_h = math.ceil(region.width * sin_a + region.height * cos_a)
            rotated = image.rotate(
                -angle,
                resample=Image.Resampling.BICUBIC,
                expand=True,
                fillcolor=(0, 0, 0, 0),
            )
            output = BytesIO()
            rotated.save(output, format="PNG")
            return RenderedRegion(output.getvalue(), new_w, new_h)
