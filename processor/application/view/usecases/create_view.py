try:
    from application.view.ports.view_store import ProjectViewStore
    from application.view.usecases.project_lookup import project_id_or_not_found
    from application.view.usecases.view_lock import view_write_lock
    from model.pipeline import Pipeline
    from model.view import View
except ImportError:
    from ..ports.view_store import ProjectViewStore
    from .project_lookup import project_id_or_not_found
    from .view_lock import view_write_lock
    from ....model.pipeline import Pipeline
    from ....model.view import View


class CreateView:
    """Create a view with an identity pipeline."""

    def __init__(self, views: ProjectViewStore) -> None:
        self._views = views

    def create(self, raw_project_id: str, name: str, pipeline: Pipeline | None = None) -> View:
        project_id = project_id_or_not_found(raw_project_id)
        with view_write_lock():
            current = self._views.read_project_views(project_id)
            created = View(current.next_view_id, name, pipeline or Pipeline())
            self._views.write_project_views(project_id, current.add_view(created))
            return created
