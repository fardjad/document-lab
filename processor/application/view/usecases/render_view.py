from dataclasses import replace

try:
    from application.view.ports.operation_registry import OperationRegistry
    from application.view.ports.view_store import ProjectViewStore
    from application.view.usecases.project_lookup import project_id_or_not_found
    from model.pipeline import Pipeline
    from model.project import ProjectNotFound
    from model.view import ViewNotFound
    from model.rendered_region import RenderedRegion
except ImportError:
    from ..ports.operation_registry import OperationRegistry
    from ..ports.view_store import ProjectViewStore
    from .project_lookup import project_id_or_not_found
    from ....model.pipeline import Pipeline
    from ....model.project import ProjectNotFound
    from ....model.view import ViewNotFound
    from ....model.rendered_region import RenderedRegion


class ViewRenderError(ValueError):
    """View cannot be rendered as a valid image."""


class RenderView:
    def __init__(self, views: ProjectViewStore, image_reader, image_sizes, registry: OperationRegistry) -> None:
        self._views = views
        self._image_reader = image_reader
        self._image_sizes = image_sizes
        self._registry = registry

    def render(self, raw_project_id: str, view_id: int) -> bytes:
        view, image, size = self._load(raw_project_id, view_id)
        return self._render_view(image, size, view)

    def preview(self, raw_project_id: str, view_id: int, pipeline: Pipeline) -> bytes:
        view, image, size = self._load(raw_project_id, view_id)
        return self._render_view(image, size, replace(view, pipeline=pipeline))

    def _load(self, raw_project_id: str, view_id: int):
        project_id = project_id_or_not_found(raw_project_id)
        selected = self._views.read_project_views(project_id).find_view(view_id)
        if selected is None:
            raise ViewNotFound("View not found")
        return selected, self._image_reader.read(raw_project_id), self._image_sizes.read(raw_project_id)

    def _render_view(self, image, size, view) -> bytes:
        try:
            width, height = size
            rendered = RenderedRegion(image.data, width, height)
            for op in view.pipeline.operations:
                rendered = self._registry.get(op.kind).render(rendered, op.options)
            return rendered.image
        except (ProjectNotFound, ViewNotFound):
            raise
        except Exception as error:
            raise ViewRenderError("Unable to render view") from error
