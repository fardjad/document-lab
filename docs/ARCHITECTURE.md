# Architecture

## 1. Overview

Document-cropper is a tool for extensible, procedural image editing. A user uploads a PNG document image, then creates named **views** of that image. A view is a projection produced by applying an ordered pipeline of operations such as cropping, rotating, deskewing, trimming, and removing a background. Each operation receives the output of the previous operation. The final operation output is the rendered image returned to the client.

The backend is a FastAPI processor. HTTP translation lives at the edge, application use cases coordinate work, the domain model describes projects and pipelines, and infrastructure supplies filesystem and image-library implementations. The React/Bun frontend communicates with the `/api` endpoints defined in `processor/infrastructure/http_api.py`.

## 2. Domain model

The model is deliberately small and technology-agnostic. It contains four first-class concepts and their value objects:

- **`Project`** (`processor/model/project.py`) owns a `ProjectId`, a `ProjectImage`, `next_view_id`, and a tuple of `View` objects. `ProjectId` accepts only safe identifier strings. `ProjectImage` contains PNG bytes and can be created with `ProjectImage.from_png`, which checks the PNG signature. `Project` enforces unique positive view IDs and a `next_view_id` greater than every existing ID. Adding a view advances the counter monotonically; deleting a view does not reuse its ID.
- **`View`** (`processor/model/view.py`) is a named projection: `View(id, name, pipeline)`. Names are trimmed, printable, non-empty strings of at most 100 characters. A view has no crop coordinates property. Crop is a normal pipeline operation, which keeps all image-editing steps in one ordered representation. `with_pipeline` creates the same view bound to another pipeline, useful for updates and previews.
- **`Pipeline`** (`processor/model/pipeline.py`) owns an ordered tuple of generic `Operation` values. The list defines execution order. An empty pipeline is an identity transform. Its `without` helper can filter operations by kind, but rendering itself remains an application concern.
- **`Operation`** (`processor/model/operation.py`) is a structural value containing a non-empty string `kind` and a dictionary of `options`. The model copies the options dictionary and checks only this structure. Domain-specific validation, such as angle bounds or required option keys, belongs to the corresponding infrastructure plugin.

These types contain no PIL/OpenCV or other image-library calls, no filesystem access, no HTTP request parsing, and no render state. The model expresses domain meaning using standard-library data structures only. Image bytes are retained by `ProjectImage` because a source PNG is part of a project, but intermediate render state is intentionally not a model concept.

## 3. Layered architecture

The dependency direction points inward:

```text
config inputs -> main.py composition -> infrastructure adapters
                                      -> application use cases -> model
```

### Model

`processor/model/` contains pure entities, value objects, and domain rules: `Project`, `ProjectId`, `ProjectImage`, `View`, `Pipeline`, and `Operation`. It must not depend on FastAPI, PIL, OpenCV, the filesystem, or storage formats.

### Application

`processor/application/` is organized by feature. View orchestration is under `application/view/usecases/`, with outbound contracts under `application/view/ports/`. Use cases handle validation coordination, lookup, persistence coordination, and the pipeline render fold. Ports describe what the use cases need without choosing a technology. For example, `ProjectViewStore` reads and writes view metadata, while `OperationRegistry` resolves image operation plugins.

Application code does not contain route handlers, request parsing, framework setup, or image-library implementation details. It can depend on model types and application ports.

### Infrastructure

`processor/infrastructure/` implements application ports and owns technology boundaries. `http_api.py` translates FastAPI requests and responses. `file_store/` contains the filesystem adapter and YAML translation. `image_processor/` contains image-library integrations and operation plugins. Infrastructure translates external shapes into model and application types at explicit boundaries.

### Config and composition

`processor/config/` reads and validates environment inputs such as the project root and CORS origins. `processor/main.py` constructs settings, the filesystem store, image collaborators, operation instances, the registry, use cases, and the FastAPI application. Dependency wiring stays there rather than inside model or use-case modules.

This structure keeps image behavior in the repository while avoiding unrelated general persistence, database, jobs, CLI, or audio layers. New abstractions should be added only when a required boundary needs them.

## 4. Port contract types

Several types under `processor/application/view/ports/` are contracts between application orchestration and infrastructure plugins. They are not domain entities.

### `RenderedRegion`

`RenderedRegion` contains `image: bytes`, `width`, and `height`. It is the intermediate render state passed from one operation to the next. Width and height travel with the bytes so each plugin can calculate its output dimensions without a separate geometry pass. Because it carries encoded image bytes and render state, it belongs in the application port layer rather than the pure model.

### `OperationSpec`

`OperationSpec` describes one operation's options: its `kind`, a schema dictionary for consumers, and a callable validator. `validate_options` checks the input shape and requires the validator to return a dictionary. The actual validation function is defined beside its plugin. This is an application/plugin contract descriptor, not domain meaning, so `OperationSpec` does not belong in `processor/model/`.

### `Helper`

`Helper` describes an operation-specific auxiliary action with a `name`, an `invocation_spec`, and an invocation callable. The callable receives the rendered image at the operation's position, validated invocation options, and the operation's current options. It returns updated operation options. The contract checks these boundaries and requires a dictionary result.

`ProjectViewStore` is the view metadata port. It exposes `read_project_views(ProjectId) -> Project` and `write_project_views(ProjectId, Project)`. The image reader and image-size reader used by rendering are injected collaborators from the project application ports.

## 5. Plugin architecture

Operations are self-contained infrastructure plugins. Each plugin owns:

1. Its operation kind string.
2. Its `OperationSpec` and pure options validator.
3. Its `render(RenderedRegion, options)` implementation.
4. Zero or more `Helper` values.

For example, `processor/infrastructure/image_processor/operations/rotate.py` contains the rotate validator, `ROTATE_SPEC`, and `RotateOperation`. There is no central operation-spec file. `OperationRegistryImpl` indexes complete operation instances by `kind`; `get` resolves an operation and `spec_for` exposes its spec for application validation. The registry does not implement image processing.

To add a basic operation, create a module containing the validator, spec, and operation class, then add an instance to the registry construction in `main.py`. The application can then render it and `UpdateView` can validate it without importing an image library.

Helpers belong to their operation's `helpers` tuple. They are not stored in a second global registry. A helper runs against the image as it exists immediately before its owning operation, accepts its own invocation options, and returns options for that one operation. `auto_straighten` and `auto_trim` use this mechanism.

If a future automatic action must change multiple operations, use one meta-operation whose options encapsulate the sub-operations. Its helper returns the meta-operation options, and its executor delegates to the contained operations. This preserves the one-operation-in, one-operation-options-out helper contract.

## 6. Existing operations

All five plugins are registered in `processor/main.py`:

- **`crop`** (`crop.py`) accepts `{x, y, width, height}`. Values are finite normalized real numbers in the range `[0, 1]`, with a positive rectangle contained in the source. It normally appears first and crops a normalized sub-region.
- **`rotate`** (`rotate.py`) accepts `{degrees}` where degrees is an integer multiple of 90. It canonicalizes the value modulo 360 and performs a quarter-turn rotation. A 90- or 270-degree turn swaps width and height.
- **`straighten`** (`straighten.py`) accepts `{angle}` as a finite real number between -45 and 45 degrees. It deskews with bicubic resampling and transparent expansion padding. It provides the `auto_straighten` helper, which delegates skew detection to the injected document analyzer.
- **`trim`** (`trim.py`) accepts `{top, right, bottom, left}` as non-negative integer pixel counts. It removes pixels from each edge and rejects a result that would have zero or negative dimensions. It provides the `auto_trim` helper, which delegates border detection to the analyzer.
- **`remove_background`** (`remove_background.py`) accepts model and thresholding options, including a model name, alpha-matting flags and thresholds, erosion size, and post-processing flag. It delegates removal to the injected background remover and preserves the resulting image dimensions.

Trim and crop can produce similar visual results but intentionally have different input semantics. Crop uses a normalized rectangle, while trim uses integer edge-pixel counts. Both are ordinary plugins rather than special view properties.

## 7. End-to-end flow: from upload to rendered image

### Project creation

The actual endpoint is `POST /api/projects` with a project ID query parameter and an uploaded file. The flow is:

1. The HTTP handler reads the upload bytes and calls `ProjectImage.from_png`.
2. The handler calls the `CreateProject` use case.
3. `CreateProject` validates the project ID and uniqueness, then asks the filesystem store to create the project.
4. `FilesystemProjectStore` creates `projects/{project_id}/` under the configured root and atomically writes `image.png`. View metadata is created when the first view is written.

Project image replacement uses `PUT /api/projects/{project_id}` and resets view metadata through the project store.

### View creation

`POST /api/projects/{id}/views` accepts a name and optional pipeline. The handler translates the request into model `Operation` and `Pipeline` values, then:

1. `CreateView` validates the project ID and takes the view write lock.
2. It reads current view metadata, uses `current.next_view_id`, and constructs a `View`.
3. It adds the view to the immutable `Project` and writes the result through `ProjectViewStore`.
4. The filesystem adapter writes `project.yaml` as version 4 with `version`, `next_view_id`, and `views`, where each view contains `id`, `name`, and serialized pipeline entries.

`PUT /api/projects/{id}/views/{view_id}` replaces the name and complete pipeline. `UpdateView` validates every operation through `registry.spec_for(kind)` before persisting. `GET /api/projects/{id}/views` lists metadata, and `DELETE` removes a view.

### View rendering

`GET /api/projects/{id}/views/{view_id}/render` calls `RenderView.render`:

1. Validate the project ID and read `Project` view metadata. This is a cheap metadata read and does not load source image bytes.
2. Find the requested view, then read the source PNG bytes through the image reader.
3. Read the source dimensions through the image-size reader, which parses the PNG header.
4. Build `RenderedRegion(image_bytes, width, height)`.
5. Fold the pipeline in order. For each model `Operation`, resolve its plugin with `registry.get(op.kind)`, call `operation.render(rendered, op.options)`, and replace the current rendered region with the returned region.
6. Return `rendered.image` as the PNG HTTP response.

The use case wraps unexpected rendering failures as `ViewRenderError`; the HTTP layer maps those to a 422 response.

### View preview

`POST /api/projects/{id}/views/{view_id}/render` accepts an override pipeline. `RenderView.preview` loads the source and selected view in the same way, substitutes the supplied pipeline for that render only, performs the same ordered fold, and does not persist the override.

### Helper invocation

The HTTP endpoints are `POST /api/projects/{id}/views/{view_id}/auto/straighten` and `/auto/trim`:

1. The handler identifies the target operation index, using the first operation of the relevant kind or the end of the pipeline if that operation is absent.
2. `InvokeHelper` validates the project and view, reads the source bytes and dimensions, and creates the initial `RenderedRegion`.
3. It renders operations before the target index, so the helper sees the image at the operation's pipeline position.
4. It resolves the target operation by kind, or derives a kind from the helper name when the target is beyond the current pipeline, then finds the named helper in that operation's `helpers` tuple.
5. It validates invocation options with `helper.invocation_spec`.
6. It calls `helper.invoke(rendered, validated_invocation_options, current_options)` and returns the suggested options.
7. The frontend applies the suggestion to the pipeline. Helper invocation itself does not persist a view.

## 8. On-disk layout

The configured project root contains one directory per project:

```text
projects/
  {project_id}/
    image.png         # source PNG image
    project.yaml      # view metadata, version 4
```

A representative `project.yaml` is:

```yaml
version: 4
next_view_id: 2
views:
  - id: 1
    name: Receipt
    pipeline:
      - kind: crop
        options: {x: 0.1, y: 0.1, width: 0.35, height: 0.325}
      - kind: rotate
        options: {degrees: 0}
      - kind: straighten
        options: {angle: 0.0}
      - kind: trim
        options: {top: 0, right: 0, bottom: 0, left: 0}
```

The filesystem store validates project paths and metadata shapes, and uses atomic writes with file and directory syncing for image and YAML updates. A missing `project.yaml` reads as a project with no views.

Version 3 metadata remains readable for backward compatibility. A v3 region's `rectangle` is converted on read into a `crop` operation inserted at pipeline index 0; the remaining v3 pipeline follows it. New writes always use version 4 and the `views`/`pipeline` representation.

## 9. Adding a new operation

1. Create `processor/infrastructure/image_processor/operations/new_op.py`.
2. Define a pure `validate_new_op(options: dict) -> dict` function. It should validate and canonicalize options, raising `ValueError` for invalid input.
3. Define `NEW_OP_SPEC = OperationSpec("new_op", schema, validate_new_op)`.
4. Define `NewOpOperation` with `kind = "new_op"`, `spec = NEW_OP_SPEC`, a `helpers` tuple (empty if none), and a `render` method that accepts a `RenderedRegion` and returns a new `RenderedRegion`.
5. Add `NewOpOperation(...)` to the `OperationRegistryImpl` list in `processor/main.py`, injecting any required infrastructure collaborator there.
6. The frontend can now send pipeline entries with `kind: "new_op"`; `UpdateView` will validate their options through the registry before saving.
7. If automatic detection is needed, define an invocation `OperationSpec` and a `Helper` in the same plugin module, then include it in the operation's `helpers` tuple. The helper should return options for this operation only.

The new plugin may use PIL, OpenCV, or another library because it is infrastructure. Keep the operation's application-facing contract limited to `RenderedRegion`, dictionaries, and its declared spec/helper types. Do not move image-library concerns into the model or add a separate central operation specification registry.
