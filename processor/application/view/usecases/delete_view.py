try:
    from application.view.ports.view_store import ProjectViewStore
    from application.view.ports.render_cache import RenderCache
    from application.view.usecases.project_lookup import project_id_or_not_found
    from application.view.usecases.view_lock import view_write_lock
    from model.view import ViewNotFound
except ImportError:
    from ..ports.view_store import ProjectViewStore
    from ..ports.render_cache import RenderCache
    from .project_lookup import project_id_or_not_found
    from .view_lock import view_write_lock
    from ....model.view import ViewNotFound


class DeleteView:
    """Remove a view and its pipeline from a project."""

    def __init__(self, views: ProjectViewStore, cache: RenderCache | None = None) -> None:
        self._views = views
        self._cache = cache

    def delete(self, raw_project_id: str, view_id: int) -> None:
        project_id = project_id_or_not_found(raw_project_id)
        with view_write_lock():
            current = self._views.read_project_views(project_id)
            self._views.write_project_views(project_id, current.remove_view(view_id))
            if self._cache is not None:
                self._cache.cleanup_view(project_id, view_id, set())
