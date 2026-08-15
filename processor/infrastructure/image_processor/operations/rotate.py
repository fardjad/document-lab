from io import BytesIO

from PIL import Image

try:
    from model.rendered_region import RenderedRegion
except ImportError:
    from ....model.rendered_region import RenderedRegion


class RotateExecutor:
    """Quarter-turn rotation executor.

    Rotates the rendered region by a multiple of 90 degrees. Odd quarters
    (90, 270) swap width and height.
    """

    kind = "rotate"

    def validate(self, options: dict) -> dict:
        degrees = options.get("degrees")
        if isinstance(degrees, bool) or not isinstance(degrees, int) or degrees % 90 != 0:
            raise ValueError("Invalid rotate degrees")
        return {"degrees": degrees % 360}

    def render(self, region: RenderedRegion, options: dict) -> RenderedRegion:
        degrees = options["degrees"]
        if degrees == 0:
            return RenderedRegion(region.image, region.width, region.height)
        with Image.open(BytesIO(region.image)) as image:
            image = image.convert("RGBA")
            if degrees == 90:
                rotated = image.transpose(Image.Transpose.ROTATE_270)
            elif degrees == 180:
                rotated = image.transpose(Image.Transpose.ROTATE_180)
            elif degrees == 270:
                rotated = image.transpose(Image.Transpose.ROTATE_90)
            else:
                rotated = image
            output = BytesIO()
            rotated.save(output, format="PNG")
            new_w, new_h = rotated.size
            return RenderedRegion(output.getvalue(), new_w, new_h)