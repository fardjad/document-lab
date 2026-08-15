from dataclasses import dataclass
import re

try:
    from model.view import ProjectViews, View
except ImportError:
    from .view import ProjectViews, View


class ProjectNotFound(FileNotFoundError):
    """Requested project or its source image does not exist."""


@dataclass(frozen=True)
class ProjectId:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", self.value):
            raise ValueError("Invalid project ID")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ProjectImage:
    data: bytes

    @classmethod
    def from_png(cls, data: bytes) -> "ProjectImage":
        """Accept only PNG-encoded project images."""

        if not isinstance(data, bytes) or data[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Only PNG project images are supported")
        return cls(data)


@dataclass(frozen=True)
class Project:
    id: ProjectId
    image: ProjectImage
    views: ProjectViews = ProjectViews(1)

    def __post_init__(self) -> None:
        if not isinstance(self.id, ProjectId):
            raise ValueError("Invalid project ID")
        if not isinstance(self.image, ProjectImage):
            raise ValueError("Invalid project image")
        if not isinstance(self.views, ProjectViews):
            raise ValueError("Invalid project views")

    def find_view(self, view_id: int) -> View | None:
        return self.views.find(view_id)

    def add_view(self, view: View) -> "Project":
        return Project(self.id, self.image, self.views.add(view))

    def replace_view(self, view: View) -> "Project":
        return Project(self.id, self.image, self.views.replace(view))

    def remove_view(self, view_id: int) -> "Project":
        return Project(self.id, self.image, self.views.remove(view_id))
