from typing import Protocol

try:
    from model.project import CropSlice, ProjectId, ProjectSlices
except ImportError:
    from ....model.project import CropSlice, ProjectId, ProjectSlices


class ProjectSliceStore(Protocol):
    def read_project_slices(self, project_id: ProjectId) -> ProjectSlices: ...

    def write_project_slices(self, project_id: ProjectId, slices: ProjectSlices) -> None: ...
