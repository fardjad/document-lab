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


CROP_DEFAULTS = {"x": 0, "y": 0, "width": 1, "height": 1}
CROP_SPEC = OperationSpec("crop", {
    key: {"type": "float", "label": label, "description": description, "control": "number", "min": 0, "max": 1, "step": 0.01, "default": CROP_DEFAULTS[key], "required": True}
    for key, label, description in (("x", "X", "Left edge position (normalized 0-1)"), ("y", "Y", "Top edge position (normalized 0-1)"), ("width", "Width", "Crop width (normalized 0-1)"), ("height", "Height", "Crop height (normalized 0-1)"))
}, validate_crop, "Crop", "Select a rectangular region of the image", "Crop169", CROP_DEFAULTS)


class CropOperation:
    kind = "crop"
    spec = CROP_SPEC
    helpers = ()

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
