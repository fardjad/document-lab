import re

try:
    from application.project.ports.project_store import ProjectStore, ProjectWriter
    from model.project import ProjectId, ProjectNotFound
except ImportError:
    from ..ports.project_store import ProjectStore, ProjectWriter
    from ....model.project import ProjectId, ProjectNotFound


class RenameProject:
    """Validate and persist a project's display name without changing its ID."""

    def __init__(self, store: ProjectStore, writer: ProjectWriter) -> None:
        self._store = store
        self._writer = writer

    def rename(self, raw_project_id: str, raw_name: str) -> str:
        try:
            project_id = ProjectId(raw_project_id)
        except ValueError as error:
            raise ProjectNotFound("Project not found") from error
        if not isinstance(raw_name, str):
            raise ValueError("Invalid project name")
        name = raw_name.strip()
        if not name or len(name) > 100 or re.search(r"[\x00-\x1f\x7f]", name):
            raise ValueError("Invalid project name")
        if project_id.value not in {str(item) for item in self._store.list_project_ids()}:
            raise ProjectNotFound("Project not found")
        self._writer.rename_project(project_id, name)
        return name
