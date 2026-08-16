import json
from pathlib import Path
import tempfile
import unittest

import httpx

try:
    from config.extension_registry import ExtensionRegistryConfig
    from infrastructure.image_processor.http_extension import HttpExtensionDiscovery, _rendered_response
except ImportError:
    from ...config.extension_registry import ExtensionRegistryConfig
    from .http_extension import HttpExtensionDiscovery, _rendered_response


class HttpExtensionTests(unittest.TestCase):
    def test_registry_rejects_credentials_and_duplicate_allow_list_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "extensions.yaml"
            path.write_text("sources:\n  - discovery_url: http://user:pass@example.test/operations\n")
            with self.assertRaises(ValueError):
                ExtensionRegistryConfig.from_file(path)

    def test_registry_reads_and_validates_render_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "extensions.yaml"
            path.write_text("sources:\n  - discovery_url: http://example.test/operations\n    render_timeout_seconds: 120\n")
            self.assertEqual(120, ExtensionRegistryConfig.from_file(path).sources[0].render_timeout_seconds)
            path.write_text("sources:\n  - discovery_url: http://example.test/operations\n    render_timeout_seconds: 0\n")
            with self.assertRaisesRegex(ValueError, "render_timeout_seconds"):
                ExtensionRegistryConfig.from_file(path)
            path.write_text("sources:\n  - discovery_url: http://example.test/operations\n    allow_operations: [rotate, rotate]\n")
            with self.assertRaises(ValueError):
                ExtensionRegistryConfig.from_file(path)

    def test_discovery_rejects_traversal_and_redirects(self) -> None:
        transport = httpx.MockTransport(lambda request: httpx.Response(302, headers={"location": "http://other.test/operations"}))
        client = httpx.Client(transport=transport, follow_redirects=False)
        discovery = HttpExtensionDiscovery.__new__(HttpExtensionDiscovery)
        discovery.client = client
        with self.assertRaises(ValueError):
            discovery._url("http://example.test/operations/", "/operations/%2e%2e/secret")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "extensions.yaml"
            path.write_text("sources:\n  - discovery_url: http://example.test/operations\n")
            discovery.registry_path = path
            with self.assertRaises(ValueError):
                discovery.load()

    def test_discovery_rejects_non_json_catalog_and_duplicate_helpers(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/health":
                return httpx.Response(204)
            if request.url.path == "/operations":
                return httpx.Response(200, text="{}", headers={"content-type": "text/plain"})
            return httpx.Response(404)

        discovery = HttpExtensionDiscovery.__new__(HttpExtensionDiscovery)
        discovery.client = httpx.Client(transport=httpx.MockTransport(handler))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "extensions.yaml"
            path.write_text("sources:\n  - discovery_url: http://example.test/operations\n")
            discovery.registry_path = path
            with self.assertRaisesRegex(ValueError, "application/json"):
                discovery.load()

    def test_render_response_requires_png_and_positive_dimensions(self) -> None:
        response = httpx.Response(200, content=b"png", headers={"content-type": "image/jpeg", "x-image-width": "2", "x-image-height": "3"})
        with self.assertRaisesRegex(ValueError, "image/png"):
            _rendered_response(response)
        response = httpx.Response(200, content=b"png", headers={"content-type": "image/png", "x-image-width": "0", "x-image-height": "3"})
        with self.assertRaises(ValueError):
            _rendered_response(response)


if __name__ == "__main__":
    unittest.main()
