from io import BytesIO
import math

from PIL import Image, UnidentifiedImageError

try:
    from model.project import CropRegion, ProjectImage
except ImportError:
    from ...model.project import CropRegion, ProjectImage


class PillowRegionRenderer:
    def render(self, image: ProjectImage, crop: CropRegion) -> bytes:
        try:
            with Image.open(BytesIO(image.data)) as source:
                source_rgba = source.convert("RGBA")
                width, height = source_rgba.size
                left = math.floor(crop.rectangle.x * width)
                top = math.floor(crop.rectangle.y * height)
                right = math.ceil((crop.rectangle.x + crop.rectangle.width) * width)
                bottom = math.ceil((crop.rectangle.y + crop.rectangle.height) * height)
                result = source_rgba.crop((left, top, right, bottom))
                if crop.rotation:
                    result = result.rotate(-crop.rotation, expand=True)
                if crop.straighten:
                    result = result.rotate(-crop.straighten, expand=True)
                trim = crop.trim
                final_width = result.width - trim.left - trim.right
                final_height = result.height - trim.top - trim.bottom
                if final_width <= 0 or final_height <= 0:
                    raise ValueError("Region trim removes entire output")
                result = result.crop((trim.left, trim.top, result.width - trim.right, result.height - trim.bottom))
                output = BytesIO()
                result.save(output, format="PNG")
                return output.getvalue()
        except (UnidentifiedImageError, OSError, ValueError) as error:
            raise ValueError("Unable to render region") from error
