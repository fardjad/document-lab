try:
    from application.region.ports.region_store import ProjectRegionStore
    from application.region.usecases.project_lookup import project_id_or_not_found
    from application.region.usecases.region_lock import region_write_lock
    from model.region import RegionNotFound
except ImportError:
    from ..ports.region_store import ProjectRegionStore
    from .project_lookup import project_id_or_not_found
    from .region_lock import region_write_lock
    from ....model.region import RegionNotFound


class DeleteRegion:
    """Remove a region and its pipeline from a project."""

    def __init__(self, regions: ProjectRegionStore) -> None:
        self._regions = regions

    def delete(self, raw_project_id: str, region_id: int) -> None:
        project_id = project_id_or_not_found(raw_project_id)
        with region_write_lock():
            current = self._regions.read_project_regions(project_id)
            self._regions.write_project_regions(project_id, current.remove(region_id))


