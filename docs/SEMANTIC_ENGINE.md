# Semantic strategy engine

`macro_app.semantic_engine.SemanticStrategyEngine` executes validated TDS actions without treating an entire match as one blind desktop recording.

## Responsibilities

The generic engine owns:

- action ordering;
- Roblox foreground and client-area checks;
- camera preparation;
- bounded retries, backoff, timeout, and placement candidate selection;
- wave waits;
- automatic ability worker lifecycle;
- pause, resume, stop, and cleanup;
- visible status messages.

The game-specific adapter owns:

- clicking and confirming a tower placement;
- opening and confirming a tower panel;
- buying upgrades and reading the resulting level;
- reading the current wave;
- checking named visual detectors;
- managing auto-skip;
- detecting the requested match result;
- releasing any adapter-specific resources.

This split prevents the orchestration engine from silently assuming that a click worked.

## Action result

Every adapter attempt returns:

```python
ActionResult(
    success=True,
    reason="Tower panel confirmed",
    retryable=True,
    details={"level": 2},
)
```

A failed critical action advances only when it is explicitly marked successful. A non-retryable failure immediately stops the strategy.

## Retry behavior

Placement retries use deterministic client-relative candidate points:

1. requested point;
2. right;
3. left;
4. down;
5. up;
6. diagonal points;
7. larger rings when additional attempts are configured.

The same strategy therefore tries the same sequence on every run. Candidate points are clamped to the Roblox client area. Delay backoff and total timeout remain bounded.

## Automatic abilities

`enable_ability` creates a managed worker. When `ready_detector` is empty, the key is pressed on its configured interval. When a detector is supplied, the adapter must confirm readiness before the key is pressed.

`disable_ability` stops and joins that worker. Stopping the engine terminates every ability worker and performs defensive key releases.

## Execution modes

`start()` creates a daemon worker for a visible UI. `run_blocking()` runs synchronously for tests and command-line tools.

The engine itself is not exposed as the default user runner yet. A verified TDS visual adapter and visible preflight UI are required before semantic strategies can be executed from the installer.
