from typing import Protocol

try:
    from model.project import Project, ProjectId
except ImportError:
    from ....model.project import Project, ProjectId


class ProjectViewStore(Protocol):
    def read_project_views(self, project_id: ProjectId) -> Project: ...
    def write_project_views(self, project_id: ProjectId, project: Project) -> None: ...
