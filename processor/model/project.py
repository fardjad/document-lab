from dataclasses import dataclass
import math
import re
from numbers import Real


class ProjectNotFound(FileNotFoundError):
    """Requested project or its source image does not exist."""


@dataclass(frozen=True)
class ProjectId:
    value: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", self.value):
            raise ValueError("Invalid project ID")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ProjectImage:
    data: bytes


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


@dataclass(frozen=True)
class CropSlice:
    id: int
    name: str
    rectangle: CropRectangle
    rotation: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.id, bool) or not isinstance(self.id, int) or self.id < 1:
            raise ValueError("Invalid slice ID")
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 100 or any(not char.isprintable() for char in self.name):
            raise ValueError("Invalid slice name")
        if not isinstance(self.rectangle, CropRectangle):
            raise ValueError("Invalid crop rectangle")
        if isinstance(self.rotation, bool) or not isinstance(self.rotation, int) or self.rotation % 90 != 0:
            raise ValueError("Invalid slice rotation")
        object.__setattr__(self, "rotation", self.rotation % 360)


@dataclass(frozen=True)
class ProjectSlices:
    next_slice_id: int
    slices: tuple[CropSlice, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.next_slice_id, bool) or not isinstance(self.next_slice_id, int) or self.next_slice_id < 1:
            raise ValueError("Invalid next slice ID")
        object.__setattr__(self, "slices", tuple(self.slices))
        if any(not isinstance(item, CropSlice) for item in self.slices):
            raise ValueError("Invalid slices")
        ids = [item.id for item in self.slices]
        if len(ids) != len(set(ids)) or self.next_slice_id <= max(ids, default=0):
            raise ValueError("Invalid slice IDs")


class SliceNotFound(LookupError):
    """Requested crop slice does not exist."""
