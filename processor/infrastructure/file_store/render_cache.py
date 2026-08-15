from pathlib import Path
import os
import struct
import tempfile
import time

try:
    from application.view.ports.rendered_region import RenderedRegion
    from model.project import ProjectId
except ImportError:
    from ...application.view.ports.rendered_region import RenderedRegion
    from ...model.project import ProjectId


class FileRenderCache:
    def __init__(self, project_root: str | Path, ttl_seconds: int) -> None:
        self._root = Path(project_root).resolve()
        self._ttl_seconds = ttl_seconds

    def _path(self, project_id: ProjectId, view_id: int, cache_key: str) -> Path:
        return self._root / project_id.value / "cache" / f"{view_id}-{cache_key}.png"

    def get(self, project_id: ProjectId, view_id: int, cache_key: str) -> RenderedRegion | None:
        path = self._path(project_id, view_id, cache_key)
        try:
            if time.time() - path.stat().st_mtime > self._ttl_seconds:
                path.unlink(missing_ok=True)
                return None
            data = path.read_bytes()
            if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
                return None
            width, height = struct.unpack(">II", data[16:24])
            return RenderedRegion(data, width, height)
        except (FileNotFoundError, ValueError, struct.error):
            return None

    def put(self, project_id: ProjectId, view_id: int, cache_key: str, rendered: RenderedRegion) -> None:
        directory = self._root / project_id.value / "cache"
        directory.mkdir(parents=True, exist_ok=True)
        target = self._path(project_id, view_id, cache_key)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=directory)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(rendered.image)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    def cleanup(self, project_id: ProjectId) -> None:
        directory = self._root / project_id.value / "cache"
        if not directory.is_dir():
            return
        for path in directory.glob("*.png"):
            try:
                if time.time() - path.stat().st_mtime > self._ttl_seconds:
                    path.unlink()
            except FileNotFoundError:
                pass

    def cleanup_view(self, project_id: ProjectId, view_id: int, valid_keys: set[str]) -> None:
        directory = self._root / project_id.value / "cache"
        if not directory.is_dir():
            return
        prefix = f"{view_id}-"
        for path in directory.glob(f"{view_id}-*.png"):
            if not path.name.startswith(prefix):
                continue
            cache_key = path.name[len(prefix) : -len(".png")]
            if cache_key not in valid_keys:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
