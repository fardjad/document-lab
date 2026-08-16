"""Runtime discovery of operation extensions kept outside the processor package."""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import shutil
import sys
from types import ModuleType
from typing import Any


@dataclass(frozen=True)
class ExtensionDependencies:
    """Capabilities that composition supplies to extension registration."""

    document_analyzer: Any
    background_remover: Any


class OperationExtensionLoader:
    """Discovers extension directories and obtains one operation from each."""

    _module_prefix = "document_cropper_extensions"

    def __init__(self, extension_root: Path, dependencies: ExtensionDependencies) -> None:
        self._extension_root = extension_root
        self._dependencies = dependencies
        self._loaded_modules: set[str] = set()

    def load(self) -> list:
        if not self._extension_root.exists():
            return []
        if not self._extension_root.is_dir():
            raise ValueError(f"Extension path is not a directory: {self._extension_root}")
        operations = []
        kinds: set[str] = set()
        for directory in sorted(self._extension_root.iterdir()):
            if not directory.is_dir() or directory.name.startswith("_"):
                continue
            init_file = directory / "__init__.py"
            if not init_file.is_file():
                continue
            operation = self._load_module(directory, init_file).register(self._dependencies)
            if operation.kind in kinds:
                raise ValueError(f"Duplicate operation kind: {operation.kind}")
            kinds.add(operation.kind)
            operations.append(operation)
        return operations

    def reload(self) -> list:
        for name in self._loaded_modules:
            sys.modules.pop(name, None)
        for cache in self._extension_root.glob("*/__pycache__"):
            shutil.rmtree(cache)
        self._loaded_modules.clear()
        return self.load()

    def _load_module(self, directory: Path, init_file: Path) -> ModuleType:
        module_name = f"{self._module_prefix}.{directory.name}"
        spec = importlib.util.spec_from_file_location(module_name, init_file, submodule_search_locations=[str(directory)])
        if spec is None or spec.loader is None:
            raise ValueError(f"Cannot load extension: {directory.name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(module_name, None)
            raise
        if not callable(getattr(module, "register", None)):
            raise ValueError(f"Extension {directory.name} must define register(dependencies)")
        self._loaded_modules.add(module_name)
        return module
