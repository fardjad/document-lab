from pathlib import Path
import os
import struct
import tempfile

import yaml

try:
    from application.project_access.ports.project_source import ProjectSource
    from model.project import CropRectangle, CropRegion, ProjectId, ProjectImage, ProjectNotFound, ProjectRegions, RegionTrim
    from application.region_management.ports.project_region_store import ProjectRegionStore
except ImportError:
    from ...application.project_access.ports.project_source import ProjectSource
    from ...model.project import CropRectangle, CropRegion, ProjectId, ProjectImage, ProjectNotFound, ProjectRegions, RegionTrim
    from ...application.region_management.ports.project_region_store import ProjectRegionStore


class FilesystemProjectStore(ProjectSource, ProjectRegionStore):
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

    def _metadata(self, project_id: ProjectId) -> Path:
        project = self._project(project_id)
        metadata = (project / "project.yaml").resolve()
        if metadata.parent != project or (project / "project.yaml").is_symlink():
            raise ValueError("Invalid project metadata path")
        return metadata

    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions:
        metadata = self._metadata(project_id)
        if not metadata.exists():
            return ProjectRegions(1)
        if not metadata.is_file():
            raise ValueError("Invalid project metadata")
        try:
            document = yaml.safe_load(metadata.read_text())
            if not isinstance(document, dict) or document.get("version") != 1:
                raise ValueError
            if set(document) != {"version", "next_region_id", "regions"}:
                raise ValueError
            next_id = document["next_region_id"]
            raw_regions = document["regions"]
            if not isinstance(raw_regions, list):
                raise ValueError
            regions = []
            for raw in raw_regions:
                if not isinstance(raw, dict) or not set(raw).issubset({"id", "name", "rectangle", "rotation", "straighten", "trim"}) or set(raw) < {"id", "name", "rectangle"}:
                    raise ValueError
                rectangle = raw["rectangle"]
                if not isinstance(rectangle, dict) or set(rectangle) != {"x", "y", "width", "height"}:
                    raise ValueError
                trim = raw.get("trim", {"top": 0, "right": 0, "bottom": 0, "left": 0})
                if not isinstance(trim, dict) or set(trim) != {"top", "right", "bottom", "left"}:
                    raise ValueError
                regions.append(CropRegion(raw["id"], raw["name"], CropRectangle(rectangle["x"], rectangle["y"], rectangle["width"], rectangle["height"]), raw.get("rotation", 0), raw.get("straighten", 0.0), RegionTrim(trim["top"], trim["right"], trim["bottom"], trim["left"])))
            return ProjectRegions(next_id, tuple(regions))
        except (KeyError, TypeError, ValueError, yaml.YAMLError) as error:
            raise ValueError("Invalid project metadata") from error

    def write_project_regions(self, project_id: ProjectId, regions: ProjectRegions) -> None:
        metadata = self._metadata(project_id)
        document = {
            "version": 1,
            "next_region_id": regions.next_region_id,
            "regions": [
                {"id": item.id, "name": item.name, "rotation": item.rotation, "straighten": item.straighten, "trim": {"top": item.trim.top, "right": item.trim.right, "bottom": item.trim.bottom, "left": item.trim.left}, "rectangle": {"x": item.rectangle.x, "y": item.rectangle.y, "width": item.rectangle.width, "height": item.rectangle.height}}
                for item in regions.regions
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
