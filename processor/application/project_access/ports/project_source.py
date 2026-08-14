from collections.abc import Iterable
from typing import Protocol

try:
    from model.project import ProjectId, ProjectImage
except ImportError:
    from ....model.project import ProjectId, ProjectImage


class ProjectSource(Protocol):
    def list_project_ids(self) -> Iterable[ProjectId]: ...

    def read_project_image(self, project_id: ProjectId) -> ProjectImage: ...
