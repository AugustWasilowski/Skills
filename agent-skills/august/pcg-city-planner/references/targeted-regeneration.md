# Targeted regeneration and artist ownership

## Persist intent; derive output

Separate four kinds of state:

1. Authored inputs: boundaries, road curves, settings, kit references, selected ground and protected scenery.
2. Stable identity/ownership: planner, parcel, recipe, road, control-point and connection IDs; parent/child links and generated baseline settings.
3. Artist intent: independent settings overrides, positional pins, manual positions, skipped/deleted generated items and explicit refit decisions.
4. Derived output: instances, generated components, geometry caches, reservations and last successful signatures.

Store identity and authored intent durably. Derived state may be serialized to preserve the saved scene, but should be reproducible without overwriting intent. Record a generated baseline so Return to Generated Settings has a concrete meaning. Distinguish overrides from merely possessing non-default values. Capture user edits, not changes made internally by generation.

Duplicating an independent planner/property needs a new identity namespace and properly remapped children. Loading and undo restore existing IDs. Avoid ID collisions across neighboring planners, duplicated worlds and cook/editor contexts.

## Placement lifecycle

Give newly placed actors valid default kit, graph and design settings. Queue initial generation after components and world placement are ready, then after the placement drag finishes. Guard class defaults, archetypes, transient preview actors, undo/reconstruction and loading. In Unreal, inspect the appropriate creation, post-load, construction, completed PostEditMove and noninteractive property-change hooks for the actor type; none should independently trigger a broad rebuild.

Persist initialization/version state so reopening a saved level does not apply the latest default preset over authored settings. A one-time preset action for older actors should be explicit. Ordinary property edits and completed moves enqueue classified work with a short debounce, including edits made while the map tab is closed. A queue tied only to widget Tick stops servicing artists who use the viewport.

## Shared classification and preview

Both the map panel and normal viewport/Details edits must call the same change classifier. Maintain per-item snapshots of semantic settings, transform, actual footprint/height, entrance connections, spline position/tangents/types/loop state, and relevant dependencies.

| Change | Expected update scope |
|---|---|
| Interior style or cosmetic variant with unchanged occupancy | Selected building and attached details |
| Crop palette/density or flooding | Selected farm and its crop/water outputs |
| Building family, size, position, tiers, wings or entrance | Selected building, supports/access/yard and intersecting dependencies |
| Nested property's farm layout | That farm; terrace/support dependencies if their shape/datum changes |
| Road shape or width | Affected sections, connected junctions, entrances and overlapping dressing; buildings stay put |
| Local obstacle or ground change | Items whose support/influence region intersects the changed region |
| Global seed, layout preset, boundary or shared kit | Explicit broader update with scope explained before commit |

Property names help classify changes but are not sufficient. Compare old and proposed descriptors to catch a cosmetic-looking variant with a larger awning, a different doorway, or a moved support. Use the union of old and new influence bounds plus semantic dependency edges to find affected items. Include both old and new connection neighborhoods for road topology edits. A preview must report items and reasons, not simply say "local" while scheduling the entire city.

If a change type is unsupported, say which scope is required and offer the appropriate action. Do not hide an unconditional full regeneration inside a local request.

## One queue and an explicit completion boundary

Recommended conceptual flow:

```text
on completed edit:
    snapshot the new authored revision
    classify against the last successful snapshot
    merge item requests into a debounced queue

execute batch:
    resolve IDs and ownership; compute dependencies and affected regions
    preflight assets, ground and proposed topology before cleanup
    generate replacement outputs in dependency order
    wait for native/PCG/deferred child work, not only the initiating call
    ignore or cancel stale work when a newer revision supersedes it
    validate required support and clearance
    commit successful replacements and their snapshots
    retain prior valid output/snapshot for failed items; record reasons
    publish per-item results and rebuilt/unchanged counts
```

Use bounded coalescing: many mouse move events become one completed edit, while a later edit supersedes pending earlier work for that item. Suppress recursive notifications while applying owned child updates. A boolean reentrancy guard alone is not enough for asynchronous generation; carry batch/item revision IDs through callbacks and completions.

Audit the engine's independent PCG editor tracking. If the planner owns update scheduling, unmanaged automatic regeneration can still clear output on a property change before preflight runs. Configure tracking for managed components only, using verified APIs for that engine. Replace disabled implicit dependencies with explicit ground/asset notifications; never globally disable PCG tracking for unrelated content.

Before destructive replacement, retain the last successful bounds, reservations, output and settings signature. Prefer temporary/staged output followed by a swap; where a recipe cannot stage, use a recoverable replacement strategy and state its limitation. Cleanup may remove only obsolete output owned by that item after success. Empty valid output and unavailable ground are different outcomes. Do not advance a failed item's signature to the proposed revision, or retries can incorrectly conclude that it is current.

## Incremental roads and dressing

Partition road surfaces into independently replaceable sections and junctions. Choose stable section identities based on persistent control intervals or stable spatial cells; total-road normalized sampling can shift every sample after one insertion. Include an overlap margin for joins and replace connected junctions consistently. Preserve material, collision and navigation continuity.

Partition district planting into stable spatial chunks, with deterministic candidate sampling tied to chunk and recipe IDs. Each chunk hashes only intersecting relevant reservations. Adding an obstacle removes/repositions affected scatter without regenerating distant chunks. Allocate a deterministic budget policy so one local change does not arbitrarily redistribute the entire city's instance cap. Essential architecture/access and crops have separately reported budgets from optional dressing.

For older scenes, adopt existing outputs and identities without changing layout on open. Initialize missing dependency records from the saved scene. If the first spatial edit requires chunk conversion, preview that one-time preparation separately from ongoing regeneration and preserve settings/output where possible. Do not infer missing ownership by deleting every actor with a similar label.

## Pins, overrides, and refit

Settings overrides protect selected properties; positional pins protect placement. A nested farm density edit should not pin its homestead or trigger sibling regeneration. Recompute reservations from the actual locations of manually moved buildings. Mark incompatible content Needs Review while retaining it.

Road editing updates access to current buildings. Refit Affected Plots is separate and enumerates eligible plots, respecting pinned/manual content and settings overrides. Define the explicit behavior of an artist deleting a managed child: a persistent skipped item, a detached actor, or a user-requested regeneration. Do not immediately recreate intentionally deleted work without a clear policy.

## Transactions and reload

Use transactions for authored inputs and identity/override changes. Undo/redo restores these inputs, then queues the affected derived updates. Avoid restoring stale generated-component pointers from a broad transaction snapshot. Reconcile actor lifecycle, references and owned output when undo creates/deletes roads or child actors. A panel draft is transient and separate from a scene transaction until Apply.

Invalidate cached snapshots appropriately after undo; do not treat a generic undo notification as a global change. Preserve spline point rotations, tangents, interpolation types, scale, elevation and closed state. Validate save/reopen and blueprint reconstruction as well as one uninterrupted session.

## Status is part of correctness

Track batch identity, item state, pending dependencies, elapsed wall time and rebuilt/unchanged counts. Do not mark generation complete when only the request was dispatched. Keep the status of a full operation distinct from a later local follow-up so its reported duration is not overwritten. Expose failures per item with an inspectable location and recovery action.
