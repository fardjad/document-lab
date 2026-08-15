import math
from io import BytesIO

from PIL import Image

try:
    from model.region import CropRectangle
    from model.rendered_region import RenderedRegion
except ImportError:
    from ...model.region import CropRectangle
    from ...model.rendered_region import RenderedRegion


class PillowRegionCropper:
    """Crops a source image to a normalized rectangle, returning a RenderedRegion.

    This is the only PIL crop logic in the system; it does not know about
    operations.
    """

    def crop(self, image: bytes, rectangle: CropRectangle) -> RenderedRegion:
        with Image.open(BytesIO(image)) as source:
            source = source.convert("RGBA")
            width, height = source.size
            left = math.floor(rectangle.x * width)
            top = math.floor(rectangle.y * height)
            right = math.ceil((rectangle.x + rectangle.width) * width)
            bottom = math.ceil((rectangle.y + rectangle.height) * height)
            cropped = source.crop((left, top, right, bottom))
            output = BytesIO()
            cropped.save(output, format="PNG")
            crop_width = right - left
            crop_height = bottom - top
            return RenderedRegion(output.getvalue(), crop_width, crop_height)