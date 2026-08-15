try:
    from application.auto_processing.ports.document_analyzers import DocumentTrimmer
    from application.auto_processing.results import AutoProcessingResult
    from application.region.ports.operation_registry import OperationRegistry
    from application.region.ports.region_store import ProjectRegionStore, RegionCropper
    from application.region.usecases.project_lookup import project_id_or_not_found
    from model.region import RegionNotFound
except ImportError:
    from ..ports.document_analyzers import DocumentTrimmer
    from ..results import AutoProcessingResult
    from ...region.ports.operation_registry import OperationRegistry
    from ...region.ports.region_store import ProjectRegionStore, RegionCropper
    from ...region.usecases.project_lookup import project_id_or_not_found
    from ....model.region import RegionNotFound


class AutoTrimRegion:
    """Suggest trim edges for a region without persisting it.

    The region is rendered with its full pipeline (crop then fold operations),
    then the bytes are passed to the trimmer port.
    """

    def __init__(self, regions: ProjectRegionStore, image_reader, cropper: RegionCropper, registry: OperationRegistry, trimmer: DocumentTrimmer) -> None:
        self._regions = regions
        self._image_reader = image_reader
        self._cropper = cropper
        self._registry = registry
        self._trimmer = trimmer

    def suggest(self, raw_project_id: str, region_id: int) -> AutoProcessingResult:
        project_id = project_id_or_not_found(raw_project_id)
        project_regions = self._regions.read_project_regions(project_id)
        selected = project_regions.find(region_id)
        if selected is None:
            raise RegionNotFound("Region not found")
        image = self._image_reader.read(raw_project_id)
        rendered = self._cropper.crop(image.data, selected.rectangle)
        for op in selected.pipeline.operations:
            executor = self._registry.get(op.kind)
            rendered = executor.render(rendered, op.options)
        return self._trimmer.detect_trim(rendered.image)