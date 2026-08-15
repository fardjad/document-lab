import math
from io import BytesIO
from numbers import Real

from PIL import Image

try:
    from model.rendered_region import RenderedRegion
    from model.operation_spec import OperationSpec
except ImportError:
    from ....model.rendered_region import RenderedRegion
    from ....model.operation_spec import OperationSpec


def _straighten(options: dict) -> dict:
    angle = options.get("angle")
    if isinstance(angle, bool) or not isinstance(angle, Real) or not math.isfinite(angle) or abs(angle) > 45:
        raise ValueError("Invalid straighten angle")
    canonical = round(angle * 10) / 10
    return {"angle": 0.0 if canonical == 0 else canonical}


STRAIGHTEN_SPEC = OperationSpec("straighten", {"angle": "real, between -45 and 45"}, _straighten)


class StraightenExecutor:
    """Fine-angle straightening executor.

    Rotates the rendered region by a small angle (up to 45 degrees in tenths)
    with BICUBIC resampling and transparent expansion padding.
    """

    kind = "straighten"
    spec = STRAIGHTEN_SPEC

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
