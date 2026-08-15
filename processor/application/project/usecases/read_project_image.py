try:
    from application.project.usecases.project_lookup import project_id_or_not_found
    from model.project import ProjectImage
except ImportError:
    from .project_lookup import project_id_or_not_found
    from ....model.project import ProjectImage


class ReadProjectImage:
    """Read a project's source image."""

    def __init__(self, store) -> None:
        self._store = store

    def read(self, raw_project_id: str) -> ProjectImage:
        return self._store.read_project_image(project_id_or_not_found(raw_project_id))
