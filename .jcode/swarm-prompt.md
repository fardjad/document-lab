# Swarm routing

## Coordinator
The coordinator uses the larger model only to plan, decompose, spawn, integrate results, and review.
For every activity outside those duties, it MUST spawn a worker first, regardless of task size, urgency, or apparent simplicity. This includes exploration, research, edits, commands, tests, and evidence gathering for review.
Before spawning, provide an execution brief: intended steps, expected deliverable, relevant files or sources, scope boundaries, and required validation. Workers execute that brief and do not spawn subworkers.

## Bounded workers
Use the default smaller worker model and minimal effort unless the coordinator explicitly needs more.
Give each worker one narrow outcome and a clear stop condition. For routine work, require the smallest sufficient inspection and validation.
If a worker makes no concrete progress, produces no usable report, or exceeds its assigned scope, stop it and replace it with a fresh bounded worker. Do not retry a runaway worker indefinitely.

## Communication and safety
DMs and broadcasts are allowed for active coordination. The worker's final assistant response is the normal completion handoff to the coordinator, so do not send a duplicate final-report DM.
Workers modify only assigned files, preserve unrelated changes, and report validation plus blockers.
