# Swarm routing

## Coordinator
The coordinator uses the larger model only to plan, decompose, spawn, integrate results, and review.
For every activity outside those duties, it MUST spawn a worker first, regardless of task size, urgency, or apparent simplicity. This includes exploration, research, edits, commands, tests, and evidence gathering for review.
Before spawning, provide an execution brief: intended steps, expected deliverable, relevant files or sources, scope boundaries, and required validation. Workers execute that brief and do not spawn subworkers.
Use light-mode task graphs or direct bounded worker spawns by default for execution and evidence gathering. Do not use deep-mode critique or verify gates, or delegate review, because final review and acceptance belong only to the coordinator. Deep mode is permitted only when the user explicitly requests it or the task clearly needs multi-stage worker critique that does not replace coordinator final review.

## Bounded workers
Use the default smaller worker model and minimal effort unless the coordinator explicitly needs more.
Give each worker one narrow outcome and a clear stop condition. For routine work, require the smallest sufficient inspection and validation.
If a worker makes no concrete progress, produces no usable report, or exceeds its assigned scope, stop it and replace it with a fresh bounded worker. Do not retry a runaway worker indefinitely.

## Completion loop / delivery discipline
After every worker reaches ready, completed, or failed, immediately process the result and choose acceptance, corrective delegation, or replacement. At spawn, create a corresponding coordinator todo for every worker; keep it in progress until the report is received and processed, not merely until the worker exits, and record its disposition as accepted, followed by corrective worker, replaced, or failed.
Workers execute their assigned implementation and prescribed checks, then report evidence only. The coordinator alone reviews results, decides blocker disposition, accepts or rejects work, and delivers the final answer. Do not assign workers independent final review, final acceptance gates, self-review of overall work, or broad “double-check weak points” review tasks.
The coordinator must process worker reports immediately and continue the completion loop without waiting for the user. Do not wait for another user message while requirements or acceptance criteria remain unmet. A worker report or status is evidence, never final delivery by itself.
Maintain a concise, explicit acceptance checklist throughout execution. Send the final user update only after requirements are satisfied, relevant validation evidence exists, and any expected commit or status is confirmed.

## Communication and safety
DMs and broadcasts are allowed for active coordination. The worker's final assistant response is the normal completion handoff to the coordinator, so do not send a duplicate final-report DM.
Workers modify only assigned files, preserve unrelated changes, and report validation plus blockers.
