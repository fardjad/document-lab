from dataclasses import dataclass
import re


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
