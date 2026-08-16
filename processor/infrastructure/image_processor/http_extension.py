from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote, urljoin, urlparse
import json

import httpx
from jsonschema import Draft202012Validator

try:
    from application.view.ports.helper import Helper
    from application.view.ports.operation_registry import Operation
    from application.view.ports.operation_spec import OperationSpec
    from application.view.ports.rendered_region import RenderedRegion
except ImportError:
    from ...application.view.ports.helper import Helper
    from ...application.view.ports.operation_registry import Operation
    from ...application.view.ports.operation_spec import OperationSpec
    from ...application.view.ports.rendered_region import RenderedRegion
try:
    from config.extension_registry import ExtensionRegistryConfig, ExtensionSource
except ImportError:
    from ...config.extension_registry import ExtensionRegistryConfig, ExtensionSource


def _validate_schema(schema: dict, value: dict) -> dict:
    if not isinstance(schema, dict) or schema.get("type") != "object" or not isinstance(value, dict):
        raise ValueError("Options must satisfy an object JSON Schema")
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda error: list(error.path))
    if errors:
        raise ValueError(errors[0].message)
    return dict(value)


def _schema_spec(kind: str, schema: dict, helper: bool = False) -> OperationSpec:
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ValueError("Schema must be an object schema without references")
    if any(key in schema for key in ("$ref", "$dynamicRef")) or _contains_reference(schema):
        raise ValueError("Schema references are not supported")
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as error:
        raise ValueError("Invalid JSON Schema") from error
    properties = schema.get("properties", {})
    if not isinstance(properties, dict) or any(not isinstance(key, str) or not isinstance(rule, dict) for key, rule in properties.items()):
        raise ValueError("Schema properties must be an object")
    if not isinstance(schema.get("required", []), list) or any(not isinstance(key, str) for key in schema.get("required", [])):
        raise ValueError("Schema required must be a list of names")
    if not isinstance(schema.get("x-hint-require-image", False), bool):
        raise ValueError("x-hint-require-image must be a boolean")
    for key, rule in properties.items():
        if "default" in rule and list(Draft202012Validator(rule).iter_errors(rule["default"])):
            raise ValueError(f"Invalid default for schema property: {key}")
    display = schema.get("x-hint-display-name", schema.get("title"))
    defaults = {key: value["default"] for key, value in schema.get("properties", {}).items() if isinstance(value, dict) and "default" in value}
    return OperationSpec(kind, schema, lambda options: _validate_schema(schema, options), display, schema.get("description", ""), schema.get("x-hint-icon"), defaults)


def _contains_reference(value: object) -> bool:
    if isinstance(value, dict):
        return any(key in {"$ref", "$dynamicRef"} or _contains_reference(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_reference(item) for item in value)
    return False


@dataclass
class HttpOperation:
    kind: str
    spec: OperationSpec
    render_url: str
    helpers: tuple[Helper, ...]
    client: httpx.Client
    headers: dict[str, str]
    requires_image: bool = False
    render_timeout_seconds: float = 300

    def render(self, rendered: RenderedRegion, options: dict) -> RenderedRegion:
        options = self.spec.validate_options(options)
        files = {"image": ("image.png", rendered.image, "image/png")} if self.requires_image else {}
        data = {"options": json.dumps(options)}
        if self.requires_image:
            data.update(width=str(rendered.width), height=str(rendered.height))
        try:
            response = self.client.post(
                self.render_url,
                headers=self.headers,
                data=data,
                files=files,
                timeout=self.render_timeout_seconds,
            )
        except httpx.TimeoutException as error:
            raise ValueError(
                f"Extension render timed out after {self.render_timeout_seconds:g} seconds"
            ) from error
        return _rendered_response(response)


def _rendered_response(response: httpx.Response) -> RenderedRegion:
    if response.status_code < 200 or response.status_code >= 300:
        raise ValueError(f"Extension request failed: {response.status_code}")
    if not response.headers.get("content-type", "").split(";", 1)[0].lower() == "image/png":
        raise ValueError("Extension response must be image/png")
    try:
        width, height = int(response.headers["x-image-width"]), int(response.headers["x-image-height"])
    except (KeyError, ValueError) as error:
        raise ValueError("Extension response must include image dimensions") from error
    if width <= 0 or height <= 0:
        raise ValueError("Extension response dimensions must be positive")
    return RenderedRegion(response.content, width, height)


class HttpExtensionDiscovery:
    def __init__(self, registry_path, client: httpx.Client | None = None) -> None:
        self.registry_path = registry_path
        self.client = client or httpx.Client()

    def load(self) -> list[HttpOperation]:
        config = ExtensionRegistryConfig.from_file(self.registry_path)
        operations = []
        seen = set()
        for source in config.sources:
            base = source.discovery_url.rsplit("/", 1)[0] + "/"
            health = self.client.get(urljoin(base, "health"), headers=source.headers)
            if not 200 <= health.status_code < 300:
                raise ValueError(f"Extension health check failed: {source.discovery_url}")
            catalog_response = self.client.get(source.discovery_url, headers=source.headers)
            if not 200 <= catalog_response.status_code < 300:
                raise ValueError("Extension catalog request failed")
            if catalog_response.headers.get("content-type", "").split(";", 1)[0].lower() != "application/json":
                raise ValueError("Extension catalog must be application/json")
            try:
                catalog = catalog_response.json()
            except ValueError as error:
                raise ValueError("Extension returned invalid JSON") from error
            entries = catalog.get("operations") if isinstance(catalog, dict) else None
            if not isinstance(entries, list):
                raise ValueError("Invalid extension catalog")
            names = set()
            for entry in entries:
                if not isinstance(entry, dict) or not isinstance(entry.get("kind"), str):
                    raise ValueError("Invalid catalog operation")
                kind = entry["kind"]
                if kind in names or kind in seen:
                    raise ValueError(f"Duplicate operation kind: {kind}")
                names.add(kind)
                if source.allow_operations and kind not in source.allow_operations:
                    continue
                operation = self._operation(source, base, entry)
                seen.add(operation.kind)
                operations.append(operation)
            missing = set(source.allow_operations) - names
            if missing:
                raise ValueError(f"Allowed operation not found: {sorted(missing)[0]}")
        return operations

    def _operation(self, source: ExtensionSource, base: str, entry: dict) -> HttpOperation:
        if not isinstance(entry, dict) or not isinstance(entry.get("kind"), str):
            raise ValueError("Invalid catalog operation")
        kind = entry["kind"]
        schema = self._get_json(base, entry.get("schema_url"), source)
        spec = _schema_spec(kind, schema)
        helpers = []
        helper_names = set()
        for item in entry.get("helpers", []):
            if not isinstance(item, dict) or not isinstance(item.get("name"), str) or item["name"] in helper_names:
                raise ValueError("Invalid or duplicate helper")
            helper_names.add(item["name"])
            helper_schema = self._get_json(base, item.get("schema_url"), source)
            helper_spec = _schema_spec(item["name"], helper_schema, True)
            invoke_url = self._url(base, item.get("invoke_url"))
            def invoke(rendered, invocation, current, url=invoke_url, hs=helper_spec):
                invocation = hs.validate_options(invocation)
                current = spec.validate_options(current)
                response = self.client.post(url, headers=source.headers, data={"invocation_options": json.dumps(invocation), "current_options": json.dumps(current), "width": str(rendered.width), "height": str(rendered.height)}, files={"image": ("image.png", rendered.image, "image/png")})
                if response.status_code < 200 or response.status_code >= 300:
                    raise ValueError(f"Extension helper failed: {response.status_code}")
                result = response.json()
                if not isinstance(result, dict) or not isinstance(result.get("options"), dict):
                    raise ValueError("Invalid helper response")
                return spec.validate_options(result["options"])
            helpers.append(Helper(item["name"], helper_spec, invoke, helper_schema.get("x-hint-display-name", helper_schema.get("title")), helper_schema.get("description", "")))
        return HttpOperation(kind, spec, self._url(base, entry.get("render_url")), tuple(helpers), self.client, source.headers or {}, bool(schema.get("x-hint-require-image", False)), source.render_timeout_seconds)

    def _get_json(self, base, path, source):
        response = self.client.get(self._url(base, path), headers=source.headers)
        if response.status_code < 200 or response.status_code >= 300:
            raise ValueError("Extension schema request failed")
        try:
            return response.json()
        except ValueError as error:
            raise ValueError("Extension returned invalid JSON") from error

    @staticmethod
    def _url(base, path):
        if not isinstance(path, str) or not path.startswith("/"):
            raise ValueError("Extension URLs must be absolute same-origin paths")
        parsed = urlparse(path)
        decoded_path = unquote(parsed.path)
        if parsed.query or parsed.fragment or parsed.netloc or "\\" in decoded_path or any(part in {".", ".."} for part in decoded_path.split("/")):
            raise ValueError("Extension URLs must be absolute same-origin paths")
        result = urljoin(base, path)
        resolved = urlparse(result)
        origin = urlparse(base)
        if (resolved.scheme, resolved.hostname, resolved.port) != (origin.scheme, origin.hostname, origin.port):
            raise ValueError("Extension URL changes authority")
        return result
