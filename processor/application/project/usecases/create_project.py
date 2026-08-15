try:
    from application.project.ports.project_store import ProjectStore, ProjectWriter
    from model.project import ProjectId, ProjectImage, ProjectNotFound
except ImportError:
    from ..ports.project_store import ProjectStore, ProjectWriter
    from ....model.project import ProjectId, ProjectImage, ProjectNotFound


class CreateProject:
    """Create a new filesystem project from an uploaded image."""

    def __init__(self, store: ProjectStore, writer: ProjectWriter) -> None:
        self._store = store
        self._writer = writer

    def create(self, raw_project_id: str, image: ProjectImage) -> ProjectId:
        try:
            project_id = ProjectId(raw_project_id)
        except ValueError as error:
            raise ValueError("Invalid project ID") from error
        existing = {str(item) for item in self._store.list_project_ids()}
        if project_id.value in existing:
            raise ValueError("Project already exists")
        self._writer.create_project(project_id, image)
        return project_id
