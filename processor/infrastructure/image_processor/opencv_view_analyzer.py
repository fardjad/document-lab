import cv2
import numpy as np

try:
    from application.view.ports.document_analyzers import DocumentStraightener, DocumentTrimmer
    from application.view.ports.document_analysis_result import AutoProcessingResult
    from model.operation import Operation
except ImportError:
    from ...application.view.ports.document_analyzers import DocumentStraightener, DocumentTrimmer
    from ...application.view.ports.document_analysis_result import AutoProcessingResult
    from ...model.operation import Operation


class OpenCVDocumentAnalyzer(DocumentStraightener, DocumentTrimmer):
    """Draft-only automatic suggestions; confirmation through region update is the only persistence path."""

    def __init__(self) -> None:
        pass

    def detect_skew(self, rendered: bytes) -> AutoProcessingResult:
        return self._straighten(self._decode(rendered))

    def detect_trim(self, rendered: bytes) -> AutoProcessingResult:
        return self._trim(self._decode(rendered))

    def _decode(self, rendered: bytes) -> np.ndarray:
        pixels = cv2.imdecode(np.frombuffer(rendered, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if pixels is None:
            raise ValueError("Unable to decode source image")
        if pixels.size == 0:
            raise ValueError("Region output is empty")
        return pixels

    def _straighten(self, image: np.ndarray) -> AutoProcessingResult:
        mask = self._foreground_mask(image)
        components, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        if components <= 1:
            return AutoProcessingResult(None, None, "No reliable document edges found")
        label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        points = cv2.findNonZero(np.where(labels == label, 255, 0).astype(np.uint8))
        if points is None or len(points) < 20:
            return AutoProcessingResult(None, None, "No reliable document edges found")
        _, (width, height), angle = cv2.minAreaRect(points)
        if width < 2 or height < 2:
            return AutoProcessingResult(None, None, "No reliable document edges found")
        correction = -angle if width >= height else 90 - angle
        while correction > 45:
            correction -= 90
        while correction < -45:
            correction += 90
        if abs(correction) > 15 or abs(correction) < 0.05:
            return AutoProcessingResult(None, None, "Detected skew is outside conservative correction range")
        return AutoProcessingResult(round(correction, 1), min(1.0, max(0.0, 1.0 - abs(correction) / 15)), "Detected document edge skew")

    def _trim(self, image: np.ndarray) -> AutoProcessingResult:
        mask = self._foreground_mask(image)
        if not np.any(mask):
            return AutoProcessingResult(None, None, "No reliable foreground found")
        components, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        if components <= 1:
            return AutoProcessingResult(None, None, "No reliable foreground found")
        label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        points = cv2.findNonZero(np.where(labels == label, 255, 0).astype(np.uint8))
        if points is None or stats[label, cv2.CC_STAT_AREA] < 20:
            return AutoProcessingResult(None, None, "No reliable foreground found")
        x, y, width, height = cv2.boundingRect(points)
        trim = Operation("trim", {"top": y, "right": image.shape[1] - (x + width), "bottom": image.shape[0] - (y + height), "left": x})
        if (y, image.shape[1] - (x + width), image.shape[0] - (y + height), x) == (0, 0, 0, 0):
            return AutoProcessingResult(None, None, "No external background to trim")
        return AutoProcessingResult(trim, 0.9, "Detected perimeter-connected background")

    def _foreground_mask(self, image: np.ndarray) -> np.ndarray:
        if image.ndim == 2:
            color = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.shape[2] == 4:
            color = image[:, :, :3]
        else:
            color = image
        valid = np.ones(image.shape[:2], dtype=bool) if image.ndim < 3 or image.shape[2] < 4 else image[:, :, 3] > 0
        valid_points = cv2.findNonZero(valid.astype(np.uint8))
        if valid_points is None:
            return np.zeros(image.shape[:2], dtype=np.uint8)
        x, y, width, height = cv2.boundingRect(valid_points)
        footprint = np.zeros_like(valid)
        footprint[y, x:x + width] = True
        footprint[y + height - 1, x:x + width] = True
        footprint[y:y + height, x] = True
        footprint[y:y + height, x + width - 1] = True
        border = color[footprint & valid].astype(np.float32)
        if len(border) == 0:
            return np.zeros(image.shape[:2], dtype=np.uint8)
        background = np.median(border, axis=0)
        difference = np.max(np.abs(color.astype(np.float32) - background), axis=2)
        foreground = ((difference > 12) & valid).astype(np.uint8) * 255
        return cv2.morphologyEx(foreground, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))