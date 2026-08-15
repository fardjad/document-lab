from threading import Lock

_REGION_WRITE_LOCK = Lock()


def region_write_lock() -> Lock:
    """Process-wide lock serializing read-modify-write cycles on region metadata."""

    return _REGION_WRITE_LOCK
