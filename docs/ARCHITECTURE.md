# Architecture

## Overview

DocumentLab is an extensible procedural image editor. A browser client presents projects, views, and ordered pipelines. A FastAPI processor owns project metadata, source images, persistence, rendering orchestration, and the public application API. Image operations are supplied by independently running HTTP extension services.

```text
browser client ── /api ──> processor ──> operation registry ──> HTTP extensions
                              │
                              ├── project and view storage
                              ├── pipeline render fold
                              └── render cache
```

The processor does not need to import an extension's image library. An extension may run locally, in a container, on another host, or with specialized hardware. The processor discovers its operations from a catalog and communicates through the v1 protocol described in [Plugin authoring](PLUGIN_AUTHORING.md).

## Client and server responsibilities

The React/Bun client is a presentation layer. It imports images, displays projects and named views, edits pipeline entries, invokes helpers, previews unsaved changes, and saves a complete view pipeline. It obtains operation metadata from the processor, so controls and operation choices can follow the active registry.

The processor is the system of record for projects and views. It validates request shapes, coordinates use cases, validates operation options against discovered schemas, persists metadata, renders pipelines, and translates application outcomes into HTTP responses. It does not make the client responsible for image processing or pipeline execution.

A lightweight Bun server serves the client and forwards `/api` requests to the processor. The browser therefore uses one client origin while the processor and extension services remain separately deployable.

## Domain concepts

The model is intentionally small and technology agnostic:

- A **project** has a stable identifier, a source PNG, a display name, and named views.
- A **view** has an identifier, a name, and a pipeline. It has no crop-coordinate property.
- A **pipeline** is an ordered collection of operations. An empty pipeline is an identity transform.
- An **operation** has a kind, options, and an enabled state. The model checks structural validity but does not know image-library rules.

Crop is a normal pipeline operation with a normalized rectangle. Trim is a separate operation using integer edge-pixel counts. Keeping both as operations makes every image transformation composable and preserves one consistent representation for persistence, preview, and rendering.

The model contains no HTTP request parsing, framework objects, filesystem access, schema documents, or intermediate render state. Image bytes are part of the project source value, while the bytes and dimensions passed between operations belong to an application-level render contract.

## Layering

Dependencies point toward the model:

```text
configuration and composition
          ↓
infrastructure adapters and HTTP boundaries
          ↓
application use cases and ports
          ↓
pure domain model
```

### Model

The model expresses project, view, pipeline, operation, identifier, and invariant rules. It should remain independent of FastAPI, Pillow, OpenCV, YAML, HTTP clients, and the filesystem.

### Application

Application code is organized by feature. Use cases coordinate project and view workflows, permissions and validation, persistence boundaries, render sequencing, helper invocation, and cache coordination. Ports describe required collaborators such as project stores, operation registries, rendered regions, specifications, and helpers.

The pipeline render fold lives here: load the source, create the initial rendered region, resolve each enabled operation, call it in order, and pass its output to the next operation. Rendering is orchestration and therefore does not belong on the domain pipeline type.

A helper is similarly coordinated at the application boundary. The processor renders all enabled operations before the target position, invokes the operation-owned helper with that rendered region and options, validates the returned options, and exposes the suggestion to the client without persisting it automatically.

### Infrastructure

Infrastructure implements application ports and owns technology details:

- HTTP translates browser requests and extension responses.
- Filesystem adapters store source PNGs and project metadata.
- Image and extension adapters translate PNG bytes, dimensions, schemas, and errors.
- The HTTP extension adapter discovers catalogs, validates JSON Schemas, invokes render endpoints, and converts PNG responses into rendered regions.

Infrastructure must translate external representations at the boundary rather than leaking framework, network, or image-library types inward.

### Configuration and composition

Configuration reads environment values and the extension registry. Composition creates settings, stores, caches, operation adapters, registries, use cases, and the FastAPI application. Dependency wiring stays at the composition boundary. Runtime behavior should not silently read process environment or construct global infrastructure inside a use case.

## Extension architecture

An operation is a plugin-owned capability. Each operation publishes:

1. a stable kind,
2. an options JSON Schema,
3. a render endpoint,
4. optional operation-owned helpers and their invocation schemas.

The processor loads a YAML registry of extension discovery URLs. For each source it checks health, fetches the catalog, applies any operation allow-list, fetches selected schemas, validates the complete proposal, and then atomically replaces the active registry. A malformed catalog, duplicate kind, invalid schema, failed health check, or missing allowed kind does not replace the previous registry.

Schemas serve three related purposes: they define option shape, provide local validation before persistence or dispatch, and supply UI metadata such as names, descriptions, defaults, icons, and control hints. The processor supports constrained draft 2020-12 object schemas and rejects unsupported references. The full v1 contract, including URL safety and media headers, is maintained in [PLUGIN_AUTHORING.md](PLUGIN_AUTHORING.md).

Helpers are accessed through their owning operation rather than a second global helper registry. A helper returns options for one operation. If an automatic action needs to change multiple operations in the future, it should be represented as one meta-operation whose options contain the coordinated state.

The current core extension service publishes crop, rotate, straighten, trim, and remove-background operations. It also publishes auto-straighten and auto-trim helpers. The architecture does not require future extensions to use Python, Pillow, or the same deployment model.

## Main workflows

### Import and project storage

The client uploads a PNG to the processor. The processor validates the image, derives a safe project identifier from the upload name, and asks the project store to persist it. A project source is stored separately from view metadata. Replacing the source resets view metadata through the project workflow; deleting a project removes its stored data.

### View editing

The client creates a named view with an optional pipeline. Updating a view replaces its name and complete pipeline. The processor validates every operation kind and options through the active registry before writing metadata. The client can disable, reorder, add, or remove operations while editing.

### Preview and render

A saved render loads the source and view, then folds the enabled pipeline in order. Intermediate results carry PNG bytes and width/height. The processor may cache completed steps for saved renders. A preview accepts a pipeline override, follows the same fold, and does not persist that override. Successful public renders are PNG responses; download renders include attachment metadata.

### Helpers

The client invokes a named helper for a view. The processor renders the image up to the target operation, calls that operation's helper, validates the resulting options, and returns them. The client merges the suggestion into the working pipeline. Saving remains an explicit user action.

## Persistence and boundaries

The project root contains one directory per project:

```text
projects/
  <project-id>/
    image.png
    project.yaml
```

`project.yaml` stores the view representation and pipeline operations. The filesystem boundary validates project paths and metadata and writes updates atomically. Persistence format details belong to the storage adapter and should not become domain concepts.

## Extension and deployment ownership

The extension service owns its runtime, dependencies, model assets, process lifecycle, resource limits, and CPU/GPU configuration. The processor owns its registry file, project data, view pipelines, cache, and public API. The deployment platform owns service startup, scaling, TLS, secrets, and network policy.

The processor's registry can supply per-source headers, but credentials must not be embedded in discovery URLs. For services beyond a trusted local network, use deployment-managed HTTPS and authentication controls. Reload refreshes catalog and schema state; it never installs packages or controls service processes.

## Adding capabilities

To add an operation, implement the v1 service contract, publish it in a catalog, provide a valid schema, test render output and dimensions, and add the source or allow-list entry to deployment configuration. The processor then exposes the discovered metadata and can validate the kind in persisted pipelines.

To add a processor workflow, keep request translation at the HTTP edge, coordination in a feature use case, domain rules in the model, and external effects behind an existing or justified application port. Keep composition in the application startup boundary. Update tests and the relevant public documentation together.
