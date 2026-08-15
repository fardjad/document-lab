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
    display_name: str | None = None
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Invalid helper name")
        display_name = self.name.replace("_", " ").title() if self.display_name is None else self.display_name
        if not isinstance(display_name, str) or not display_name:
            raise ValueError("Invalid helper display name")
        if not isinstance(self.description, str):
            raise ValueError("Invalid helper description")
        if not isinstance(self.invocation_spec, OperationSpec):
            raise ValueError("Invalid helper invocation spec")
        if not callable(self.invoke):
            raise ValueError("Invalid helper invoker")
        object.__setattr__(self, "display_name", display_name)

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
