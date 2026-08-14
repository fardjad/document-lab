from dataclasses import dataclass
import os
from pathlib import Path


DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


@dataclass(frozen=True)
class Settings:
    project_root: Path
    cors_origins: list[str]

    @classmethod
    def from_environment(cls) -> "Settings":
        configured = os.getenv("CORS_ORIGINS")
        origins = [item.strip() for item in configured.split(",") if item.strip()] if configured else DEFAULT_CORS_ORIGINS.copy()
        return cls((Path(__file__).resolve().parents[2] / "projects").resolve(), origins)
