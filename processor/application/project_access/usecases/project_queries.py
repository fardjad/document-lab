from collections.abc import Iterable

try:
    from model.project import ProjectId, ProjectImage, ProjectNotFound
    from application.project_access.ports.project_source import ProjectSource
except ImportError:
    from ....model.project import ProjectId, ProjectImage, ProjectNotFound
    from ..ports.project_source import ProjectSource


class ProjectQueries:
    def __init__(self, source: ProjectSource) -> None:
        self._source = source

    def list_projects(self) -> list[str]:
        return sorted(str(project_id) for project_id in self._source.list_project_ids())

    def read_project_image(self, raw_project_id: str) -> ProjectImage:
        try:
            project_id = ProjectId(raw_project_id)
        except ValueError as error:
            raise ProjectNotFound("Project not found") from error
        return self._source.read_project_image(project_id)
