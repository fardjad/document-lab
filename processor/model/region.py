from dataclasses import dataclass
import math
from numbers import Real

try:
    from model.pipeline import Pipeline
except ImportError:
    from .pipeline import Pipeline


class RegionNotFound(LookupError):
    """Requested crop region does not exist."""


@dataclass(frozen=True)
class CropRectangle:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        values = (self.x, self.y, self.width, self.height)
        if any(isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) for value in values):
            raise ValueError("Invalid crop rectangle")
        if self.x < 0 or self.y < 0 or self.width <= 0 or self.height <= 0:
            raise ValueError("Invalid crop rectangle")

    def within_image(self, image_width: int, image_height: int) -> bool:
        """Whether the normalized rectangle fits inside the source image."""

        return self.x + self.width <= 1 and self.y + self.height <= 1


@dataclass(frozen=True)
class CropRegion:
    id: int
    name: str
    rectangle: CropRectangle
    pipeline: Pipeline = Pipeline()

    def __post_init__(self) -> None:
        if isinstance(self.id, bool) or not isinstance(self.id, int) or self.id < 1:
            raise ValueError("Invalid region ID")
        if not isinstance(self.name, str):
            raise ValueError("Invalid region name")
        name = self.name.strip()
        if not name or len(name) > 100 or any(not char.isprintable() for char in name):
            raise ValueError("Invalid region name")
        object.__setattr__(self, "name", name)
        if not isinstance(self.rectangle, CropRectangle):
            raise ValueError("Invalid crop rectangle")
        if not isinstance(self.pipeline, Pipeline):
            raise ValueError("Invalid region pipeline")

    def with_pipeline(self, pipeline: Pipeline) -> "CropRegion":
        """The same region bound to a different pipeline, for updates and previews."""

        return CropRegion(self.id, self.name, self.rectangle, pipeline)


@dataclass(frozen=True)
class ProjectRegions:
    next_region_id: int
    regions: tuple[CropRegion, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.next_region_id, bool) or not isinstance(self.next_region_id, int) or self.next_region_id < 1:
            raise ValueError("Invalid next region ID")
        object.__setattr__(self, "regions", tuple(self.regions))
        if any(not isinstance(item, CropRegion) for item in self.regions):
            raise ValueError("Invalid regions")
        ids = [item.id for item in self.regions]
        if len(ids) != len(set(ids)) or self.next_region_id <= max(ids, default=0):
            raise ValueError("Invalid region IDs")

    def find(self, region_id: int) -> CropRegion | None:
        """The region with the given ID, if present."""

        return next((item for item in self.regions if item.id == region_id), None)

    def add(self, region: CropRegion) -> "ProjectRegions":
        """Collection plus a new region; IDs stay unique and never reused."""

        return ProjectRegions(max(self.next_region_id, region.id + 1), self.regions + (region,))

    def replace(self, region: CropRegion) -> "ProjectRegions":
        """Collection with one region replaced by ID."""

        if self.find(region.id) is None:
            raise RegionNotFound("Region not found")
        return ProjectRegions(self.next_region_id, tuple(region if item.id == region.id else item for item in self.regions))

    def remove(self, region_id: int) -> "ProjectRegions":
        """Collection without the region with the given ID."""

        if self.find(region_id) is None:
            raise RegionNotFound("Region not found")
        return ProjectRegions(self.next_region_id, tuple(item for item in self.regions if item.id != region_id))