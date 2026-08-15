import os
import struct
import tempfile
import time
import unittest
import zlib
from pathlib import Path

from application.view.ports.rendered_region import RenderedRegion
from infrastructure.file_store.render_cache import FileRenderCache
from model.project import ProjectId


def png_bytes(width: int, height: int, pixel: bytes = b"\x00\x00\x00") -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + pixel for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class FileRenderCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.root))
        self.project_id = ProjectId("project")
        self.cache = FileRenderCache(self.root, ttl_seconds=60)

    def test_get_returns_none_when_cache_file_does_not_exist(self) -> None:
        self.assertIsNone(self.cache.get(self.project_id, "missing"))

    def test_put_writes_png_and_get_returns_region_with_header_dimensions(self) -> None:
        image = png_bytes(3, 2)
        rendered = RenderedRegion(image, 3, 2)

        self.cache.put(self.project_id, "step", rendered)

        path = self.root / "project" / "cache" / "step.png"
        self.assertTrue(path.is_file())
        self.assertEqual(rendered, self.cache.get(self.project_id, "step"))

    def test_get_deletes_and_returns_none_for_stale_file(self) -> None:
        path = self.root / "project" / "cache" / "step.png"
        self.cache.put(self.project_id, "step", RenderedRegion(png_bytes(1, 1), 1, 1))
        old = time.time() - 120
        os.utime(path, (old, old))

        self.assertIsNone(self.cache.get(self.project_id, "step"))
        self.assertFalse(path.exists())

    def test_cleanup_deletes_stale_files_and_keeps_fresh_files(self) -> None:
        self.cache.put(self.project_id, "stale", RenderedRegion(png_bytes(1, 1), 1, 1))
        self.cache.put(self.project_id, "fresh", RenderedRegion(png_bytes(1, 1), 1, 1))
        stale_path = self.root / "project" / "cache" / "stale.png"
        os.utime(stale_path, (time.time() - 120, time.time() - 120))

        self.cache.cleanup(self.project_id)

        self.assertFalse(stale_path.exists())
        self.assertTrue((self.root / "project" / "cache" / "fresh.png").exists())


if __name__ == "__main__":
    unittest.main()
