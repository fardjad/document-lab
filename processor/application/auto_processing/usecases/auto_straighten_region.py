try:
    from application.auto_processing.ports.document_analyzers import DocumentStraightener
    from application.auto_processing.results import AutoProcessingResult
    from application.region.ports.operation_registry import OperationRegistry
    from application.region.ports.region_store import ProjectRegionStore, RegionCropper
    from application.region.usecases.project_lookup import project_id_or_not_found
    from model.region import RegionNotFound
except ImportError:
    from ..ports.document_analyzers import DocumentStraightener
    from ..results import AutoProcessingResult
    from ...region.ports.operation_registry import OperationRegistry
    from ...region.ports.region_store import ProjectRegionStore, RegionCropper
    from ...region.usecases.project_lookup import project_id_or_not_found
    from ....model.region import RegionNotFound


class AutoStraightenRegion:
    """Suggest a straighten angle for a region without persisting it.

    The region is rendered with straighten and trim removed from its pipeline
    (so the analyzer sees a pre-straighten, pre-trim crop), then the bytes are
    passed to the straightener port.
    """

    def __init__(self, regions: ProjectRegionStore, image_reader, cropper: RegionCropper, registry: OperationRegistry, straightener: DocumentStraightener) -> None:
        self._regions = regions
        self._image_reader = image_reader
        self._cropper = cropper
        self._registry = registry
        self._straightener = straightener

    def suggest(self, raw_project_id: str, region_id: int) -> AutoProcessingResult:
        project_id = project_id_or_not_found(raw_project_id)
        project_regions = self._regions.read_project_regions(project_id)
        selected = project_regions.find(region_id)
        if selected is None:
            raise RegionNotFound("Region not found")
        image = self._image_reader.read(raw_project_id)
        pipeline = selected.pipeline.without("straighten", "trim")
        rendered = self._cropper.crop(image.data, selected.rectangle)
        for op in pipeline.operations:
            executor = self._registry.get(op.kind)
            rendered = executor.render(rendered, op.options)
        return self._straightener.detect_skew(rendered.image)