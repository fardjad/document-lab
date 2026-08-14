from pathlib import Path

try:
    from application.project_access.ports.project_source import ProjectSource
    from model.project import ProjectId, ProjectImage, ProjectNotFound
except ImportError:
    from ...application.project_access.ports.project_source import ProjectSource
    from ...model.project import ProjectId, ProjectImage, ProjectNotFound


class FilesystemProjectSource(ProjectSource):
    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()

    def _project(self, project_id: ProjectId) -> Path:
        project = (self._root / project_id.value).resolve()
        if project.parent != self._root or not project.is_dir():
            raise ProjectNotFound("Project not found")
        return project

    def _image(self, project_id: ProjectId) -> Path:
        project = self._project(project_id)
        image = (project / "image.png").resolve()
        if image.parent != project or not image.is_file():
            raise ProjectNotFound("Project image not found")
        return image

    def list_project_ids(self) -> list[ProjectId]:
        if not self._root.is_dir():
            return []
        projects = []
        for entry in self._root.iterdir():
            try:
                project_id = ProjectId(entry.name)
                self._image(project_id)
            except (ValueError, ProjectNotFound):
                continue
            projects.append(project_id)
        return projects

    def read_project_image(self, project_id: ProjectId) -> ProjectImage:
        return ProjectImage(self._image(project_id).read_bytes())
