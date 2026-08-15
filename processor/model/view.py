from dataclasses import dataclass

try:
    from model.pipeline import Pipeline
except ImportError:
    from .pipeline import Pipeline


class ViewNotFound(LookupError):
    """Requested view does not exist."""


@dataclass(frozen=True)
class View:
    id: int
    name: str
    pipeline: Pipeline = Pipeline()

    def __post_init__(self) -> None:
        if isinstance(self.id, bool) or not isinstance(self.id, int) or self.id < 1:
            raise ValueError("Invalid view ID")
        if not isinstance(self.name, str):
            raise ValueError("Invalid view name")
        name = self.name.strip()
        if not name or len(name) > 100 or any(not char.isprintable() for char in name):
            raise ValueError("Invalid view name")
        object.__setattr__(self, "name", name)
        if not isinstance(self.pipeline, Pipeline):
            raise ValueError("Invalid view pipeline")

    def with_pipeline(self, pipeline: Pipeline) -> "View":
        """The same view bound to a different pipeline, for updates and previews."""

        return View(self.id, self.name, pipeline)


@dataclass(frozen=True)
class ProjectViews:
    next_view_id: int
    views: tuple[View, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.next_view_id, bool) or not isinstance(self.next_view_id, int) or self.next_view_id < 1:
            raise ValueError("Invalid next view ID")
        object.__setattr__(self, "views", tuple(self.views))
        if any(not isinstance(item, View) for item in self.views):
            raise ValueError("Invalid views")
        ids = [item.id for item in self.views]
        if len(ids) != len(set(ids)) or self.next_view_id <= max(ids, default=0):
            raise ValueError("Invalid view IDs")

    def find(self, view_id: int) -> View | None:
        """The view with the given ID, if present."""

        return next((item for item in self.views if item.id == view_id), None)

    def add(self, view: View) -> "ProjectViews":
        """Collection plus a new view; IDs stay unique and never reused."""

        return ProjectViews(max(self.next_view_id, view.id + 1), self.views + (view,))

    def replace(self, view: View) -> "ProjectViews":
        """Collection with one view replaced by ID."""

        if self.find(view.id) is None:
            raise ViewNotFound("View not found")
        return ProjectViews(self.next_view_id, tuple(view if item.id == view.id else item for item in self.views))

    def remove(self, view_id: int) -> "ProjectViews":
        """Collection without the view with the given ID."""

        if self.find(view_id) is None:
            raise ViewNotFound("View not found")
        return ProjectViews(self.next_view_id, tuple(item for item in self.views if item.id != view_id))
