from dataclasses import replace

try:
    from application.region.ports.operation_registry import OperationRegistry
    from application.region.ports.region_store import ProjectRegionStore, RegionCropper
    from application.region.usecases.project_lookup import project_id_or_not_found
    from model.pipeline import Pipeline
    from model.project import ProjectId, ProjectNotFound
    from model.region import RegionNotFound
    from model.rendered_region import RenderedRegion
except ImportError:
    from dataclasses import replace

    from ..ports.operation_registry import OperationRegistry
    from ..ports.region_store import ProjectRegionStore, RegionCropper
    from .project_lookup import project_id_or_not_found
    from ....model.pipeline import Pipeline
    from ....model.project import ProjectId, ProjectNotFound
    from ....model.region import RegionNotFound
    from ....model.rendered_region import RenderedRegion


class RegionRenderError(ValueError):
    """Region cannot be rendered as a valid image."""


class RenderRegion:
    """Render a region by cropping and folding pipeline operations in order.

    Crop is upstream: the cropper produces a ``RenderedRegion`` from the source
    image bytes and the region rectangle. Each operation executor then transforms
    that ``RenderedRegion`` in sequence. A preview is the same render with an
    override pipeline bound before rendering.
    """

    def __init__(self, regions: ProjectRegionStore, image_reader, cropper: RegionCropper, registry: OperationRegistry) -> None:
        self._regions = regions
        self._image_reader = image_reader
        self._cropper = cropper
        self._registry = registry

    def render(self, raw_project_id: str, region_id: int) -> bytes:
        region, image, _ = self._load(raw_project_id, region_id)
        return self._render_region(image, region)

    def preview(self, raw_project_id: str, region_id: int, pipeline: Pipeline) -> bytes:
        """Render with an override pipeline; a preview is a render with overridden operations."""

        region, image, _ = self._load(raw_project_id, region_id)
        draft = replace(region, pipeline=pipeline)
        return self._render_region(image, draft)

    def _load(self, raw_project_id: str, region_id: int):
        project_id = project_id_or_not_found(raw_project_id)
        project_regions = self._regions.read_project_regions(project_id)
        selected = project_regions.find(region_id)
        if selected is None:
            raise RegionNotFound("Region not found")
        return selected, self._image_reader.read(raw_project_id), project_id

    def _render_region(self, image, region) -> bytes:
        try:
            rendered = self._cropper.crop(image.data, region.rectangle)
            for op in region.pipeline.operations:
                executor = self._registry.get(op.kind)
                rendered = executor.render(rendered, op.options)
            return rendered.image
        except (ProjectNotFound, RegionNotFound):
            raise
        except Exception as error:
            raise RegionRenderError("Unable to render region") from error