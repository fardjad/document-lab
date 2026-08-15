try:
    from application.auto_processing.usecases.invoke_helper import InvokeHelper
except ImportError:
    from .invoke_helper import InvokeHelper


class AutoStraightenView(InvokeHelper):
    """Compatibility name for the generic helper invocation use case."""
