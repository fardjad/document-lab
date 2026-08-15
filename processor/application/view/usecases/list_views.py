try:
    from application.view.ports.view_store import ProjectViewStore
    from model.project import Project, ProjectId, ProjectNotFound
except ImportError:
    from ..ports.view_store import ProjectViewStore
    from ....model.project import Project, ProjectId, ProjectNotFound


class ListViews:
    """List the views of a project."""

    def __init__(self, views: ProjectViewStore) -> None:
        self._views = views

    def list(self, raw_project_id: str) -> Project:
        return self._views.read_project_views(self._project_id(raw_project_id))

    def _project_id(self, raw_project_id: str) -> ProjectId:
        try:
            return ProjectId(raw_project_id)
        except ValueError as error:
            raise ProjectNotFound("Project not found") from error
