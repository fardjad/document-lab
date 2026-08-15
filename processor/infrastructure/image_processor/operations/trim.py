from io import BytesIO

from PIL import Image

try:
    from model.rendered_region import RenderedRegion
    from application.view.ports.operation_spec import OperationSpec
except ImportError:
    from ....model.rendered_region import RenderedRegion
    from ....application.view.ports.operation_spec import OperationSpec


def _trim(options: dict) -> dict:
    for edge in ("top", "right", "bottom", "left"):
        value = options.get(edge)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("Invalid trim edge")
    return {edge: options[edge] for edge in ("top", "right", "bottom", "left")}


TRIM_SPEC = OperationSpec("trim", {edge: "non-negative int" for edge in ("top", "right", "bottom", "left")}, _trim)


class TrimExecutor:
    """Border-trimming executor.

    Crops pixels from each edge. Rejects trim that would remove the entire
    output.
    """

    kind = "trim"
    spec = TRIM_SPEC

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
