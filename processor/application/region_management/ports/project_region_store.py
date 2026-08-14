from typing import Protocol

try:
    from model.project import CropRegion, ProjectId, ProjectRegions
except ImportError:
    from ....model.project import CropRegion, ProjectId, ProjectRegions


class ProjectRegionStore(Protocol):
    def read_project_regions(self, project_id: ProjectId) -> ProjectRegions: ...

    def write_project_regions(self, project_id: ProjectId, regions: ProjectRegions) -> None: ...

    def read_project_image_size(self, project_id: ProjectId) -> tuple[int, int]: ...
