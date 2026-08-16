from __future__ import annotations

try:
    from application.project.ports.project_store import ProjectStore
    from model.project import ProjectId
except ImportError:
    from ..ports.project_store import ProjectStore
    from ....model.project import ProjectId


class ListProjects:
    """List discoverable project identifiers."""

    def __init__(self, store: ProjectStore) -> None:
        self._store = store

    def list(self) -> list[str]:
        return sorted(str(project_id) for project_id in self._store.list_project_ids())

    def list_with_names(self) -> list[dict[str, str]]:
        return [{"id": project_id, "name": self._store.read_project_name(ProjectId(project_id))} for project_id in self.list()]
