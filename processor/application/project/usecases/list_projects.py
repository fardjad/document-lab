try:
    from application.project.ports.project_store import ProjectStore
except ImportError:
    from ..ports.project_store import ProjectStore


class ListProjects:
    """List discoverable project identifiers."""

    def __init__(self, store: ProjectStore) -> None:
        self._store = store

    def list(self) -> list[str]:
        return sorted(str(project_id) for project_id in self._store.list_project_ids())
