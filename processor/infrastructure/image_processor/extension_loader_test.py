from pathlib import Path
import tempfile
import unittest

from infrastructure.image_processor.extension_loader import ExtensionDependencies, OperationExtensionLoader


class OperationExtensionLoaderTests(unittest.TestCase):
    def test_loads_extension_and_reload_executes_updated_registration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugin = root / "test_operation"
            plugin.mkdir()
            source = plugin / "__init__.py"
            source.write_text(
                "class Operation:\n"
                "    kind = 'one'\n"
                "    spec = None\n"
                "    helpers = ()\n"
                "def register(dependencies):\n"
                "    return Operation()\n"
            )
            loader = OperationExtensionLoader(root, ExtensionDependencies(None, None))

            self.assertEqual(["one"], [operation.kind for operation in loader.load()])

            source.write_text(
                "class Operation:\n"
                "    kind = 'two'\n"
                "    spec = None\n"
                "    helpers = ()\n"
                "def register(dependencies):\n"
                "    return Operation()\n"
            )
            self.assertEqual(["two"], [operation.kind for operation in loader.reload()])

    def test_rejects_extension_without_registration_function(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "invalid"
            plugin.mkdir()
            (plugin / "__init__.py").write_text("value = 1\n")

            with self.assertRaisesRegex(ValueError, "must define register"):
                OperationExtensionLoader(Path(directory), ExtensionDependencies(None, None)).load()
