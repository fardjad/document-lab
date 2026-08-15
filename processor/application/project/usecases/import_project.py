try:
    from application.project.ports.project_store import ProjectStore, ProjectWriter
    from model.project import ProjectId, ProjectImage, ProjectNotFound
except ImportError:
    from ..ports.project_store import ProjectStore, ProjectWriter
    from ....model.project import ProjectId, ProjectImage, ProjectNotFound


class ImportProject:
    """Import a project from an external source.

    Stubbed pending definition of the import contract. The use case currently
    validates its identifier and rejects every import so the HTTP surface stays
    explicit instead of silently succeeding.
    """

    def __init__(self, store: ProjectStore, writer: ProjectWriter) -> None:
        self._store = store
        self._writer = writer

    def import_(self, raw_project_id: str, image: ProjectImage) -> ProjectId:
        try:
            project_id = ProjectId(raw_project_id)
        except ValueError as error:
            raise ValueError("Invalid project ID") from error
        raise NotImplementedError("Project import is not available yet")
