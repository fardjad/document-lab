from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class OperationSpec:
    """Application/plugin contract for an operation's options."""

    kind: str
    schema: dict
    validate: Callable[[dict], dict]
    display_name: str | None = None
    description: str = ""
    icon: str | None = None
    default_options: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind:
            raise ValueError("Invalid operation spec kind")
        if not isinstance(self.schema, dict):
            raise ValueError("Invalid operation spec schema")
        display_name = self.kind.replace("_", " ").title() if self.display_name is None else self.display_name
        icon = self.kind if self.icon is None else self.icon
        if not isinstance(display_name, str) or not display_name:
            raise ValueError("Invalid operation spec display name")
        if not isinstance(self.description, str):
            raise ValueError("Invalid operation spec description")
        if not isinstance(icon, str) or not icon:
            raise ValueError("Invalid operation spec icon")
        if not isinstance(self.default_options, dict):
            raise ValueError("Invalid operation spec default options")
        if not callable(self.validate):
            raise ValueError("Invalid operation spec validator")
        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "icon", icon)
        object.__setattr__(self, "schema", dict(self.schema))
        object.__setattr__(self, "default_options", dict(self.default_options))

    def validate_options(self, options: dict) -> dict:
        if not isinstance(options, dict):
            raise ValueError("Invalid operation options")
        result = self.validate(options)
        if not isinstance(result, dict):
            raise ValueError("Operation validator must return a dict")
        return result
