from dataclasses import dataclass, field


@dataclass(frozen=True)
class Operation:
    """A generic pipeline operation identified by kind with free-form options.

    Structural validation only: kind must be a non-empty string and options must
    be a dict. Domain validation (degrees % 90, angle bounds, etc.) lives in the
    executor plugins, not here.
    """

    kind: str
    options: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind:
            raise ValueError("Invalid operation kind")
        if not isinstance(self.options, dict):
            raise ValueError("Invalid operation options")
        object.__setattr__(self, "options", dict(self.options))