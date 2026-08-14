from pathlib import Path
import os
import struct
import tempfile
import unittest
from types import SimpleNamespace
from typing import Any, cast

from infrastructure.file_store.filesystem_project_source import FilesystemProjectStore
from model.project import ProjectId, ProjectNotFound


class FilesystemProjectStoreTests(unittest.TestCase):
    def test_missing_root_has_no_projects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = FilesystemProjectStore(Path(directory) / "missing")
            self.assertEqual([], source.list_project_ids())

    def test_missing_image_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "project").mkdir()
            with self.assertRaisesRegex(ProjectNotFound, "^Project image not found$"):
                FilesystemProjectStore(root).read_project_image(ProjectId("project"))

    def test_discovers_only_valid_projects_and_sorts_at_use_case_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("zebra", "Alpha", "no-image", "bad project"):
                (root / name).mkdir()
            (root / "zebra" / "image.png").write_bytes(b"z")
            (root / "Alpha" / "image.png").write_bytes(b"a")
            self.assertEqual({"Alpha", "zebra"}, {str(value) for value in FilesystemProjectStore(root).list_project_ids()})

    def test_reads_original_source_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            project.joinpath("image.png").write_bytes(b"original png bytes")
            self.assertEqual(b"original png bytes", FilesystemProjectStore(root).read_project_image(ProjectId("project")).data)

    def test_reads_png_ihdr_size(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            project.joinpath("image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + struct.pack(">II", 640, 480) + b"\x08\x06\x00\x00\x00")
            self.assertEqual((640, 480), FilesystemProjectStore(root).read_project_image_size(ProjectId("project")))

    def test_rejects_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ProjectNotFound, "^Project not found$"):
                FilesystemProjectStore(directory).read_project_image(cast(Any, SimpleNamespace(value="../outside")))

    def test_rejects_project_and_image_symlink_escapes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, outside = base / "projects", base / "outside"
            root.mkdir()
            outside.mkdir()
            (outside / "image.png").write_bytes(b"outside")
            try:
                os.symlink(outside, root / "linked", target_is_directory=True)
                project = root / "project"
                project.mkdir()
                os.symlink(outside / "image.png", project / "image.png")
            except OSError as error:
                self.skipTest(f"symlinks unavailable: {error}")
            source = FilesystemProjectStore(root)
            with self.assertRaisesRegex(ProjectNotFound, "^Project not found$"):
                source.read_project_image(ProjectId("linked"))
            with self.assertRaisesRegex(ProjectNotFound, "^Project image not found$"):
                source.read_project_image(ProjectId("project"))


if __name__ == "__main__":
    unittest.main()
