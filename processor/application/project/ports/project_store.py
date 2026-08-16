from collections.abc import Iterable
from typing import Protocol

try:
    from model.project import ProjectId, ProjectImage
except ImportError:
    from ....model.project import ProjectId, ProjectImage


class ProjectStore(Protocol):
    """Outbound contract for discovering projects and reading their source images."""

    def list_project_ids(self) -> Iterable[ProjectId]: ...

    def read_project_image(self, project_id: ProjectId) -> ProjectImage: ...

    def read_project_image_size(self, project_id: ProjectId) -> tuple[int, int]: ...

    def read_project_name(self, project_id: ProjectId) -> str: ...


class ProjectWriter(Protocol):
    """Outbound contract for mutating project content on disk."""

    def create_project(self, project_id: ProjectId, image: ProjectImage) -> None: ...

    def replace_project_image(self, project_id: ProjectId, image: ProjectImage) -> None: ...

    def delete_project(self, project_id: ProjectId) -> None: ...

    def rename_project(self, project_id: ProjectId, name: str) -> None: ...
