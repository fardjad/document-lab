try:
    from .application.auto_processing.usecases.auto_straighten_region import AutoStraightenRegion
    from .application.auto_processing.usecases.auto_trim_region import AutoTrimRegion
    from .application.project.usecases.create_project import CreateProject
    from .application.project.usecases.delete_project import DeleteProject
    from .application.project.usecases.import_project import ImportProject
    from .application.project.usecases.list_projects import ListProjects
    from .application.project.usecases.read_project_image import ReadProjectImage
    from .application.project.usecases.read_project_image_size import ReadProjectImageSize
    from .application.project.usecases.update_project import UpdateProject
    from .application.region.usecases.create_region import CreateRegion
    from .application.region.usecases.delete_region import DeleteRegion
    from .application.region.usecases.list_regions import ListRegions
    from .application.region.usecases.render_region import RenderRegion
    from .application.region.usecases.update_region import UpdateRegion
    from .config.settings import Settings
    from .infrastructure.file_store.filesystem_project_source import FilesystemProjectStore
    from .infrastructure.http_api import create_app
    from .infrastructure.image_processor.opencv_region_analyzer import OpenCVDocumentAnalyzer
    from .infrastructure.image_processor.operations.remove_background import RemoveBackgroundExecutor
    from .infrastructure.image_processor.operations.rotate import RotateExecutor
    from .infrastructure.image_processor.operations.straighten import StraightenExecutor
    from .infrastructure.image_processor.operations.trim import TrimExecutor
    from .infrastructure.image_processor.operation_registry import OperationRegistryImpl
    from .infrastructure.image_processor.pillow_region_cropper import PillowRegionCropper
    from .infrastructure.image_processor.rembg_background_remover import RembgBackgroundRemover
except ImportError:
    from application.auto_processing.usecases.auto_straighten_region import AutoStraightenRegion
    from application.auto_processing.usecases.auto_trim_region import AutoTrimRegion
    from application.project.usecases.create_project import CreateProject
    from application.project.usecases.delete_project import DeleteProject
    from application.project.usecases.import_project import ImportProject
    from application.project.usecases.list_projects import ListProjects
    from application.project.usecases.read_project_image import ReadProjectImage
    from application.project.usecases.read_project_image_size import ReadProjectImageSize
    from application.project.usecases.update_project import UpdateProject
    from application.region.usecases.create_region import CreateRegion
    from application.region.usecases.delete_region import DeleteRegion
    from application.region.usecases.list_regions import ListRegions
    from application.region.usecases.render_region import RenderRegion
    from application.region.usecases.update_region import UpdateRegion
    from config.settings import Settings
    from infrastructure.file_store.filesystem_project_source import FilesystemProjectStore
    from infrastructure.http_api import create_app
    from infrastructure.image_processor.opencv_region_analyzer import OpenCVDocumentAnalyzer
    from infrastructure.image_processor.operations.remove_background import RemoveBackgroundExecutor
    from infrastructure.image_processor.operations.rotate import RotateExecutor
    from infrastructure.image_processor.operations.straighten import StraightenExecutor
    from infrastructure.image_processor.operations.trim import TrimExecutor
    from infrastructure.image_processor.operation_registry import OperationRegistryImpl
    from infrastructure.image_processor.pillow_region_cropper import PillowRegionCropper
    from infrastructure.image_processor.rembg_background_remover import RembgBackgroundRemover


settings = Settings.from_environment()
store = FilesystemProjectStore(settings.project_root)
background_remover = RembgBackgroundRemover()
registry = OperationRegistryImpl([
    RotateExecutor(),
    StraightenExecutor(),
    TrimExecutor(),
    RemoveBackgroundExecutor(background_remover),
])
cropper = PillowRegionCropper()
analyzer = OpenCVDocumentAnalyzer()
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
    ListRegions(store),
    CreateRegion(store, read_project_image_size),
    UpdateRegion(store, read_project_image_size, registry),
    DeleteRegion(store),
    RenderRegion(store, read_project_image, cropper, registry),
    AutoStraightenRegion(store, read_project_image, cropper, registry, analyzer),
    AutoTrimRegion(store, read_project_image, cropper, registry, analyzer),
)