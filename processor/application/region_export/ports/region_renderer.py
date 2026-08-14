from typing import Protocol

try:
    from model.project import CropRegion, ProjectImage
except ImportError:
    from ....model.project import CropRegion, ProjectImage


class RegionRenderer(Protocol):
    def render(self, image: ProjectImage, crop: CropRegion) -> bytes: ...
