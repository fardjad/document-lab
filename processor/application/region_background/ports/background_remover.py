from typing import Protocol

try:
    from model.project import BackgroundRemoval
except ImportError:
    from ....model.project import BackgroundRemoval


class BackgroundRemover(Protocol):
    def remove(self, image: bytes, settings: BackgroundRemoval) -> bytes: ...
