from threading import Lock
import math

try:
    from model.project import BackgroundRemoval, CropRectangle, CropRegion, ProjectId, ProjectRegions, ProjectNotFound, RegionNotFound, RegionTrim
    from application.region_management.ports.project_region_store import ProjectRegionStore
except ImportError:
    from ....model.project import BackgroundRemoval, CropRectangle, CropRegion, ProjectId, ProjectRegions, ProjectNotFound, RegionNotFound, RegionTrim
    from ..ports.project_region_store import ProjectRegionStore


_SLICE_LOCK = Lock()


class RegionCommands:
    def __init__(self, store: ProjectRegionStore) -> None:
        self._store = store

    def list_regions(self, raw_project_id: str) -> ProjectRegions:
        return self._store.read_project_regions(self._project_id(raw_project_id))

    def create_region(self, raw_project_id: str, rectangle: CropRectangle) -> CropRegion:
        project_id = self._project_id(raw_project_id)
        with _SLICE_LOCK:
            current = self._store.read_project_regions(project_id)
            self._validate_transform(project_id, rectangle, 0, 0.0, RegionTrim())
            created = CropRegion(current.next_region_id, f"Region {current.next_region_id}", rectangle)
            updated = ProjectRegions(created.id + 1, current.regions + (created,))
            self._store.write_project_regions(project_id, updated)
            return created

    def update_region(self, raw_project_id: str, region_id: int, name: str, rectangle: CropRectangle, rotation: int, straighten: float, trim: RegionTrim, background_removal: BackgroundRemoval | None = None) -> CropRegion:
        project_id = self._project_id(raw_project_id)
        name = self._name(name)
        with _SLICE_LOCK:
            current = self._store.read_project_regions(project_id)
            self._validate_transform(project_id, rectangle, rotation, straighten, trim)
            updated_region = CropRegion(region_id, name, rectangle, rotation, straighten, trim, background_removal)
            if not any(item.id == region_id for item in current.regions):
                raise RegionNotFound("Region not found")
            updated = ProjectRegions(current.next_region_id, tuple(updated_region if item.id == region_id else item for item in current.regions))
            self._store.write_project_regions(project_id, updated)
            return updated_region

    def delete_region(self, raw_project_id: str, region_id: int) -> None:
        project_id = self._project_id(raw_project_id)
        with _SLICE_LOCK:
            current = self._store.read_project_regions(project_id)
            if not any(item.id == region_id for item in current.regions):
                raise RegionNotFound("Region not found")
            self._store.write_project_regions(project_id, ProjectRegions(current.next_region_id, tuple(item for item in current.regions if item.id != region_id)))

    def _project_id(self, raw_project_id: str) -> ProjectId:
        try:
            return ProjectId(raw_project_id)
        except ValueError as error:
            raise ProjectNotFound("Project not found") from error

    def _name(self, name: str) -> str:
        if not isinstance(name, str):
            raise ValueError("Invalid region name")
        return name.strip()

    def _validate_transform(self, project_id: ProjectId, rectangle: CropRectangle, rotation: int, straighten: float, trim: RegionTrim) -> None:
        if not isinstance(trim, RegionTrim):
            raise ValueError("Invalid region trim")
        image_width, image_height = self._store.read_project_image_size(project_id)
        if rectangle.x < 0 or rectangle.y < 0 or rectangle.x + rectangle.width > 1 or rectangle.y + rectangle.height > 1:
            raise ValueError("Crop rectangle outside image")
        angle = math.radians(straighten)
        source_width = rectangle.width * image_width
        source_height = rectangle.height * image_height
        width = math.ceil(abs(source_width * math.cos(angle)) + abs(source_height * math.sin(angle)))
        height = math.ceil(abs(source_width * math.sin(angle)) + abs(source_height * math.cos(angle)))
        if rotation % 180:
            width, height = height, width
        if trim.left + trim.right >= width or trim.top + trim.bottom >= height:
            raise ValueError("Region trim removes entire output")
