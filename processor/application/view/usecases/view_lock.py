from threading import Lock

_VIEW_WRITE_LOCK = Lock()


def view_write_lock() -> Lock:
    """Process-wide lock serializing read-modify-write cycles on view metadata."""

    return _VIEW_WRITE_LOCK
