from dataclasses import dataclass, replace
import re

try:
    from model.view import View, ViewNotFound
except ImportError:
    from .view import View, ViewNotFound


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
    next_view_id: int = 1
    views: tuple[View, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.id, ProjectId):
            raise ValueError("Invalid project ID")
        if not isinstance(self.image, ProjectImage):
            raise ValueError("Invalid project image")
        if isinstance(self.next_view_id, bool) or not isinstance(self.next_view_id, int) or self.next_view_id < 1:
            raise ValueError("Invalid next view ID")
        object.__setattr__(self, "views", tuple(self.views))
        if any(not isinstance(item, View) for item in self.views):
            raise ValueError("Invalid views")
        ids = [item.id for item in self.views]
        if len(ids) != len(set(ids)) or self.next_view_id <= max(ids, default=0):
            raise ValueError("Invalid view IDs")

    def find_view(self, view_id: int) -> View | None:
        return next((item for item in self.views if item.id == view_id), None)

    def add_view(self, view: View) -> "Project":
        return replace(self, next_view_id=max(self.next_view_id, view.id + 1), views=self.views + (view,))

    def replace_view(self, view: View) -> "Project":
        if self.find_view(view.id) is None:
            raise ViewNotFound("View not found")
        return replace(self, views=tuple(view if item.id == view.id else item for item in self.views))

    def remove_view(self, view_id: int) -> "Project":
        if self.find_view(view_id) is None:
            raise ViewNotFound("View not found")
        return replace(self, views=tuple(item for item in self.views if item.id != view_id))
