try:
    from model.project import ProjectId, ProjectNotFound
except ImportError:
    from ....model.project import ProjectId, ProjectNotFound


def project_id_or_not_found(raw_project_id: str) -> ProjectId:
    """Translate an untrusted raw identifier into a project ID.

    Callers pass arbitrary strings; an identifier that cannot name a project
    is reported as not found rather than as a format error.
    """

    try:
        return ProjectId(raw_project_id)
    except ValueError as error:
        raise ProjectNotFound("Project not found") from error
