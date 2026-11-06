# Native map and settings editor

## Module boundary and implementation shape

For Unreal, place the artist panel in an editor-only module or plugin module. Keep generation/data contracts in the runtime or project module that owns them. Runtime modules must not depend on Slate editor widgets, UnrealEd, or Python. Determine whether runtime generation is needed before adding packaging obligations.

A practical source split, with project-specific names:

```text
Generation module
  Recipe descriptors and settings
  Planner, spatial index and ground service
  Change classifier, queue and per-item results
Editor module
  Module registration / menu / tab lifecycle
  Map view model and cached geometry
  Slate map widget and settings panel
  Transient edit draft and commit adapter
  Managed-road component visualizer
  Optional automation API and tests
```

Use a dockable Slate tab registered through the editor's tab manager and ToolMenus, with clear menu placement appropriate to the project. Register/unregister menu callbacks, object/selection delegates, tickers and custom visualizers symmetrically. Skip UI setup in commandlets. Check shutdown/module reload and weak references to actors that may unload or be deleted.

Typical native dependencies include Slate/SlateCore, UnrealEd, LevelEditor, ToolMenus, PropertyEditor and ComponentVisualizers; add only what the implementation uses and inspect the actual engine API. The following identifiers describe a proven Unreal integration approach, not a version-independent copy/paste API contract: FGlobalTabmanager, SDockTab, IDetailsView, FScopedTransaction, FEditorDelegates, FSplineComponentVisualizer.

Use cached descriptors as the map model. Refresh only on relevant scene/asset/selection changes and completed generation, with a lightweight timer where necessary for pending work. Do not serialize every actor or recalculate every footprint each paint/frame. Reopening the panel only observes/adopts state; it must not seed or regenerate the settlement.

## Map presentation

Draw actual oriented building footprints, compound-property outlines, farm boundaries, circular gardens, commercial areas, road corridors/junctions and entrances. Suppress individual crops and scatter instances at city scale. Distinguish an unloaded item's retained descriptor from an editable actor. Other loaded planners can appear as subdued context while one is active.

Provide pan/zoom, Fit, search and layer filtering; make hit testing use the same visible geometry/filter rules as drawing. Use line-distance picking for roads and polygon containment for parcels. Allow selection of a parent property and its house/farm children; prefer explicit hierarchy or smallest relevant visible shape rather than making the parent swallow all clicks.

Keep viewport/Outliner selection synchronized with a guard against recursive notifications. Multi-selection behavior should be explicit if supported. Double-click focuses the viewport on the chosen object's real bounds or selected road section. Pins, overrides, pending ground, generation failures and conflicts must be distinguishable, with clickable warnings and optional reservation overlays.

## Coordinate correctness: prevent a mirrored map

Choose and label the map's orientation. Do not call it north-up unless the project defines world north. A fixed Unreal Top view and a camera-follow map are different modes; implement one deliberately and explain it to artists.

In the inspected Unreal Top/OrthoXY implementation, world +X displays right and +Y displays down. Slate also uses downward-positive screen Y. Flipping Y again creates a reflection that no camera yaw can fix. Verify this in the target engine's viewport projection before reusing the convention.

For that fixed Top convention, with world XY center C, pixel center O and positive scale s:

```text
screen(P) = O + s * (P - C)
world(Q)  = C + (Q - O) / s

pan: C -= world(currentCursor) - world(previousCursor)
zoom: W = world(cursor); change s; C += W - world(cursor)
```

If a rotated/local map is requested, use one explicit basis matrix and its inverse for every operation; transforming one axis only changes handedness. Convert actor-local outlines/splines into world once. Treat vectors/tangents differently from positions, and avoid double-applying actor transforms. Test nonzero origins, rotated planners, non-square viewports and zoom levels.

Round-trip screen/world tests alone cannot detect a reflection: a wrong transform and its inverse still round-trip. Compare an asymmetric arrangement and world-axis directions against the engine's actual Top projection, then test same-side-of-road selection in the viewport. Include point/tangent dragging, pan and cursor-anchored zoom in this check.

## Draft settings and targeted Apply

Use a transient UObject/settings model with no generation callbacks. Populate it from the selected item's actual settings, including artist overrides. Bind the Details view to this draft, not directly to the live actor. Expose relevant broad controls for the selected recipe; keep unrelated engine/component settings out of the compact panel.

1. Snapshot source identity/revision and settings when selection begins.
2. Record draft edits and generate a cached affected-items preview from the shared classifier.
3. On Apply, ensure the source is still loaded and unchanged, or present a merge/reload choice. Preflight proposed settings and dependencies.
4. Commit authored values and identity changes as one undoable transaction; request the scoped update and report its progress.
5. Discard reloads the draft without touching scene output. Selection/tab-close prompts protect unapplied edits.

Avoid dummy spawned actors for property previews if their construction hooks generate or dirty the level. New-item drafts can use nonregistered transient components or pure descriptors. Do not mark edits applied or signatures successful until generation's completion boundary confirms the result.

Actions should include Regenerate Selected, Validate, pin/unpin position, return to generated settings, and explicit Refit Affected Plots. Preserve the full-generation action, but label and preview its broader effects. Staging applies to the panel; ordinary viewport/Details edits can retain the project's automatic completed-edit workflow through the same queue.

## Full road editing

Support segment selection, point/tangent dragging, insertion/deletion, drawing/deleting roads, loop toggling and connection snapping as required. Give roads and control points persistent IDs. Insert/delete updates the ID list without renaming surviving points; retain plot attachment identities.

- Existing points preserve Z during XY dragging. Fit to Ground explicitly resamples elevation into the draft.
- Inserted points interpolate the current curve rather than simply averaging endpoints on curved segments. Preserve/adjust tangent continuity according to the point type.
- New roads use sampled ground; pending terrain leaves the draft intact with a reason.
- Snapping checks both distance and elevation; do not connect grade-separated routes accidentally.
- Width and surface settings normally apply to the selected road, unless a segment-level schema is intentionally provided.
- Draw the draft in both map and viewport; rebuild generated roads only on Apply. Deletion is also staged.

Use a custom spline component subtype or another scoped visualizer mechanism to synchronize exact point/segment selection without taking over every spline tool in the editor. Initialize visualizer selection transforms, including a valid normalized quaternion or identity, before drawing a gizmo. Do not assume selection structs reset every field safely.

Inspect spline getters in the target engine. In one custom UE5.5 implementation, the aggregate spline-point getter did not honor the requested world space for all fields. Explicit position, arrive/leave tangent and rotation/scale accessors with tested local/world conversion avoided corrupting edits. Treat this as a compatibility test, not a universal engine bug.

## UI validation limits

An API can verify draft commits and road IDs but cannot prove docking, click targets, keyboard focus or mouse capture behave correctly. Perform a short hands-on pass with actual screenshots when tools permit. If the editor cannot be controlled or observed, deliver verified code/script results and explicitly leave interaction checks unverified. The finished panel itself must work without the remote bridge.
