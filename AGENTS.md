# Project journal

Read `JOURNAL.md` before planning or changing this project. It holds current product direction, constraints, prior decisions, and learned solutions.

After each user request is completed, update `JOURNAL.md`:

- Add dated entry under `## Journal entries` summarizing request, decision, and outcome.
- Update `## Current direction` when request changes active requirements.
- Record solved blockers, root causes, and durable fixes under `## Lessons learned` when work required investigation or troubleshooting.

Keep entries concise and factual. Do not record secrets, credentials, or transient command output. Preserve prior entries; correct them only when known inaccurate.

## Git commits

Commit only when user asks. Keep commits atomic: one coherent category of change per commit. Use concise imperative commit subjects that state outcome, with a body only when context is needed. Do not use Conventional Commits prefixes such as `feat:`, `fix:`, or `chore:`.
