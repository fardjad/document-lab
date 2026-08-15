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
