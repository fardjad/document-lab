from pathlib import Path
import os
import shutil
import struct
import tempfile

import yaml

try:
    from application.project.ports.project_store import ProjectStore, ProjectWriter
    from application.view.ports.view_store import ProjectViewStore
    from model.operation import Operation
    from model.pipeline import Pipeline
    from model.project import Project, ProjectId, ProjectImage, ProjectNotFound
    from model.view import View
except ImportError:
    from ...application.project.ports.project_store import ProjectStore, ProjectWriter
    from ...application.view.ports.view_store import ProjectViewStore
    from ...model.operation import Operation
    from ...model.pipeline import Pipeline
    from ...model.project import Project, ProjectId, ProjectImage, ProjectNotFound
    from ...model.view import View


class FilesystemProjectStore(ProjectStore, ProjectViewStore, ProjectWriter):
    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()

    def _project(self, project_id: ProjectId) -> Path:
        project = (self._root / project_id.value).resolve()
        if project.parent != self._root or not project.is_dir():
            raise ProjectNotFound("Project not found")
        return project

    def _image(self, project_id: ProjectId) -> Path:
        project = self._project(project_id)
        image = (project / "image.png").resolve()
        if image.parent != project or not image.is_file():
            raise ProjectNotFound("Project image not found")
        return image

    def list_project_ids(self) -> list[ProjectId]:
        if not self._root.is_dir():
            return []
        projects = []
        for entry in self._root.iterdir():
            try:
                project_id = ProjectId(entry.name)
                self._image(project_id)
            except (ValueError, ProjectNotFound):
                continue
            projects.append(project_id)
        return projects

    def read_project_image(self, project_id: ProjectId) -> ProjectImage:
        return ProjectImage(self._image(project_id).read_bytes())

    def read_project_image_size(self, project_id: ProjectId) -> tuple[int, int]:
        data = self._image(project_id).read_bytes()
        if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
            raise ValueError("Invalid PNG image")
        width, height = struct.unpack(">II", data[16:24])
        if not width or not height:
            raise ValueError("Invalid PNG image")
        return width, height

    def read_project_name(self, project_id: ProjectId) -> str:
        metadata = self._metadata(project_id)
        if not metadata.exists():
            return project_id.value
        try:
            document = yaml.safe_load(metadata.read_text())
            name = document.get("name") if isinstance(document, dict) else None
            if name is None:
                return project_id.value
            if not isinstance(name, str) or not name.strip():
                raise ValueError
            return name
        except (TypeError, ValueError, yaml.YAMLError) as error:
            raise ValueError("Invalid project metadata") from error

    def create_project(self, project_id: ProjectId, image: ProjectImage) -> None:
        project = (self._root / project_id.value).resolve()
        if project.parent != self._root:
            raise ValueError("Invalid project path")
        if project.exists():
            raise FileExistsError("Project already exists")
        project.mkdir(parents=False, exist_ok=False)
        try:
            self._atomic_write(project / "image.png", image.data)
        except BaseException:
            shutil.rmtree(project, ignore_errors=True)
            raise

    def replace_project_image(self, project_id: ProjectId, image: ProjectImage) -> None:
        project = self._project(project_id)
        self._atomic_write(project / "image.png", image.data)
        shutil.rmtree(project / "cache", ignore_errors=True)
        self.write_project_views(project_id, Project(project_id, ProjectImage(b"")))

    def delete_project(self, project_id: ProjectId) -> None:
        project = self._project(project_id)
        shutil.rmtree(project)

    def _metadata(self, project_id: ProjectId) -> Path:
        project = self._project(project_id)
        metadata = (project / "project.yaml").resolve()
        if metadata.parent != project or (project / "project.yaml").is_symlink():
            raise ValueError("Invalid project metadata path")
        return metadata

    def read_project_views(self, project_id: ProjectId) -> Project:
        metadata = self._metadata(project_id)
        if not metadata.exists():
            return Project(project_id, ProjectImage(b""))
        if not metadata.is_file():
            raise ValueError("Invalid project metadata")
        try:
            document = yaml.safe_load(metadata.read_text())
            version = document.get("version") if isinstance(document, dict) else None
            if version in (4, 5):
                expected = {"version", "next_view_id", "views"} | ({"name"} if version == 5 else set())
                if set(document) != expected:
                    raise ValueError
                next_id = document["next_view_id"]
                raw_views = document["views"]
                if not isinstance(raw_views, list):
                    raise ValueError
                views = [self._view(raw) for raw in raw_views]
                return Project(project_id, ProjectImage(b""), next_id, tuple(views))
            if version != 3 or set(document) != {"version", "next_region_id", "regions"}:
                raise ValueError
            next_id = document["next_region_id"]
            raw_regions = document["regions"]
            if not isinstance(raw_regions, list):
                raise ValueError
            views = [self._v3_view(raw) for raw in raw_regions]
            return Project(project_id, ProjectImage(b""), next_id, tuple(views))
        except (KeyError, TypeError, ValueError, yaml.YAMLError) as error:
            raise ValueError("Invalid project metadata") from error

    def _view(self, raw) -> View:
        if not isinstance(raw, dict) or set(raw) != {"id", "name", "pipeline"}:
            raise ValueError
        return View(raw["id"], raw["name"], self._pipeline(raw["pipeline"]))

    def _v3_view(self, raw) -> View:
        if not isinstance(raw, dict) or not set(raw).issubset({"id", "name", "rectangle", "pipeline"}) or set(raw) < {"id", "name", "rectangle"}:
            raise ValueError
        rectangle = raw["rectangle"]
        if not isinstance(rectangle, dict) or set(rectangle) != {"x", "y", "width", "height"}:
            raise ValueError
        pipeline = self._pipeline(raw.get("pipeline"))
        crop = Operation("crop", rectangle)
        return View(raw["id"], raw["name"], Pipeline((crop,) + pipeline.operations))

    def _pipeline(self, raw) -> Pipeline:
        if raw is None:
            return Pipeline()
        if not isinstance(raw, list):
            raise ValueError
        operations = []
        for entry in raw:
            if not isinstance(entry, dict) or not set(entry).issubset({"kind", "options", "enabled"}) or set(entry) < {"kind", "options"}:
                raise ValueError
            kind = entry["kind"]
            options = entry["options"]
            if not isinstance(kind, str) or not kind or not isinstance(options, dict):
                raise ValueError
            enabled = entry.get("enabled", True)
            operations.append(Operation(kind, options, enabled))
        return Pipeline(tuple(operations))

    def write_project_views(self, project_id: ProjectId, project: Project) -> None:
        metadata = self._metadata(project_id)
        named = metadata.exists() and "name" in (yaml.safe_load(metadata.read_text()) or {})
        document = {
            "version": 5 if named else 4,
            "next_view_id": project.next_view_id,
            "views": [
                {
                    "id": item.id,
                    "name": item.name,
                    "pipeline": [{"kind": op.kind, "options": dict(op.options), "enabled": op.enabled} for op in item.pipeline.operations],
                }
                for item in project.views
            ],
        }
        if named:
            document["name"] = self.read_project_name(project_id)
            document = {"version": document.pop("version"), "name": document.pop("name"), **document}
        self._atomic_write_yaml(metadata, document)

    def rename_project(self, project_id: ProjectId, name: str) -> None:
        metadata = self._metadata(project_id)
        if not metadata.exists():
            document = {"version": 5, "name": name, "next_view_id": 1, "views": []}
        else:
            try:
                document = yaml.safe_load(metadata.read_text())
            except yaml.YAMLError as error:
                raise ValueError("Invalid project metadata") from error
            if not isinstance(document, dict):
                raise ValueError("Invalid project metadata")
            document["name"] = name
            document["version"] = 5
        self._atomic_write_yaml(metadata, document)

    def _atomic_write(self, target: Path, data: bytes) -> None:
        descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            self._fsync_directory(target.parent)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    def _atomic_write_yaml(self, target: Path, document: dict) -> None:
        payload = yaml.safe_dump(document, sort_keys=False)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
        try:
            with os.fdopen(descriptor, "w") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            self._fsync_directory(target.parent)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    def _fsync_directory(self, directory: Path) -> None:
        descriptor = os.open(directory, os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
