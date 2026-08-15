from dataclasses import dataclass
from typing import Callable

try:
    from application.view.ports.rendered_region import RenderedRegion
    from application.view.ports.operation_spec import OperationSpec
except ImportError:
    from .rendered_region import RenderedRegion
    from .operation_spec import OperationSpec


@dataclass(frozen=True)
class Helper:
    """Application/plugin contract for an operation helper."""

    name: str
    invocation_spec: OperationSpec
    invoke: Callable[[RenderedRegion, dict, dict], dict]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Invalid helper name")
        if not isinstance(self.invocation_spec, OperationSpec):
            raise ValueError("Invalid helper invocation spec")
        if not callable(self.invoke):
            raise ValueError("Invalid helper invoker")

    def invoke_helper(
        self,
        rendered: RenderedRegion,
        invocation_options: dict,
        current_options: dict,
    ) -> dict:
        if not isinstance(rendered, RenderedRegion):
            raise ValueError("Invalid rendered region")
        if not isinstance(invocation_options, dict):
            raise ValueError("Invalid helper invocation options")
        if not isinstance(current_options, dict):
            raise ValueError("Invalid current operation options")
        result = self.invoke(rendered, invocation_options, current_options)
        if not isinstance(result, dict):
            raise ValueError("Helper invoker must return a dict")
        return result
