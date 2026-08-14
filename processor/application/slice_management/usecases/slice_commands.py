from threading import Lock

try:
    from model.project import CropRectangle, CropSlice, ProjectId, ProjectSlices, ProjectNotFound, SliceNotFound
    from application.slice_management.ports.project_slice_store import ProjectSliceStore
except ImportError:
    from ....model.project import CropRectangle, CropSlice, ProjectId, ProjectSlices, ProjectNotFound, SliceNotFound
    from ..ports.project_slice_store import ProjectSliceStore


_SLICE_LOCK = Lock()


class SliceCommands:
    def __init__(self, store: ProjectSliceStore) -> None:
        self._store = store

    def list_slices(self, raw_project_id: str) -> ProjectSlices:
        return self._store.read_project_slices(self._project_id(raw_project_id))

    def create_slice(self, raw_project_id: str, rectangle: CropRectangle) -> CropSlice:
        project_id = self._project_id(raw_project_id)
        with _SLICE_LOCK:
            current = self._store.read_project_slices(project_id)
            created = CropSlice(current.next_slice_id, f"Slice {current.next_slice_id}", rectangle)
            updated = ProjectSlices(created.id + 1, current.slices + (created,))
            self._store.write_project_slices(project_id, updated)
            return created

    def update_slice(self, raw_project_id: str, slice_id: int, name: str, rectangle: CropRectangle, rotation: int) -> CropSlice:
        project_id = self._project_id(raw_project_id)
        name = self._name(name)
        with _SLICE_LOCK:
            current = self._store.read_project_slices(project_id)
            updated_slice = CropSlice(slice_id, name, rectangle, rotation)
            if not any(item.id == slice_id for item in current.slices):
                raise SliceNotFound("Slice not found")
            updated = ProjectSlices(current.next_slice_id, tuple(updated_slice if item.id == slice_id else item for item in current.slices))
            self._store.write_project_slices(project_id, updated)
            return updated_slice

    def delete_slice(self, raw_project_id: str, slice_id: int) -> None:
        project_id = self._project_id(raw_project_id)
        with _SLICE_LOCK:
            current = self._store.read_project_slices(project_id)
            if not any(item.id == slice_id for item in current.slices):
                raise SliceNotFound("Slice not found")
            self._store.write_project_slices(project_id, ProjectSlices(current.next_slice_id, tuple(item for item in current.slices if item.id != slice_id)))

    def _project_id(self, raw_project_id: str) -> ProjectId:
        try:
            return ProjectId(raw_project_id)
        except ValueError as error:
            raise ProjectNotFound("Project not found") from error

    def _name(self, name: str) -> str:
        if not isinstance(name, str):
            raise ValueError("Invalid slice name")
        return name.strip()
