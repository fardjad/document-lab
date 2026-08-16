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
    cache_ttl_seconds: int = 86400
    extension_root: Path | None = None
    extensions_registry_path: Path | None = None

    def __post_init__(self) -> None:
        if self.extension_root is None:
            object.__setattr__(self, "extension_root", Path(__file__).resolve().parents[2] / "extensions")

    @classmethod
    def from_environment(cls) -> "Settings":
        configured = os.getenv("CORS_ORIGINS")
        origins = [item.strip() for item in configured.split(",") if item.strip()] if configured else DEFAULT_CORS_ORIGINS.copy()
        default_root = Path(__file__).resolve().parents[2] / "projects"
        project_root = Path(os.path.expandvars(os.path.expanduser(os.getenv("PROJECTS_ROOT", str(default_root))))).resolve()
        ttl = int(os.getenv("CACHE_TTL_SECONDS", "86400"))
        default_extensions = Path(__file__).resolve().parents[2] / "extensions"
        extension_root = Path(os.path.expandvars(os.path.expanduser(os.getenv("EXTENSIONS_ROOT", str(default_extensions))))).resolve()
        registry = os.getenv("EXTENSIONS_REGISTRY_PATH")
        registry_path = Path(os.path.expandvars(os.path.expanduser(registry))).resolve() if registry else None
        return cls(project_root, origins, ttl, extension_root, registry_path)
