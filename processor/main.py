try:
    from .infrastructure.file_store.filesystem_project_source import FilesystemProjectStore
    from .application.project_access.usecases.project_queries import ProjectQueries
    from .application.slice_management.usecases.slice_commands import SliceCommands
    from .config.settings import Settings
    from .infrastructure.http_api import create_app
except ImportError:
    from infrastructure.file_store.filesystem_project_source import FilesystemProjectStore
    from application.project_access.usecases.project_queries import ProjectQueries
    from application.slice_management.usecases.slice_commands import SliceCommands
    from config.settings import Settings
    from infrastructure.http_api import create_app


settings = Settings.from_environment()
store = FilesystemProjectStore(settings.project_root)
app = create_app(ProjectQueries(store), settings.cors_origins, SliceCommands(store))
