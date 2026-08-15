from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class OperationSpec:
    """Technology-neutral contract for an operation plugin's options."""

    kind: str
    schema: dict
    validate: Callable[[dict], dict]

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind:
            raise ValueError("Invalid operation spec kind")
        if not isinstance(self.schema, dict):
            raise ValueError("Invalid operation spec schema")
        if not callable(self.validate):
            raise ValueError("Invalid operation spec validator")
        object.__setattr__(self, "schema", dict(self.schema))

    def validate_options(self, options: dict) -> dict:
        if not isinstance(options, dict):
            raise ValueError("Invalid operation options")
        result = self.validate(options)
        if not isinstance(result, dict):
            raise ValueError("Operation validator must return a dict")
        return result
