try:
    from application.region.ports.region_store import ProjectRegionStore
    from model.project import ProjectId, ProjectNotFound
    from model.region import ProjectRegions
except ImportError:
    from ..ports.region_store import ProjectRegionStore
    from ....model.project import ProjectId, ProjectNotFound
    from ....model.region import ProjectRegions


class ListRegions:
    """List the regions of a project."""

    def __init__(self, regions: ProjectRegionStore) -> None:
        self._regions = regions

    def list(self, raw_project_id: str) -> ProjectRegions:
        return self._regions.read_project_regions(self._project_id(raw_project_id))

    def _project_id(self, raw_project_id: str) -> ProjectId:
        try:
            return ProjectId(raw_project_id)
        except ValueError as error:
            raise ProjectNotFound("Project not found") from error
