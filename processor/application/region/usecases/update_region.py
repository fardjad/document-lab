try:
    from application.region.ports.operation_registry import OperationRegistry
    from application.region.ports.region_store import ProjectRegionStore
    from application.region.usecases.project_lookup import project_id_or_not_found
    from application.region.usecases.region_lock import region_write_lock
    from model.project import ProjectNotFound
    from model.pipeline import Pipeline
    from model.region import CropRectangle, CropRegion, RegionNotFound
except ImportError:
    from ..ports.operation_registry import OperationRegistry
    from ..ports.region_store import ProjectRegionStore
    from .project_lookup import project_id_or_not_found
    from .region_lock import region_write_lock
    from ....model.project import ProjectNotFound
    from ....model.pipeline import Pipeline
    from ....model.region import CropRectangle, CropRegion, RegionNotFound


class UpdateRegion:
    """Replace a region's name, rectangle, and pipeline.

    Saving or updating a region persists the pipeline: a full pipeline is part
    of the update payload, so rotate, straighten, trim, and background removal
    are saved together.  Each operation's option schema is validated via its
    executor before persisting.
    """

    def __init__(self, regions: ProjectRegionStore, image_sizes, registry: OperationRegistry) -> None:
        self._regions = regions
        self._image_sizes = image_sizes
        self._registry = registry

    def update(self, raw_project_id: str, region_id: int, name: str, rectangle: CropRectangle, pipeline: Pipeline) -> CropRegion:
        project_id = project_id_or_not_found(raw_project_id)
        with region_write_lock():
            current = self._regions.read_project_regions(project_id)
            width, height = self._image_sizes.read(raw_project_id)
            if not rectangle.within_image(width, height):
                raise ValueError("Crop rectangle outside image")
            for op in pipeline.operations:
                executor = self._registry.get(op.kind)
                executor.validate(op.options)
            updated_region = CropRegion(region_id, name, rectangle, pipeline)
            if current.find(region_id) is None:
                raise RegionNotFound("Region not found")
            self._regions.write_project_regions(project_id, current.replace(updated_region))
            return updated_region