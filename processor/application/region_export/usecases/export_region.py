try:
    from application.project_access.ports.project_source import ProjectSource
    from application.region_background.ports.background_remover import BackgroundRemover
    from application.region_management.ports.project_region_store import ProjectRegionStore
    from application.region_export.ports.region_renderer import RegionRenderer
    from model.project import ProjectId, ProjectNotFound, RegionNotFound
except ImportError:
    from ...project_access.ports.project_source import ProjectSource
    from ...region_background.ports.background_remover import BackgroundRemover
    from ...region_management.ports.project_region_store import ProjectRegionStore
    from ..ports.region_renderer import RegionRenderer
    from ....model.project import ProjectId, ProjectNotFound, RegionNotFound


class RegionRenderError(ValueError):
    """Region cannot be rendered as a valid image."""


class RegionExport:
    def __init__(self, source: ProjectSource, regions: ProjectRegionStore, renderer: RegionRenderer, background_remover: BackgroundRemover | None = None) -> None:
        self._source = source
        self._regions = regions
        self._renderer = renderer
        self._background_remover = background_remover

    def export(self, raw_project_id: str, region_id: int) -> bytes:
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
            if selected.background_removal is not None and self._background_remover is not None:
                rendered = self._background_remover.remove(rendered, selected.background_removal)
            return rendered
        except (ProjectNotFound, RegionNotFound):
            raise
        except Exception as error:
            raise RegionRenderError("Unable to render region") from error
