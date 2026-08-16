from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import urlparse

import yaml


@dataclass(frozen=True)
class ExtensionSource:
    discovery_url: str
    allow_operations: tuple[str, ...] = ()
    headers: dict[str, str] | None = None
    render_timeout_seconds: float = 300


class ExtensionRegistryConfig:
    def __init__(self, sources: tuple[ExtensionSource, ...]) -> None:
        self.sources = sources

    @classmethod
    def from_file(cls, path: Path) -> "ExtensionRegistryConfig":
        try:
            document = yaml.safe_load(path.read_text())
        except (OSError, yaml.YAMLError) as error:
            raise ValueError(f"Cannot read extension registry: {error}") from error
        if not isinstance(document, dict) or not isinstance(document.get("sources"), list):
            raise ValueError("Extension registry must contain a sources list")
        sources = []
        for item in document["sources"]:
            if not isinstance(item, dict) or not isinstance(item.get("discovery_url"), str):
                raise ValueError("Each extension source requires discovery_url")
            url = item["discovery_url"]
            parsed = urlparse(url)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(f"Invalid discovery URL: {url}")
            allowed = item.get("allow_operations", [])
            headers = item.get("headers", {})
            timeout = item.get("render_timeout_seconds", 300)
            if not isinstance(allowed, list) or any(not isinstance(value, str) or not value for value in allowed) or len(set(allowed)) != len(allowed):
                raise ValueError("allow_operations must be a list of names")
            if not isinstance(headers, dict) or any(not isinstance(k, str) or not k or not isinstance(v, str) for k, v in headers.items()):
                raise ValueError("headers must be a string-to-string mapping")
            if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
                raise ValueError("render_timeout_seconds must be a positive number")
            sources.append(ExtensionSource(url, tuple(allowed), dict(headers), float(timeout)))
        return cls(tuple(sources))

    @classmethod
    def from_environment(cls) -> "ExtensionRegistryConfig":
        configured = os.getenv("EXTENSIONS_REGISTRY_PATH")
        if not configured:
            raise ValueError("EXTENSIONS_REGISTRY_PATH is required")
        return cls.from_file(Path(os.path.expandvars(os.path.expanduser(configured))).resolve())
