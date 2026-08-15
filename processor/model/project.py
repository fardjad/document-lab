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
class RegionTrim:
    top: int = 0
    right: int = 0
    bottom: int = 0
    left: int = 0

    def __post_init__(self) -> None:
        values = (self.top, self.right, self.bottom, self.left)
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values):
            raise ValueError("Invalid region trim")


BACKGROUND_REMOVAL_MODELS = ("birefnet-general", "isnet-general-use", "u2net", "u2netp", "silueta")


@dataclass(frozen=True)
class BackgroundRemoval:
    model: str = "birefnet-general"
    alpha_matting: bool = False
    alpha_matting_foreground_threshold: int = 240
    alpha_matting_background_threshold: int = 10
    alpha_matting_erode_size: int = 10
    post_process_mask: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or self.model not in BACKGROUND_REMOVAL_MODELS:
            raise ValueError("Invalid background removal model")
        if any(not isinstance(value, bool) for value in (self.alpha_matting, self.post_process_mask)):
            raise ValueError("Invalid background removal flag")
        thresholds = (self.alpha_matting_foreground_threshold, self.alpha_matting_background_threshold)
        if any(isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 255 for value in thresholds):
            raise ValueError("Invalid background removal threshold")
        erode = self.alpha_matting_erode_size
        if isinstance(erode, bool) or not isinstance(erode, int) or not 1 <= erode <= 100:
            raise ValueError("Invalid background removal erode size")


@dataclass(frozen=True)
class CropRegion:
    id: int
    name: str
    rectangle: CropRectangle
    rotation: int = 0
    straighten: float = 0.0
    trim: RegionTrim = RegionTrim()
    background_removal: BackgroundRemoval | None = None

    def __post_init__(self) -> None:
        if isinstance(self.id, bool) or not isinstance(self.id, int) or self.id < 1:
            raise ValueError("Invalid region ID")
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 100 or any(not char.isprintable() for char in self.name):
            raise ValueError("Invalid region name")
        if not isinstance(self.rectangle, CropRectangle):
            raise ValueError("Invalid crop rectangle")
        if isinstance(self.rotation, bool) or not isinstance(self.rotation, int) or self.rotation % 90 != 0:
            raise ValueError("Invalid region rotation")
        object.__setattr__(self, "rotation", self.rotation % 360)
        if isinstance(self.straighten, bool) or not isinstance(self.straighten, Real) or not math.isfinite(self.straighten) or abs(self.straighten) > 45:
            raise ValueError("Invalid region straighten")
        tenths = round(self.straighten * 10)
        if abs(self.straighten * 10 - tenths) > 1e-7:
            raise ValueError("Invalid region straighten")
        canonical = round(tenths / 10, 1)
        object.__setattr__(self, "straighten", 0.0 if canonical == 0 else canonical)
        if not isinstance(self.trim, RegionTrim):
            raise ValueError("Invalid region trim")
        if self.background_removal is not None and not isinstance(self.background_removal, BackgroundRemoval):
            raise ValueError("Invalid background removal")


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


class RegionNotFound(LookupError):
    """Requested crop region does not exist."""
