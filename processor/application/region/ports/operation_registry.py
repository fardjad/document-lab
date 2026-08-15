from typing import Protocol

try:
    from model.rendered_region import RenderedRegion
except ImportError:
    from ....model.rendered_region import RenderedRegion


class OperationExecutor(Protocol):
    """Outbound contract for a self-contained pipeline operation plugin.

    Each executor owns its option schema validation and its render logic,
    including dimension computation. ``validate`` checks the option schema
    without an image; ``render`` produces the next ``RenderedRegion``.
    """

    kind: str

    def validate(self, options: dict) -> dict: ...

    def render(self, region: RenderedRegion, options: dict) -> RenderedRegion: ...


class OperationRegistry(Protocol):
    """Outbound contract for resolving operation executors by kind."""

    def get(self, kind: str) -> OperationExecutor: ...

    def kinds(self) -> tuple[str, ...]: ...