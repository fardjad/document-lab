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

