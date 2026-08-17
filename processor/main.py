try:
    from .application.view.usecases.invoke_helper import InvokeHelper
    from .application.project.usecases.create_project import CreateProject
    from .application.project.usecases.delete_project import DeleteProject
    from .application.project.usecases.list_projects import ListProjects
    from .application.project.usecases.read_project_image import ReadProjectImage
    from .application.project.usecases.read_project_image_size import ReadProjectImageSize
    from .application.project.usecases.update_project import UpdateProject
    from .application.project.usecases.rename_project import RenameProject
    from .application.view.usecases.create_view import CreateView
    from .application.view.usecases.delete_view import DeleteView
    from .application.view.usecases.list_views import ListViews
    from .application.view.usecases.render_view import RenderView
    from .application.view.usecases.update_view import UpdateView
    from .config.settings import Settings
    from .infrastructure.file_store.filesystem_project_source import FilesystemProjectStore
    from .infrastructure.file_store.render_cache import FileRenderCache
    from .infrastructure.http_api import create_app
    from .infrastructure.image_processor.opencv_view_analyzer import OpenCVDocumentAnalyzer
    from .infrastructure.image_processor.extension_loader import ExtensionDependencies, OperationExtensionLoader
    from .infrastructure.image_processor.operation_registry import OperationRegistryImpl
    from .infrastructure.image_processor.rembg_background_remover import RembgBackgroundRemover
    from .infrastructure.image_processor.http_extension import HttpExtensionDiscovery
except ImportError:
    from application.view.usecases.invoke_helper import InvokeHelper
    from application.project.usecases.create_project import CreateProject
    from application.project.usecases.delete_project import DeleteProject
    from application.project.usecases.list_projects import ListProjects
    from application.project.usecases.read_project_image import ReadProjectImage
    from application.project.usecases.read_project_image_size import ReadProjectImageSize
    from application.project.usecases.update_project import UpdateProject
    from application.project.usecases.rename_project import RenameProject
    from application.view.usecases.create_view import CreateView
    from application.view.usecases.delete_view import DeleteView
    from application.view.usecases.list_views import ListViews
    from application.view.usecases.render_view import RenderView
    from application.view.usecases.update_view import UpdateView
    from config.settings import Settings
    from infrastructure.file_store.filesystem_project_source import FilesystemProjectStore
    from infrastructure.file_store.render_cache import FileRenderCache
    from infrastructure.http_api import create_app
    from infrastructure.image_processor.opencv_view_analyzer import OpenCVDocumentAnalyzer
    from infrastructure.image_processor.extension_loader import ExtensionDependencies, OperationExtensionLoader
    from infrastructure.image_processor.operation_registry import OperationRegistryImpl
    from infrastructure.image_processor.rembg_background_remover import RembgBackgroundRemover
    from infrastructure.image_processor.http_extension import HttpExtensionDiscovery


settings = Settings.from_environment()
store = FilesystemProjectStore(settings.project_root)
cache = FileRenderCache(settings.project_root, settings.cache_ttl_seconds)
background_remover = RembgBackgroundRemover()
analyzer = OpenCVDocumentAnalyzer()
extension_loader = OperationExtensionLoader(settings.extension_root, ExtensionDependencies(document_analyzer=analyzer, background_remover=background_remover))
discovery = HttpExtensionDiscovery(settings.extensions_registry_path) if settings.extensions_registry_path else None
active_loader = discovery if discovery is not None else extension_loader
registry = OperationRegistryImpl(active_loader.load())
for project_id in store.list_project_ids():
    cache.cleanup(project_id)
list_projects = ListProjects(store)
read_project_image = ReadProjectImage(store)
read_project_image_size = ReadProjectImageSize(store)
app = create_app(
    list_projects,
    read_project_image,
    settings.cors_origins,
    CreateProject(store, store),
    UpdateProject(store, store),
    DeleteProject(store, store),
    ListViews(store),
    CreateView(store),
    UpdateView(store, registry, cache),
    DeleteView(store, cache),
    RenderView(store, read_project_image, read_project_image_size, registry, cache),
    InvokeHelper(store, read_project_image, read_project_image_size, registry, cache),
    registry,
    RenameProject(store, store),
    active_loader.load,
)

if discovery is not None:
    import signal
    signal.signal(signal.SIGHUP, lambda *_: registry.replace(discovery.load()))
