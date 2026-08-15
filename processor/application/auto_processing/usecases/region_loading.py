try:
    from application.auto_processing.results import AutoProcessingResult
    from application.region.ports.region_store import ProjectRegionStore
    from application.region.usecases.project_lookup import project_id_or_not_found
    from model.project import ProjectImage
    from model.region import CropRegion, RegionNotFound
except ImportError:
    from ..results import AutoProcessingResult
    from ...region.ports.region_store import ProjectRegionStore
    from ...region.usecases.project_lookup import project_id_or_not_found
    from ....model.project import ProjectImage
    from ....model.region import CropRegion, RegionNotFound


def loaded_region(regions: ProjectRegionStore, image_reader, raw_project_id: str, region_id: int) -> tuple[CropRegion, ProjectImage]:
    """Resolve a project's region together with its source image."""

    project_id = project_id_or_not_found(raw_project_id)
    project_regions = regions.read_project_regions(project_id)
    selected = project_regions.find(region_id)
    if selected is None:
        raise RegionNotFound("Region not found")
    return selected, image_reader.read(raw_project_id)
