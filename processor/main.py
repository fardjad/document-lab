try:
    from .application.auto_processing.usecases.auto_straighten_view import AutoStraightenView
    from .application.auto_processing.usecases.auto_trim_view import AutoTrimView
    from .application.project.usecases.create_project import CreateProject
    from .application.project.usecases.delete_project import DeleteProject
    from .application.project.usecases.import_project import ImportProject
    from .application.project.usecases.list_projects import ListProjects
    from .application.project.usecases.read_project_image import ReadProjectImage
    from .application.project.usecases.read_project_image_size import ReadProjectImageSize
    from .application.project.usecases.update_project import UpdateProject
    from .application.view.usecases.create_view import CreateView
    from .application.view.usecases.delete_view import DeleteView
    from .application.view.usecases.list_views import ListViews
    from .application.view.usecases.render_view import RenderView
    from .application.view.usecases.update_view import UpdateView
    from .config.settings import Settings
    from .infrastructure.file_store.filesystem_project_source import FilesystemProjectStore
    from .infrastructure.http_api import create_app
    from .infrastructure.image_processor.opencv_view_analyzer import OpenCVDocumentAnalyzer
    from .infrastructure.image_processor.operations.remove_background import RemoveBackgroundOperation
    from .infrastructure.image_processor.operations.rotate import RotateOperation
    from .infrastructure.image_processor.operations.straighten import StraightenOperation
    from .infrastructure.image_processor.operations.trim import TrimOperation
    from .infrastructure.image_processor.operation_registry import OperationRegistryImpl
    from .infrastructure.image_processor.operations.crop import CropOperation
    from .infrastructure.image_processor.rembg_background_remover import RembgBackgroundRemover
except ImportError:
    from application.auto_processing.usecases.auto_straighten_view import AutoStraightenView
    from application.auto_processing.usecases.auto_trim_view import AutoTrimView
    from application.project.usecases.create_project import CreateProject
    from application.project.usecases.delete_project import DeleteProject
    from application.project.usecases.import_project import ImportProject
    from application.project.usecases.list_projects import ListProjects
    from application.project.usecases.read_project_image import ReadProjectImage
    from application.project.usecases.read_project_image_size import ReadProjectImageSize
    from application.project.usecases.update_project import UpdateProject
    from application.view.usecases.create_view import CreateView
    from application.view.usecases.delete_view import DeleteView
    from application.view.usecases.list_views import ListViews
    from application.view.usecases.render_view import RenderView
    from application.view.usecases.update_view import UpdateView
    from config.settings import Settings
    from infrastructure.file_store.filesystem_project_source import FilesystemProjectStore
    from infrastructure.http_api import create_app
    from infrastructure.image_processor.opencv_view_analyzer import OpenCVDocumentAnalyzer
    from infrastructure.image_processor.operations.remove_background import RemoveBackgroundOperation
    from infrastructure.image_processor.operations.rotate import RotateOperation
    from infrastructure.image_processor.operations.straighten import StraightenOperation
    from infrastructure.image_processor.operations.trim import TrimOperation
    from infrastructure.image_processor.operation_registry import OperationRegistryImpl
    from infrastructure.image_processor.operations.crop import CropOperation
    from infrastructure.image_processor.rembg_background_remover import RembgBackgroundRemover


settings = Settings.from_environment()
store = FilesystemProjectStore(settings.project_root)
background_remover = RembgBackgroundRemover()
analyzer = OpenCVDocumentAnalyzer()
straighten = StraightenOperation(analyzer)
trim = TrimOperation(analyzer)
registry = OperationRegistryImpl([
    RotateOperation(),
    straighten,
    trim,
    CropOperation(),
    RemoveBackgroundOperation(background_remover),
])
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
    ImportProject(store, store),
    ListViews(store),
    CreateView(store),
    UpdateView(store, registry),
    DeleteView(store),
    RenderView(store, read_project_image, read_project_image_size, registry),
    AutoStraightenView(store, read_project_image, read_project_image_size, registry),
    AutoTrimView(store, read_project_image, read_project_image_size, registry),
)
