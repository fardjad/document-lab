import math
from io import BytesIO
from numbers import Real

from PIL import Image

try:
    from application.view.ports.operation_spec import OperationSpec
    from application.view.ports.rendered_region import RenderedRegion
except ImportError:
    from ....application.view.ports.operation_spec import OperationSpec
    from ....application.view.ports.rendered_region import RenderedRegion


def validate_crop(options: dict) -> dict:
    values = tuple(options.get(key) for key in ("x", "y", "width", "height"))
    if any(isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) for value in values):
        raise ValueError("Invalid crop rectangle")
    x, y, width, height = values
    if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
        raise ValueError("Invalid crop rectangle")
    return {key: value for key, value in zip(("x", "y", "width", "height"), values)}


CROP_SPEC = OperationSpec("crop", {key: "finite real, normalized" for key in ("x", "y", "width", "height")}, validate_crop)


class CropExecutor:
    kind = "crop"
    spec = CROP_SPEC

    def validate(self, options: dict) -> dict:
        return CROP_SPEC.validate_options(options)

    def render(self, region: RenderedRegion, options: dict) -> RenderedRegion:
        x, y, width, height = (options[key] for key in ("x", "y", "width", "height"))
        with Image.open(BytesIO(region.image)) as source:
            source = source.convert("RGBA")
            left = round(x * source.width)
            top = round(y * source.height)
            right = round((x + width) * source.width)
            bottom = round((y + height) * source.height)
            cropped = source.crop((left, top, right, bottom))
            output = BytesIO()
            cropped.save(output, format="PNG")
            new_width, new_height = cropped.size
            return RenderedRegion(output.getvalue(), new_width, new_height)
