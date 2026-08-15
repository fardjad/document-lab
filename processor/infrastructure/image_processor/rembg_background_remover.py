from threading import Lock

from rembg import new_session, remove

try:
    from model.project import BackgroundRemoval
except ImportError:
    from ...model.project import BackgroundRemoval


class RembgBackgroundRemover:
    def __init__(self) -> None:
        self._sessions = {}
        self._locks = {}
        self._state_lock = Lock()

    def _session(self, model: str):
        with self._state_lock:
            session = self._sessions.get(model)
            if session is not None:
                return session
            lock = self._locks.setdefault(model, Lock())
        with lock:
            with self._state_lock:
                session = self._sessions.get(model)
                if session is not None:
                    return session
                session = new_session(model)
                self._sessions[model] = session
                return session

    def remove(self, image: bytes, settings: BackgroundRemoval) -> bytes:
        if not isinstance(settings, BackgroundRemoval):
            raise ValueError("Invalid background removal settings")
        session = self._session(settings.model)
        result = remove(
            image,
            session=session,
            alpha_matting=settings.alpha_matting,
            alpha_matting_foreground_threshold=settings.alpha_matting_foreground_threshold,
            alpha_matting_background_threshold=settings.alpha_matting_background_threshold,
            alpha_matting_erode_size=settings.alpha_matting_erode_size,
            post_process_mask=settings.post_process_mask,
            force_return_bytes=True,
        )
        if not isinstance(result, bytes):
            raise ValueError("Background removal produced no image")
        return result
