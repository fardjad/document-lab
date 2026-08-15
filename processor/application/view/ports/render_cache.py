from typing import Protocol

try:
    from model.project import ProjectId
    from application.view.ports.rendered_region import RenderedRegion
except ImportError:
    from ....model.project import ProjectId
    from .rendered_region import RenderedRegion


class RenderCache(Protocol):
    def get(self, project_id: ProjectId, view_id: int, cache_key: str) -> RenderedRegion | None: ...

    def put(self, project_id: ProjectId, view_id: int, cache_key: str, rendered: RenderedRegion) -> None: ...

    def cleanup_view(self, project_id: ProjectId, view_id: int, valid_keys: set[str]) -> None: ...

    def cleanup(self, project_id: ProjectId) -> None: ...
