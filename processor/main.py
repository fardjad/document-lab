try:
    from .infrastructure.file_store.filesystem_project_source import FilesystemProjectSource
    from .application.project_access.usecases.project_queries import ProjectQueries
    from .config.settings import Settings
    from .infrastructure.http_api import create_app
except ImportError:
    from infrastructure.file_store.filesystem_project_source import FilesystemProjectSource
    from application.project_access.usecases.project_queries import ProjectQueries
    from config.settings import Settings
    from infrastructure.http_api import create_app


settings = Settings.from_environment()
app = create_app(ProjectQueries(FilesystemProjectSource(settings.project_root)), settings.cors_origins)
