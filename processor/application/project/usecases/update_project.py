try:
    from application.project.ports.project_store import ProjectStore, ProjectWriter
    from model.project import ProjectId, ProjectImage, ProjectNotFound
except ImportError:
    from ..ports.project_store import ProjectStore, ProjectWriter
    from ....model.project import ProjectId, ProjectImage, ProjectNotFound


class UpdateProject:
    """Replace a project's source image.

    Region geometry is normalized to the source image, so replacing the image
    invalidates view pipelines; views are reset to the empty collection.
    """

    def __init__(self, store: ProjectStore, writer: ProjectWriter) -> None:
        self._store = store
        self._writer = writer

    def update(self, raw_project_id: str, image: ProjectImage) -> None:
        try:
            project_id = ProjectId(raw_project_id)
        except ValueError as error:
            raise ProjectNotFound("Project not found") from error
        existing = {str(item) for item in self._store.list_project_ids()}
        if project_id.value not in existing:
            raise ProjectNotFound("Project not found")
        self._writer.replace_project_image(project_id, image)
