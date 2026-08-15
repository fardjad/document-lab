try:
    from application.project.usecases.project_lookup import project_id_or_not_found
except ImportError:
    from .project_lookup import project_id_or_not_found


class ReadProjectImageSize:
    """Read a project's source image pixel size."""

    def __init__(self, store) -> None:
        self._store = store

    def read(self, raw_project_id: str) -> tuple[int, int]:
        return self._store.read_project_image_size(project_id_or_not_found(raw_project_id))
