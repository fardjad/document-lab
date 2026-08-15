from dataclasses import dataclass

try:
    from application.view.ports.operation_registry import OperationRegistry
    from application.view.ports.rendered_region import RenderedRegion
    from application.view.ports.view_store import ProjectViewStore
    from application.view.usecases.project_lookup import project_id_or_not_found
    from model.view import ViewNotFound
except ImportError:
    from ...view.ports.operation_registry import OperationRegistry
    from ...view.ports.rendered_region import RenderedRegion
    from ...view.ports.view_store import ProjectViewStore
    from ...view.usecases.project_lookup import project_id_or_not_found
    from ....model.view import ViewNotFound


@dataclass(frozen=True)
class InvokeHelper:
    """Render a view up to an operation and invoke one of its helpers."""

    views: ProjectViewStore
    image_reader: object
    image_sizes: object
    registry: OperationRegistry

    def invoke(
        self,
        raw_project_id: str,
        view_id: int,
        operation_index: int,
        helper_name: str,
        invocation_options: dict,
    ) -> dict:
        project_id = project_id_or_not_found(raw_project_id)
        selected = self.views.read_project_views(project_id).find_view(view_id)
        if selected is None:
            raise ViewNotFound("View not found")
        operations = selected.pipeline.operations
        if not isinstance(operation_index, int) or isinstance(operation_index, bool):
            raise ValueError("Invalid operation index")
        if operation_index < 0 or operation_index > len(operations):
            raise ValueError("Operation index out of range")
        target_operation = operations[operation_index] if operation_index < len(operations) else None
        if target_operation is not None and not target_operation.enabled:
            raise ValueError("Cannot invoke helper for disabled operation")

        image = self.image_reader.read(raw_project_id)
        width, height = self.image_sizes.read(raw_project_id)
        rendered = RenderedRegion(image.data, width, height)
        for operation in operations[:operation_index]:
            if not operation.enabled:
                continue
            rendered = self.registry.get(operation.kind).render(rendered, operation.options)

        if target_operation is not None:
            registered = self.registry.get(target_operation.kind)
        else:
            registered = next(
                (
                    self.registry.get(kind)
                    for kind in self.registry.kinds()
                    if any(helper.name == helper_name for helper in self.registry.get(kind).helpers)
                ),
                None,
            )
            if registered is None:
                raise ValueError(f"Unknown helper: {helper_name}")
        try:
            helper = next(helper for helper in registered.helpers if helper.name == helper_name)
        except StopIteration as error:
            raise ValueError(f"Unknown helper: {helper_name}") from error
        validated_options = helper.invocation_spec.validate_options(invocation_options)
        return helper.invoke(rendered, validated_options, target_operation.options if target_operation is not None else {})
