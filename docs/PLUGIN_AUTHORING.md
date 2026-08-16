# Plugin authoring

This guide specifies the v1 HTTP extension contract used by the processor. A plugin is an independently deployed HTTP service that publishes one or more image operations. The service owns its language, framework, dependencies, process lifecycle, CPU/GPU selection, and resource configuration. The processor owns projects, views, pipeline order, local option validation, rendering orchestration, and the public `/api` API.

The contract is intentionally small: health, an operation catalog, JSON Schema documents, a PNG render endpoint, and optional helper endpoints. The processor does not import plugin code and does not start or configure plugin processes.

## 1. Service lifecycle and registry

Run a plugin service independently. For local development, the repository's core service is started with:

```bash
cd extensions/core
uv run fastapi dev src/core/app.py --port 9101
```

The processor reads a YAML registry path from `EXTENSIONS_REGISTRY_PATH`. A registry contains a `sources` list:

```yaml
sources:
  - discovery_url: http://127.0.0.1:9101/operations
  - discovery_url: https://plugins.example.net/document-tools/operations
    allow_operations: [rotate, straighten]
    headers:
      Authorization: Bearer deployment-secret
```

`discovery_url` must be an absolute `http` or `https` URL with a host, and it must not contain credentials, a query, or a fragment. `allow_operations` is optional. If omitted, every catalog entry from that source is selected. If present, only named kinds are selected, and every allowed name must exist in the catalog. Duplicate names are invalid. `headers` is an optional string-to-string mapping sent to health, catalog, schema, render, and helper requests. Keep secrets in deployment-managed configuration rather than committing them.

The processor checks each source's health, fetches and validates its catalog and selected schemas, then creates HTTP-backed operations. Duplicate operation kinds across sources are rejected. `POST /api/operations/reload` rereads the registry and performs the same discovery transaction without restarting the processor. `SIGHUP` also triggers reload when HTTP discovery is configured. A failed reload leaves the previous active registry in place. Reload does not install, start, stop, or update services.

## 2. Contract rules

- All resource documents are JSON.
- All plugin render and helper requests use `multipart/form-data`.
- Input images are PNG files.
- Successful render responses are PNG bytes with positive `X-Image-Width` and `X-Image-Height` headers.
- Catalog, schema, and helper URLs are absolute same-origin paths beginning with `/`. They must not contain a query, fragment, authority, backslash, `.` or `..` path component, encoded traversal, or a redirect to another origin.
- `kind` is unique in a catalog and across all discovered sources.
- Helper names are unique within an operation.
- A catalog may contain no operations.
- The processor does not follow redirects as a way to change a plugin's authority.
- The processor validates schemas and operation options locally, but the service must validate again before execution.
- v1 has no configured timeout, image-size cap, response-size cap, or automatic render/helper retry. Add operational controls at the service boundary if the deployment needs them, while preserving this semantic contract.

## 3. Health endpoint

### `GET /health`

Every service exposes health at its origin. Any `2xx` status is healthy. The response body is not part of v1 and may be empty or JSON. The configured source headers are sent with this request.

A non-`2xx` response makes discovery fail. Health is checked during initial loading and every reload.

## 4. Operation catalog

### `GET /operations`

The response must be `application/json` with an object containing an `operations` array. A catalog entry has this shape:

```json
{
  "operations": [
    {
      "kind": "rotate",
      "schema_url": "/operations/rotate/schema.json",
      "render_url": "/operations/rotate/render",
      "helpers": [
        {
          "name": "auto_rotate",
          "schema_url": "/operations/rotate/helpers/auto_rotate/schema.json",
          "invoke_url": "/operations/rotate/helpers/auto_rotate/invoke"
        }
      ]
    }
  ]
}
```

Each entry must contain:

| Field | Type | Meaning |
| --- | --- | --- |
| `kind` | string | Stable, non-duplicate pipeline operation identifier. |
| `schema_url` | string | Absolute same-origin path to the operation options schema. |
| `render_url` | string | Absolute same-origin path for render requests. |
| `helpers` | array | Zero or more helper descriptors. |

Each helper descriptor must contain a unique `name`, `schema_url`, and `invoke_url`. The processor does not infer endpoint paths or helper behavior from naming conventions.

The catalog itself does not carry display metadata. Display name, description, icon, defaults, and UI hints come from the operation schema. Helper display metadata comes from the helper schema.

## 5. Operation schema

### `GET <schema_url>`

Return a JSON Schema draft 2020-12 object for the operation's options. The processor accepts an object schema without `$ref` or `$dynamicRef` anywhere in the document. Schemas must be valid according to `Draft202012Validator`. The schema's properties, required names, types, constraints, and defaults are the source of local validation and the processor's operation metadata.

A useful baseline is:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "title": "Rotate",
  "description": "Rotate the image in 90-degree increments",
  "x-hint-icon": "Rotate90DegreesCcw",
  "x-hint-require-image": true,
  "properties": {
    "degrees": {
      "type": "integer",
      "enum": [0, 90, 180, 270],
      "default": 0,
      "title": "Degrees",
      "description": "Rotation angle",
      "x-hint-ui-control": "slider"
    }
  },
  "required": ["degrees"]
}
```

### Recognized metadata

| Field | Location | Meaning |
| --- | --- | --- |
| `x-hint-require-image` | schema root | Boolean. `true` means render receives an input image. Defaults to `false`. |
| `x-hint-icon` | schema root | Optional frontend icon identifier. |
| `x-hint-display-name` | schema root or property | Optional preferred display label. Otherwise `title` is used. |

Standard schema fields such as `title`, `description`, `default`, `enum`, `minimum`, `maximum`, `multipleOf`, and `format` should be used for semantics. The processor currently reads root `title`, `description`, `x-hint-display-name`, `x-hint-icon`, and `x-hint-require-image`; other valid schema metadata is retained in the schema but is not interpreted by the processor. Unknown `x-hint-*` fields are ignored for forward compatibility. A plugin may include UI hints such as `x-hint-ui-control` for clients that understand them, but they are not required processor behavior in v1.

Defaults must validate against their property's schema. A schema with no options should use `type: object`, `properties: {}`, `required: []`, and `additionalProperties: false`. The processor derives operation defaults from property-level `default` values. An operation that requires an image should set `x-hint-require-image: true`; the current core operations do so.

## 6. Render protocol

### `POST <render_url>`

Send `multipart/form-data`:

| Part | Required | Content |
| --- | --- | --- |
| `options` | Yes | JSON object encoded as a form field. |
| `image` | When `x-hint-require-image` is `true` | PNG file named `image.png`, with media type `image/png`. It is the image already rendered at this pipeline position. |
| `width` | With `image` | Integer input width. |
| `height` | With `image` | Integer input height. |

The processor validates `options` against the schema before sending it. The service must parse the JSON object and validate its complete operation-specific semantics before processing. It may canonicalize values, but the returned image must represent the accepted options.

On success, return:

```text
HTTP/1.1 200 OK
Content-Type: image/png
X-Image-Width: 90
X-Image-Height: 120

(binary PNG)
```

`Content-Type` must be `image/png` and both dimension headers must be positive integers matching the returned image. The processor rejects non-PNG responses, missing dimensions, non-positive dimensions, and non-`2xx` statuses.

### Error responses

For invalid options, invalid images, unavailable dependencies, and execution failures, return a non-`2xx` status. A structured error body is recommended:

```json
{
  "code": "invalid_options",
  "message": "degrees must be a multiple of 90"
}
```

The core service uses `422` with `code` values such as `invalid_options` and `invalid_image`. The processor translates a failed plugin request into a controlled processor render error rather than persisting a partial result.

## 7. Helper protocol

Helpers are operation-owned actions. A helper receives one rendered region and returns options for its owning operation. It must not edit multiple pipeline entries.

### `GET <helper.schema_url>`

Return a separate JSON Schema object for helper invocation options. It uses the same schema rules and metadata fields as an operation schema. A no-argument helper returns an empty object schema. The helper's root `title`, `description`, and optional `x-hint-display-name` become its display metadata.

### `POST <helper.invoke_url>`

Send `multipart/form-data`:

| Part | Required | Content |
| --- | --- | --- |
| `image` | Yes | PNG rendered through every enabled operation before the target operation. |
| `width` | Yes | Integer width of `image`. |
| `height` | Yes | Integer height of `image`. |
| `invocation_options` | Yes | JSON object validated against the helper schema. |
| `current_options` | Yes | JSON object for the target operation. When the helper inserts an operation, use the operation's defaults or `{}` as appropriate. |

On success return JSON containing an `options` object:

```json
{
  "options": {
    "top": 4,
    "right": 3,
    "bottom": 4,
    "left": 3
  }
}
```

The processor validates the returned options against the owning operation schema before exposing them to the client. A helper invoked through the processor's public route is non-persistent: the frontend applies the returned options to its working pipeline, and the user saves separately.

If the target operation is disabled, the processor refuses helper invocation. When a helper is requested for an operation not yet in the pipeline, the processor can resolve the helper's owning operation from the discovered catalog and supplies its default options.

## 8. Current core service

The repository's `extensions/core` service currently publishes these operations:

- `crop`: normalized `x`, `y`, `width`, and `height` rectangle values contained in `[0, 1]`.
- `rotate`: integer `degrees` in quarter turns, canonicalized modulo 360.
- `straighten`: finite `angle` from `-45` through `45` degrees, rounded to a tenth; expands with transparent padding.
- `trim`: non-negative integer `top`, `right`, `bottom`, and `left` edge counts; rejects a trim that removes the entire image.
- `remove_background`: model selection plus alpha-matting and post-processing options.

It also publishes `auto_straighten` for `straighten` and `auto_trim` for `trim`. A plugin may publish any number of operations and helpers, including none.

## 9. Testing

### Unit and contract tests

Test the service directly with an HTTP test client or an actual local server. At minimum verify:

1. `GET /health` returns a `2xx` status.
2. `GET /operations` is valid JSON, contains unique kinds, and lists complete helper descriptors.
3. Every catalog URL returns a valid same-origin resource.
4. Every operation and helper schema is valid draft 2020-12 object JSON Schema, has valid defaults, and rejects malformed options.
5. Render rejects missing or invalid images when required.
6. Render returns PNG with matching positive dimension headers.
7. Render rejects invalid options, impossible geometry, and invalid images with controlled non-`2xx` responses.
8. Helper invocation validates invocation and current options and returns an `options` object accepted by the operation schema.
9. Helper output is deterministic for the same image and inputs when the operation is expected to be deterministic.

The core service tests can be run from its project directory:

```bash
cd extensions/core
uv run pytest
```

### Processor integration tests

Test through the processor's public API with a real or fixture HTTP service:

- `GET /api/operations` exposes the discovered schemas, defaults, metadata, and helpers.
- Create, update, preview, render, and delete a view using the discovered operation.
- Invoke a helper through `POST /api/projects/{project_id}/views/{view_id}/helpers/{helper_name}`.
- Verify an allow-list selects only named kinds and a missing allowed kind fails reload.
- Verify duplicate kinds, malformed catalogs, invalid schemas, failed health, non-PNG output, missing dimensions, and failed helper responses are rejected.
- Verify a failed reload does not replace the previously active registry.

Run processor tests from `processor/`:

```bash
cd processor
uv run pytest
```

### End-to-end browser tests

Run the client smoke tests from `frontend/` after the development services are available:

```bash
cd frontend
bun install
bun run test:e2e
```

## 10. Deployment

Deploy the plugin service separately from the processor. A container, system service, another host, or an orchestrator is acceptable. The operator owns:

- the service process and restart policy,
- the plugin runtime and lock file,
- CPU/GPU device selection,
- model downloads and caches,
- memory, concurrency, and filesystem limits,
- TLS termination and network exposure,
- secret injection for configured request headers.

The processor operator owns the registry file and `EXTENSIONS_REGISTRY_PATH`. The processor needs network access to the service's discovery URL and must be able to use the same origin for all catalog-declared paths. Use HTTPS and deployment-managed headers for services outside a trusted local network. Do not put credentials in the discovery URL.

For production, pin plugin dependencies, expose a health check that reflects service readiness, log request failures and render latency, and test the exact catalog and schemas served by the deployed artifact. Do not make reload execute installation scripts or process commands. Restart or scale the plugin through the deployment platform, then use `POST /api/operations/reload` to refresh the processor's catalog and schemas.

## 11. Compatibility checklist

Before publishing a plugin, confirm:

- [ ] The service has `GET /health` and `GET /operations`.
- [ ] The catalog has unique kinds and complete absolute same-origin URLs.
- [ ] Every selected operation has an object schema and render endpoint.
- [ ] Every helper has an object invocation schema and invoke endpoint.
- [ ] Schema defaults validate, and `x-hint-require-image` is correct.
- [ ] Render requests and responses use the exact multipart and PNG contract.
- [ ] Successful responses include matching positive `X-Image-Width` and `X-Image-Height` headers.
- [ ] Helper responses contain an `options` object accepted by the owning operation schema.
- [ ] Invalid inputs produce controlled non-`2xx` responses.
- [ ] Direct service tests and processor integration tests pass.
- [ ] Deployment configuration keeps runtime secrets and resources outside the repository registry.
