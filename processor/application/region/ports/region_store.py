from typing import Protocol

try:
    from model.project import ProjectId
    from model.region import CropRectangle, ProjectRegions
    from model.rendered_region import RenderedRegion
except ImportError:
    from ....model.project import ProjectId
    from ....model.region import CropRectangle, ProjectRegions
    from ....model.rendered_region import RenderedRegion


class ProjectRegionStore(Protocol):
    """Outbound contract for reading and writing project region metadata."""

    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions: ...

    def write_project_regions(self, project_id: ProjectId, regions: ProjectRegions) -> None: ...


class RegionCropper(Protocol):
    """Outbound contract for cropping a source image down to a region."""

    def crop(self, image: bytes, rectangle: CropRectangle) -> RenderedRegion: ...