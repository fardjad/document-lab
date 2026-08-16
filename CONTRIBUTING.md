# Contributing

Thank you for contributing to DocumentLab. Keep changes focused on the editor's current client/server architecture: a React/Bun client, a FastAPI processor, pure project and pipeline model types, application use cases and ports, infrastructure adapters, and independently deployed HTTP image extensions.

## Development setup

Install Python dependencies with `uv` in each Python project and install frontend dependencies with Bun:

```bash
cd processor
uv sync
cd ../extensions/core
uv sync
cd ../../frontend
bun install
```

From the repository root, the supported integrated development command is:

```bash
just dev
```

It starts the core extension on `9101`, the processor on `8000`, and the frontend on `3000`. Open <http://localhost:3000>. The command supplies `EXTENSIONS_REGISTRY_PATH=extensions.yaml` to the processor and cleans up the process group when stopped.

Useful environment inputs include:

- `PROJECTS_ROOT`: processor project storage directory. It defaults to `processor/projects`.
- `CACHE_TTL_SECONDS`: render-cache lifetime in seconds. It defaults to `86400`.
- `CORS_ORIGINS`: comma-separated allowed client origins.
- `EXTENSIONS_REGISTRY_PATH`: YAML registry used for HTTP extension discovery.
- `EXTENSIONS_ROOT`: fallback local extension directory when HTTP discovery is not configured.
- `PORT`: frontend port, default `3000`.
- `BACKEND_PORT`: processor port used by the frontend proxy, default `8000`.

Do not commit generated project data, secrets, model caches, or test artifacts.

## Repository boundaries

Follow the existing dependency direction:

- `processor/model/` contains technology-agnostic `Project`, `View`, `Pipeline`, `Operation`, and related value objects. Do not put FastAPI, image libraries, filesystem access, schemas, or render state there.
- `processor/application/{feature}/usecases/` coordinates workflows. `processor/application/{feature}/ports/` contains contracts and port data needed by those workflows.
- `processor/infrastructure/` implements ports and owns HTTP, filesystem, image-library, and extension-service boundaries.
- `processor/config/` reads and validates environment and registry inputs.
- `processor/main.py` composes dependencies and creates the application.
- `frontend/` contains client UI and the API client.
- `extensions/` contains independently runnable operation services. Plugin implementation details and heavyweight image dependencies belong there, not in the model.

When adding behavior, prefer the narrowest existing layer. Add a new port or abstraction only when a real technology or test seam requires it.

## Making changes

1. Read the relevant model, use case, adapter, and tests before editing.
2. Keep one behavior change per focused patch.
3. Preserve public API and on-disk compatibility unless the change explicitly updates the contract.
4. Add or update a test for every non-trivial behavior, especially path handling, schema validation, image dimensions, pipeline ordering, helper placement, and error mapping.
5. Update documentation when an endpoint, environment input, extension contract, or user-facing workflow changes.
6. Run the formatter or existing automatic fixer before manual cleanup.
7. Run the narrowest relevant tests, then the broader checks when practical.

## Testing and checks

### Processor tests

```bash
cd processor
uv run pytest
```

Python tests use the `*_test.py` naming convention. The processor test configuration includes the processor package and core extension source on its test path.

### Core extension tests

```bash
cd extensions/core
uv run pytest
```

Extension tests should verify the service directly: health, catalog shape, schema validation, render media type and dimension headers, invalid image handling, and helper responses.

### Frontend build and browser tests

```bash
cd frontend
bun run build
bun run test:e2e
```

The browser tests use Playwright and exercise the client through the development server. Keep fixtures small and isolated under `frontend/tests/fixtures`.

### Integrated smoke test

Run the complete stack and verify:

```bash
curl --fail http://127.0.0.1:9101/health
curl --fail http://127.0.0.1:9101/operations
curl --fail http://127.0.0.1:8000/api/operations
```

Then import a PNG, create a view, add an operation, preview it, and save the pipeline in the browser. Stop `just dev` after the check.

## API and extension changes

The processor's public routes are documented in the [README](README.md). Plugin authors must follow [PLUGIN_AUTHORING.md](docs/PLUGIN_AUTHORING.md), including the catalog, draft 2020-12 object schemas, multipart render/helper requests, PNG response headers, and controlled errors.

When changing an operation:

- Keep the operation kind stable when persisted pipelines should remain compatible.
- Put domain-neutral option structure in the plugin's schema and operation-specific validation beside the plugin.
- Make image output dimensions explicit and test them.
- Keep helpers owned by their operation and return options for that operation only.
- Test discovery failures and failed reload rollback if catalog or schema behavior changes.

When changing a processor route, update the request and response behavior, status-code tests, and documentation together. Avoid leaking framework request objects into model or application code.

## Documentation and assets

Documentation is Markdown. Keep architecture documentation conceptual and use links to detailed protocol documentation rather than duplicating implementation plans. README screenshots use the expected relative paths:

- `media/workspace.png`
- `media/pipeline.png`

If adding screenshots, use representative current UI states and keep the files small enough for repository use.

## Pull requests

A useful pull request description includes:

- the user-visible or maintainability outcome,
- the files and architectural layer changed,
- API, schema, persistence, or compatibility implications,
- tests and commands run,
- any environment or deployment steps required.

Keep unrelated formatting churn out of the change. Do not commit generated lockfile changes unless dependencies intentionally changed. Review the diff for accidental code, configuration, secrets, screenshots, or test-artifact changes.

## Commit and review guidance

Use concise imperative commit subjects when commits are requested. Keep commits atomic and do not use Conventional Commits prefixes. Reviewers should be able to identify the behavior, boundary, and validation evidence from the diff.

Before requesting review, confirm:

- [ ] Only intended files changed.
- [ ] Relevant unit, integration, build, or browser checks passed.
- [ ] New public behavior is documented.
- [ ] No credentials or generated data are included.
- [ ] The architecture and dependency direction remain intact.
