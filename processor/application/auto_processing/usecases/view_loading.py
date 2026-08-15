try:
    from model.view import View, ViewNotFound
except ImportError:
    from ....model.view import View, ViewNotFound


def loaded_view(views, project_id, view_id: int) -> View:
    selected = views.read_project_views(project_id).find(view_id)
    if selected is None:
        raise ViewNotFound("View not found")
    return selected
