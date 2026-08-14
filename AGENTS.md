# Project journal

Read `JOURNAL.md` before planning or changing this project. It holds current product direction, constraints, prior decisions, and learned solutions.

After each user request is completed, update `JOURNAL.md`:

- Add dated entry under `## Journal entries` summarizing request, decision, and outcome.
- Update `## Current direction` when request changes active requirements.
- Record solved blockers, root causes, and durable fixes under `## Lessons learned` when work required investigation or troubleshooting.

Keep entries concise and factual. Do not record secrets, credentials, or transient command output. Preserve prior entries; correct them only when known inaccurate.

## Git commits

Commit only when user asks. Keep commits atomic: one coherent category of change per commit. Use concise imperative commit subjects that state outcome, with a body only when context is needed. Do not use Conventional Commits prefixes such as `feat:`, `fix:`, or `chore:`.

## Architecture and style guide

Backend uses explicit, meaningful layers. Required layout: `processor/model/`, `processor/application/{feature}/ports/`, `processor/application/{feature}/usecases/`, `processor/infrastructure/`, and `processor/config/`; composition stays in `processor/main.py`. Do not add placeholder-only packages or unnecessary abstractions.

### Architecture and placement

- Keep dependency direction inward: `model` remains independent; application ports and use cases depend only on `model` and application code; infrastructure implements application ports and owns inbound HTTP; config supplies composition inputs; `processor/main.py` wires dependencies.
- Keep framework, HTTP, filesystem, storage, and other technology details at edges. Domain concepts and image-processing behavior must not depend on them.
- Keep current FastAPI processor and React/Bun frontend shape until requirements justify a change.
- Image detection, cropping, straightening, transforms, project-local `project.yaml` metadata, and related processing belong in this repository as requirements add them. Audio, CLI, jobs, database-backed persistence, and general persistence do not.

### Application and model

- Use application code for use cases, orchestration, permissions, and transaction coordination where needed.
- Put repository, gateway, publisher, transaction-boundary, and similar outbound contracts needed by application logic in the application layer as ports.
- Use model code for image/document entities, value objects, and domain rules. Keep it technology agnostic.
- Prefer model placement when logic expresses domain meaning; prefer application placement when it coordinates a use case.
- Do not put route handlers, request parsing, framework setup, or runtime wiring in application or model code.

### Infrastructure and config

- Put FastAPI routes and inbound HTTP translation in infrastructure; keep filesystem integration in `processor/infrastructure/file_store/` and image-library integration in infrastructure capability packages.
- Infrastructure implements application ports and translates technology details at explicit boundaries.
- Keep environment reading, parsing, and validation in configuration code rather than hiding it inside use cases or model logic.
- Let config supply system inputs to composition and infrastructure.
- Keep dependency wiring in `processor/main.py`.
- Group infrastructure by adapter role or capability, such as `file_store/`, `image_processor/`, or `http_api/`, rather than generic technology buckets.

### Placement and dependencies

- If code defines what system does, place it in model or application. Put application-port implementations, filesystem, network, external services, and framework-facing inbound code in infrastructure.
- Prefer small, explicit translations at boundaries over leaking external shapes inward.
- Do not add ports, interfaces, factories, repositories, or dependency-injection mechanisms beyond required layers without a meaningful seam.
- When injectable collaborators are needed, prefer an explicit final `dependencies` argument or small `Dependencies` type. Use dependency injection for testable seams, not abstraction for its own sake.
- Treat configuration objects as dependencies when they are infrastructure inputs rather than function's main subject.
- Merge defaults near function start when it keeps body simpler.
- Organize application code by feature; keep required layers meaningful rather than placeholder-only.

### Tests, linting, and formatting

- Prefer existing standard test runner and mocking facilities before adding tooling. Name Python tests `*_test.py`.
- Test security-sensitive path handling and non-trivial image-processing behavior. Each test verifies one behavior.
- Keep tests near covered modules when practical; use small shared setup helpers and override only needed collaborators.
- Prefer readability over strict type precision in tests when language and test framework permit tradeoff.
- Prefer project format, lint, and check scripts before ad hoc commands or wrappers. Run relevant formatting, tests, and checks after changes.
- Prefer automatic fixers over manual formatting or lint cleanup. Apply manual fixes only when automatic tools fail and no better option exists.
- After changes, run relevant fixer or formatter, then relevant tests, then resolve remaining issues.
