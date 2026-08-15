from dataclasses import replace
import hashlib
import json

try:
    from application.view.ports.operation_registry import OperationRegistry
    from application.view.ports.view_store import ProjectViewStore
    from application.view.usecases.project_lookup import project_id_or_not_found
    from model.pipeline import Pipeline
    from model.project import ProjectNotFound
    from model.view import ViewNotFound
    from application.view.ports.rendered_region import RenderedRegion
    from application.view.ports.render_cache import RenderCache
except ImportError:
    from ..ports.operation_registry import OperationRegistry
    from ..ports.view_store import ProjectViewStore
    from .project_lookup import project_id_or_not_found
    from ....model.pipeline import Pipeline
    from ....model.project import ProjectNotFound
    from ....model.view import ViewNotFound
    from ..ports.rendered_region import RenderedRegion
    from ..ports.render_cache import RenderCache


class ViewRenderError(ValueError):
    """View cannot be rendered as a valid image."""


def cache_key_for_step(operations, step: int) -> str:
    parts = []
    for operation in operations[: step + 1]:
        if operation.enabled:
            options = json.dumps(operation.options, sort_keys=True)
            options_hash = hashlib.sha256(options.encode()).hexdigest()
            parts.append(f"{operation.kind}:{options_hash}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


class RenderView:
    def __init__(self, views: ProjectViewStore, image_reader, image_sizes, registry: OperationRegistry, cache: RenderCache | None = None) -> None:
        self._views = views
        self._image_reader = image_reader
        self._image_sizes = image_sizes
        self._registry = registry
        self._cache = cache

    def render(self, raw_project_id: str, view_id: int) -> bytes:
        view, image, size = self._load(raw_project_id, view_id)
        return self._render_view(image, size, view, project_id_or_not_found(raw_project_id), use_cache=True)

    def preview(self, raw_project_id: str, view_id: int, pipeline: Pipeline) -> bytes:
        view, image, size = self._load(raw_project_id, view_id)
        return self._render_view(image, size, replace(view, pipeline=pipeline), project_id_or_not_found(raw_project_id), use_cache=False)

    def _load(self, raw_project_id: str, view_id: int):
        project_id = project_id_or_not_found(raw_project_id)
        selected = self._views.read_project_views(project_id).find_view(view_id)
        if selected is None:
            raise ViewNotFound("View not found")
        return selected, self._image_reader.read(raw_project_id), self._image_sizes.read(raw_project_id)

    def _render_view(self, image, size, view, project_id, use_cache: bool) -> bytes:
        try:
            width, height = size
            rendered = RenderedRegion(image.data, width, height)
            for step, op in enumerate(view.pipeline.operations):
                if not op.enabled:
                    continue
                if use_cache and self._cache is not None:
                    cached = self._cache.get(project_id, cache_key_for_step(view.pipeline.operations, step))
                    if cached is not None:
                        rendered = cached
                        continue
                rendered = self._registry.get(op.kind).render(rendered, op.options)
                if use_cache and self._cache is not None:
                    self._cache.put(project_id, cache_key_for_step(view.pipeline.operations, step), rendered)
            return rendered.image
        except (ProjectNotFound, ViewNotFound):
            raise
        except Exception as error:
            raise ViewRenderError("Unable to render view") from error
