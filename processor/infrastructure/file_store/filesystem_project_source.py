from pathlib import Path
import os
import tempfile

import yaml

try:
    from application.project_access.ports.project_source import ProjectSource
    from model.project import CropRectangle, CropSlice, ProjectId, ProjectImage, ProjectNotFound, ProjectSlices
    from application.slice_management.ports.project_slice_store import ProjectSliceStore
except ImportError:
    from ...application.project_access.ports.project_source import ProjectSource
    from ...model.project import CropRectangle, CropSlice, ProjectId, ProjectImage, ProjectNotFound, ProjectSlices
    from ...application.slice_management.ports.project_slice_store import ProjectSliceStore


class FilesystemProjectStore(ProjectSource, ProjectSliceStore):
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

    def _metadata(self, project_id: ProjectId) -> Path:
        project = self._project(project_id)
        metadata = (project / "project.yaml").resolve()
        if metadata.parent != project or (project / "project.yaml").is_symlink():
            raise ValueError("Invalid project metadata path")
        return metadata

    def read_project_slices(self, project_id: ProjectId) -> ProjectSlices:
        metadata = self._metadata(project_id)
        if not metadata.exists():
            return ProjectSlices(1)
        if not metadata.is_file():
            raise ValueError("Invalid project metadata")
        try:
            document = yaml.safe_load(metadata.read_text())
            if not isinstance(document, dict) or document.get("version") != 1:
                raise ValueError
            if set(document) != {"version", "next_slice_id", "slices"}:
                raise ValueError
            next_id = document["next_slice_id"]
            raw_slices = document["slices"]
            if not isinstance(raw_slices, list):
                raise ValueError
            slices = []
            for raw in raw_slices:
                if not isinstance(raw, dict) or not set(raw).issubset({"id", "name", "rectangle", "rotation", "straighten"}) or set(raw) < {"id", "name", "rectangle"}:
                    raise ValueError
                rectangle = raw["rectangle"]
                if not isinstance(rectangle, dict) or set(rectangle) != {"x", "y", "width", "height"}:
                    raise ValueError
                slices.append(CropSlice(raw["id"], raw["name"], CropRectangle(rectangle["x"], rectangle["y"], rectangle["width"], rectangle["height"]), raw.get("rotation", 0), raw.get("straighten", 0.0)))
            return ProjectSlices(next_id, tuple(slices))
        except (KeyError, TypeError, ValueError, yaml.YAMLError) as error:
            raise ValueError("Invalid project metadata") from error

    def write_project_slices(self, project_id: ProjectId, slices: ProjectSlices) -> None:
        metadata = self._metadata(project_id)
        document = {
            "version": 1,
            "next_slice_id": slices.next_slice_id,
            "slices": [
                {"id": item.id, "name": item.name, "rotation": item.rotation, "straighten": item.straighten, "rectangle": {"x": item.rectangle.x, "y": item.rectangle.y, "width": item.rectangle.width, "height": item.rectangle.height}}
                for item in slices.slices
            ],
        }
        payload = yaml.safe_dump(document, sort_keys=False)
        descriptor, temporary = tempfile.mkstemp(prefix=".project.yaml.", dir=metadata.parent)
        try:
            with os.fdopen(descriptor, "w") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, metadata)
            directory = os.open(metadata.parent, os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise
