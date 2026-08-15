try:
    from application.project_access.ports.project_source import ProjectSource
    from application.region_background.ports.background_remover import BackgroundRemover
    from application.region_export.ports.region_renderer import RegionRenderer
    from application.region_management.ports.project_region_store import ProjectRegionStore
    from model.project import BackgroundRemoval, ProjectId, ProjectNotFound, RegionNotFound
except ImportError:
    from ...project_access.ports.project_source import ProjectSource
    from ..ports.background_remover import BackgroundRemover
    from ...region_export.ports.region_renderer import RegionRenderer
    from ...region_management.ports.project_region_store import ProjectRegionStore
    from ....model.project import BackgroundRemoval, ProjectId, ProjectNotFound, RegionNotFound


class BackgroundRemovalError(ValueError):
    """Region cannot be rendered with background removal."""


class RegionBackgroundRemoval:
    def __init__(self, source: ProjectSource, regions: ProjectRegionStore, renderer: RegionRenderer, remover: BackgroundRemover) -> None:
        self._source = source
        self._regions = regions
        self._renderer = renderer
        self._remover = remover

    def preview(self, raw_project_id: str, region_id: int, settings: BackgroundRemoval) -> bytes:
        if not isinstance(settings, BackgroundRemoval):
            raise BackgroundRemovalError("Invalid background removal settings")
        try:
            project_id = ProjectId(raw_project_id)
        except ValueError as error:
            raise ProjectNotFound("Project not found") from error
        project_regions = self._regions.read_project_regions(project_id)
        selected = next((item for item in project_regions.regions if item.id == region_id), None)
        if selected is None:
            raise RegionNotFound("Region not found")
        try:
            rendered = self._renderer.render(self._source.read_project_image(project_id), selected)
        except (ProjectNotFound, RegionNotFound):
            raise
        except Exception as error:
            raise BackgroundRemovalError("Unable to render region") from error
        try:
            return self._remover.remove(rendered, settings)
        except Exception as error:
            raise BackgroundRemovalError("Unable to remove background") from error
