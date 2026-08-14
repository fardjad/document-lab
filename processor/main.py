try:
    from .infrastructure.file_store.filesystem_project_source import FilesystemProjectStore
    from .application.project_access.usecases.project_queries import ProjectQueries
    from .application.region_management.usecases.region_commands import RegionCommands
    from .application.region_export.usecases.export_region import RegionExport
    from .infrastructure.image_processor.pillow_region_renderer import PillowRegionRenderer
    from .application.region_analysis.usecases.analyze_region import RegionAnalysis
    from .infrastructure.image_processor.opencv_region_analyzer import OpenCVRegionAnalyzer
    from .config.settings import Settings
    from .infrastructure.http_api import create_app
except ImportError:
    from infrastructure.file_store.filesystem_project_source import FilesystemProjectStore
    from application.project_access.usecases.project_queries import ProjectQueries
    from application.region_management.usecases.region_commands import RegionCommands
    from application.region_export.usecases.export_region import RegionExport
    from infrastructure.image_processor.pillow_region_renderer import PillowRegionRenderer
    from application.region_analysis.usecases.analyze_region import RegionAnalysis
    from infrastructure.image_processor.opencv_region_analyzer import OpenCVRegionAnalyzer
    from config.settings import Settings
    from infrastructure.http_api import create_app


settings = Settings.from_environment()
store = FilesystemProjectStore(settings.project_root)
renderer = PillowRegionRenderer()
app = create_app(ProjectQueries(store), settings.cors_origins, RegionCommands(store), RegionExport(store, store, renderer), RegionAnalysis(store, store, OpenCVRegionAnalyzer(renderer)))
