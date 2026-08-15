from typing import Protocol

try:
    from application.view.ports.rendered_region import RenderedRegion
    from application.view.ports.operation_spec import OperationSpec
    from application.view.ports.helper import Helper
except ImportError:
    from .rendered_region import RenderedRegion
    from .operation_spec import OperationSpec
    from .helper import Helper


class Operation(Protocol):
    """Outbound contract for a self-contained pipeline operation plugin."""

    kind: str
    spec: OperationSpec
    helpers: tuple[Helper, ...]

    def render(self, rendered: RenderedRegion, options: dict) -> RenderedRegion: ...


class OperationRegistry(Protocol):
    """Outbound contract for resolving complete operations by kind."""

    def get(self, kind: str) -> Operation: ...

    def kinds(self) -> tuple[str, ...]: ...


class OperationSpecRegistry(OperationRegistry, Protocol):
    """Compatibility contract exposing specs through the operation registry."""

    def spec_for(self, kind: str) -> OperationSpec:
        return self.get(kind).spec


# Compatibility alias for callers migrating from the pre-helper terminology.
OperationExecutor = Operation
