try:
    from application.view.ports.operation_registry import OperationSpecRegistry
    from application.view.ports.view_store import ProjectViewStore
    from application.view.usecases.project_lookup import project_id_or_not_found
    from application.view.usecases.view_lock import view_write_lock
    from model.pipeline import Pipeline
    from model.view import View, ViewNotFound
except ImportError:
    from ..ports.operation_registry import OperationSpecRegistry
    from ..ports.view_store import ProjectViewStore
    from .project_lookup import project_id_or_not_found
    from .view_lock import view_write_lock
    from ....model.pipeline import Pipeline
    from ....model.view import View, ViewNotFound


class UpdateView:
    """Replace a view's name and pipeline.

    Saving or updating a view persists the pipeline: a full pipeline is part
    of the update payload, so rotate, straighten, trim, and background removal
    are saved together.  Each operation's option schema is validated via its
    executor before persisting.
    """

    def __init__(self, views: ProjectViewStore, registry: OperationSpecRegistry) -> None:
        self._views = views
        self._registry = registry

    def update(self, raw_project_id: str, view_id: int, name: str, pipeline: Pipeline) -> View:
        project_id = project_id_or_not_found(raw_project_id)
        with view_write_lock():
            current = self._views.read_project_views(project_id)
            for op in pipeline.operations:
                self._registry.spec_for(op.kind).validate_options(op.options)
            updated_view = View(view_id, name, pipeline)
            if current.find(view_id) is None:
                raise ViewNotFound("View not found")
            self._views.write_project_views(project_id, current.replace(updated_view))
            return updated_view
