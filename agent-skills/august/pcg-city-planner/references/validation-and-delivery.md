# Validation and delivery

## Work in the requested environment

Identify the exact project, engine, module names, working level and running editor process before building or testing. One machine may have several unrelated Unreal editors. Replacing a loaded native module may require saving and closing only the target editor; prepare changes first and explain that concrete reason if closure is needed. Do not kill an artist's editor or switch projects without authorization.

Use source inspection to verify APIs in custom engine builds. If browsing is needed, use the relevant official engine documentation for that version. Python/editor bridges are useful for inspecting graph defaults, asset bounds, PCG output counts, settings and actor identity. Discover actual available capabilities rather than inventing console commands or assuming filesystem asset bytes can be edited safely.

Modify named files/levels in place. Use existing test infrastructure and an authorized scratch level; do not create new showcase maps, backups, packages or duplicate guides by default. Add a small automated test/helper only where it proves a meaningful invariant or is required to repeat a nontrivial check.

## Minimum checks by layer

| Layer | Meaningful evidence |
|---|---|
| Kit | Supported pieces fit their role; pivots/units/materials and collision verified |
| Building | Tall/short roofs, corners, openings, closed ceilings, curved interiors, full foundations |
| Recipes | Each works standalone and within a compound; shared gates and access remain clear |
| Terrain | Flat terrain, collision plane, rolling grade, steep rejection and unavailable ground |
| Roads | T/X junctions, collinear joins, curves, loops, continuous road/stair collision, grade separation |
| Locality | Single interior/farm edit leaves unrelated transforms, seeds, components and output unchanged |
| Artist edits | Pinned positions and nested overrides survive road edits, refit and regeneration |
| Persistence | Save/reopen, reconstruction, duplication, road point IDs and undo/redo behave correctly |
| Failure | Missing graph/kit/material/mesh and failed child generation retain prior valid output |
| Editor | Selection both ways, same-side orientation, focus, draft/apply/discard, close prompts, layers/search |
| Scale | Neighboring/rotated planners, district chunks, realistic scene timing, instance counts and memory |

Choose representative configurations from the current game's requirements rather than imposing a historical 750 m map, home count, retaining limit or budget. A building number target is only satisfied by successfully generated usable buildings, not planned parcels. A connected entrance counts only after support and clearance checks pass.

## Regression checks that catch expensive mistakes

Record fingerprints before and after local edits: persistent IDs, authored settings, actor transforms, component/instance counts, generated mesh references and generation counters. Assert locality directly. Matching the final appearance is insufficient when every unrelated actor was secretly rebuilt.

Test both the panel and ordinary Details/viewport paths. Test rapid edits while work is pending, stale completion callbacks, and undo during/after generation. Confirm one shared queue handles them without duplicate actors or accidental full regeneration. Repeated no-op regeneration should preserve identity and not accumulate water actors, road chunks or child components.

Use an asymmetric scene for map tests. Verify the selected farm lies on the same side of its road in map and Top viewport, including a rotated planner at a nonzero origin. Test drawing and inverse picking separately from round-trip consistency.

Change a farm from rectangular to circular and back inside a compound; inspect the center, footprint, crops, water, reservations and siblings. Stretch an ivy volume vertically across several stories and measure occupied surface coverage separately from leaf density. Test a tall roof and a house on uneven ground from low angles, not only in an overhead screenshot.

For missing ground or assets, observe that old valid output remains and the item reports pending/failure. Restore the dependency and ensure retry actually runs; a prematurely advanced signature can hide the need to regenerate.

## Performance measurement

Measure local interior edit, crop/water edit, footprint change, road section edit, and explicit full update separately on the actual example scene. Count rebuilt versus unchanged items, road/dressing chunks reused, architecture/crop/dressing instances, and total wall time through dependent completion and required validation.

Report first-edit migration/warmup separately from steady-state edits. Keep full-update metrics attached to their batch so a quick follow-up does not replace them. Do not promise a hardware-independent duration or reuse timings from another game.

At large scales, inspect both generation cost and editor idle cost. An apparently fast Apply is not enough if map repaint serializes the entire scene every frame, actor polling is unbounded, or all foliage is one indivisible component. Use cached geometry, spatial queries and independently replaceable owned output.

## Shipping and artist handoff

Build the necessary native modules, compile affected Blueprint/graph assets through supported editor tools, and inspect logs for actual errors. Validate a clean reopen with the intended modules/assets, not only a hot-patched session. Runtime generation, if requested, also needs packaged-build testing; editor success does not establish cook/runtime support.

If distributing outside source control, inventory logic/data dependencies, module/engine compatibility, required plugins, cooked versus editor assets, and art already supplied by the recipient. Include only the files needed for the requested distribution. Do not promise an asset-only ZIP will work when its Blueprint parents or PCG settings live in C++. Native plugins/modules need a compatible build or a supported source rebuild path.

Keep the artist guide short and in the requested destination. Explain initial placement, selection, nested children, Apply/Discard, road edits versus refit, pin versus override, warnings and saving. State the map orientation and use actual UI names. When bilingual documentation is requested, pair each instruction with its translation and preserve the exact control labels.

Report what changed, how it was tested, measured performance, and concrete remaining limitations. Do not describe pending-ground handling, navigation clearance or all edge cases as proven merely because the module compiles. A useful final handoff distinguishes native build success, scripted regressions, visual inspection, and remaining artist checks.
