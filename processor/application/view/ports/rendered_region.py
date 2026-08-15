from dataclasses import dataclass


@dataclass(frozen=True)
class RenderedRegion:
    """Intermediate render state: image bytes plus current pixel dimensions.

    Carries both the rendered image bytes and the pixel size so each executor
    can compute new dimensions as part of rendering without a separate geometry
    pass.
    """

    image: bytes
    width: int
    height: int

    def __post_init__(self) -> None:
        if not isinstance(self.image, bytes):
            raise ValueError("Invalid rendered region image")
        if isinstance(self.width, bool) or not isinstance(self.width, int) or self.width <= 0:
            raise ValueError("Invalid rendered region width")
        if isinstance(self.height, bool) or not isinstance(self.height, int) or self.height <= 0:
            raise ValueError("Invalid rendered region height")