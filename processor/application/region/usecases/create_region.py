try:
    from application.region.ports.region_store import ProjectRegionStore
    from application.region.usecases.project_lookup import project_id_or_not_found
    from application.region.usecases.region_lock import region_write_lock
    from model.pipeline import Pipeline
    from model.region import CropRectangle, CropRegion
except ImportError:
    from ..ports.region_store import ProjectRegionStore
    from .project_lookup import project_id_or_not_found
    from .region_lock import region_write_lock
    from ....model.pipeline import Pipeline
    from ....model.region import CropRectangle, CropRegion


class CreateRegion:
    """Create a region with an identity pipeline."""

    def __init__(self, regions: ProjectRegionStore, image_sizes) -> None:
        self._regions = regions
        self._image_sizes = image_sizes

    def create(self, raw_project_id: str, rectangle: CropRectangle) -> CropRegion:
        project_id = project_id_or_not_found(raw_project_id)
        with region_write_lock():
            current = self._regions.read_project_regions(project_id)
            width, height = self._image_sizes.read(raw_project_id)
            if not rectangle.within_image(width, height):
                raise ValueError("Crop rectangle outside image")
            created = CropRegion(current.next_region_id, f"Region {current.next_region_id}", rectangle, Pipeline())
            self._regions.write_project_regions(project_id, current.add(created))
            return created