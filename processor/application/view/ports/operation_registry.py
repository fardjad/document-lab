from typing import Protocol

try:
    from application.view.ports.rendered_region import RenderedRegion
    from application.view.ports.operation_spec import OperationSpec
except ImportError:
    from .rendered_region import RenderedRegion
    from .operation_spec import OperationSpec


class OperationExecutor(Protocol):
    """Outbound contract for a self-contained pipeline operation plugin.

    Each executor owns its option schema validation and its render logic,
    including dimension computation. ``validate`` checks the option schema
    without an image; ``render`` produces the next ``RenderedRegion``.
    """

    kind: str

    def validate(self, options: dict) -> dict: ...

    def render(self, view: RenderedRegion, options: dict) -> RenderedRegion: ...


class OperationRegistry(Protocol):
    """Outbound contract for resolving operation executors by kind."""

    def get(self, kind: str) -> OperationExecutor: ...

    def kinds(self) -> tuple[str, ...]: ...


class OperationSpecRegistry(Protocol):
    """Outbound contract for resolving pure operation option specifications."""

    def spec_for(self, kind: str) -> OperationSpec: ...

    def kinds(self) -> tuple[str, ...]: ...
