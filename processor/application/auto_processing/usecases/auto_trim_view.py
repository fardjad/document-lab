try:
    from application.auto_processing.ports.document_analyzers import DocumentTrimmer
    from application.auto_processing.results import AutoProcessingResult
    from application.view.ports.operation_registry import OperationRegistry
    from application.view.ports.view_store import ProjectViewStore
    from application.view.usecases.project_lookup import project_id_or_not_found
    from model.rendered_region import RenderedRegion
    from model.view import ViewNotFound
except ImportError:
    from ..ports.document_analyzers import DocumentTrimmer
    from ..results import AutoProcessingResult
    from ...view.ports.operation_registry import OperationRegistry
    from ...view.ports.view_store import ProjectViewStore
    from ...view.usecases.project_lookup import project_id_or_not_found
    from ....model.rendered_region import RenderedRegion
    from ....model.view import ViewNotFound


class AutoTrimView:
    def __init__(self, views: ProjectViewStore, image_reader, image_sizes, registry: OperationRegistry, trimmer: DocumentTrimmer) -> None:
        self._views, self._image_reader, self._image_sizes, self._registry, self._trimmer = views, image_reader, image_sizes, registry, trimmer

    def suggest(self, raw_project_id: str, view_id: int) -> AutoProcessingResult:
        project_id = project_id_or_not_found(raw_project_id)
        selected = self._views.read_project_views(project_id).find_view(view_id)
        if selected is None:
            raise ViewNotFound("View not found")
        image = self._image_reader.read(raw_project_id)
        width, height = self._image_sizes.read(raw_project_id)
        rendered = RenderedRegion(image.data, width, height)
        for op in selected.pipeline.operations:
            rendered = self._registry.get(op.kind).render(rendered, op.options)
        return self._trimmer.detect_trim(rendered.image)
