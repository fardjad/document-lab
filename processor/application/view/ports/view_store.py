from typing import Protocol

try:
    from model.project import ProjectId
    from model.view import ProjectViews
except ImportError:
    from ....model.project import ProjectId
    from ....model.view import ProjectViews


class ProjectViewStore(Protocol):
    def read_project_views(self, project_id: ProjectId) -> ProjectViews: ...
    def write_project_views(self, project_id: ProjectId, views: ProjectViews) -> None: ...
