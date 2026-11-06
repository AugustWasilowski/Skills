# Roof partition and reassembly

## Choose the intended kind of modularity

**Exact source cuts** reproduce an existing roof. They are suitable for handoff when the artist must retain a particular silhouette, pitch, curvature, eave lift, or tier transition. They are usually compatible within the recorded source profile, not automatically across differently sized buildings.

**Reusable construction modules** support building new combinations. Define compatible field, eave, hip/outer corner, inner corner/valley, ridge, ridge end, gable edge, and transition families as needed. Establish shared edge profiles and allowable slope/run/rise combinations first. Reconstruct representative roofs from those modules to prove reuse.

Cutting a monolithic curved roof into 400 cm squares establishes spatial addresses, not universal interchangeability. When the user needs many interchangeable building sizes, normalize the supported roof profiles or design reusable bands/transitions. Do not silently stretch source cuts into a new shape. Generic roof studies must be labeled as studies unless they actually assemble into the resolved roof.

## Cut from the same source surface

1. Resolve the complete roof in its documented local frame. Decide whether the cut applies to the complete graybox roof, tile skin, structural layer, ridge, or another explicitly named subsystem.
2. Freeze triangulation consistently before intersection. Preserve the original polygon/corner attribute mapping through triangulation, especially on nonplanar quads.
3. Choose grid planes relative to a documented origin. For exact plan-grid cuts, clip source triangles against X/Y cell planes. Compute a shared-edge intersection in a consistent endpoint order, so neighboring owners do not round the same vertex differently.
4. Carry source-face identity and interpolation weights into the fragments. Interpolate original UVs and normals at new vertices; normalize interpolated normals. Independently projecting each chunk or recomputing normals only from its isolated neighbors can create texture or lighting seams.
5. Assign geometry lying exactly on a cut plane to one owner. Remove degenerate fragments consistently and preserve holes in pent roofs or courtyards. Define handling for small terminal slivers rather than silently dropping valid geometry.
6. Place each piece around its chosen snap pivot. One useful convention is the XY cell corner with Z rounded down to a vertical grid step. Restore the original surface elevation through the recorded placement; do not quantize the roof vertices to that Z step.

A grid governs interfaces and placement, not necessarily the entire bounding box. Terminal cells can be partial; eaves or tiles can extend beyond a nominal plane if the declared ownership/overlap contract allows it. Record that exception so artists and PCG consumers do not use AABBs as snap spacing.

## Decide what happens at the cut

For an artist surface reference, open internal interfaces can be intentional. Label them explicitly. For a required closed solid, generate correctly wound caps for each valid boundary loop and account for holes and disconnected components; do not bridge an entire roof cross-section with a guessed polygon. A cap policy is a deliverable decision, not a universal default.

Keep silhouette ornaments, bells, and other separately attached decoration out of arbitrary cuts where practical. Give them named attachment anchors. For tiled production roofs, whole tiles can be assigned to cells by a bearing anchor with documented overlap instead of being sliced repeatedly. Keep tile dimensions constant; solve fitting through overlap, terminal pieces, or controlled cuts.

Different layers may need different partition rules. A tile-patch kit is not a complete roof replacement if its rafters, ridges, or structural envelope remain monolithic. State the replaced and retained layers precisely.

## Record a reconstruction contract

Use the existing manifest schema where available. Useful fields include:

| Record | Required meaning |
|---|---|
| Piece identity and export name | Stable lookup versus human-readable mesh filename |
| Source/profile identity | Which resolved surface and compatible seam family this piece belongs to |
| Cell address, nominal span, grid sizes | Its place in the local construction lattice |
| Pivot and axis convention | How the exported local mesh must be placed |
| Connection contours and normals | Actual mating geometry, beyond a bounding-box midpoint |
| Roof-local instances | Piece transforms reconstructing one source roof |
| Roof placement | Transform from the roof frame into the building frame |
| Composed building instances | Optional direct placements for a procedural consumer |
| Replacement target and retained layers | Prevents double-spawning the original roof and its cuts |
| Cut/overlap policy | Open interfaces, capped solids, tile overlap, or exterior overhang |

Compose transforms in a single declared convention and apply unit conversion exactly once. Preserve local pivots in exported meshes; explode or shelf the preview using display transforms only. Match connection contours after placement, not by comparing raw local vertex coordinates from differently elevated pivots.

## Verify geometry and practical reuse

For exact cuts, compare reconstructed bounds and surface coverage to the same triangulated source. Check area conservation as supporting evidence, but also inspect boundary contours and holes: equal area alone cannot prove that nothing is missing or duplicated. Verify new vertices lie on their source surfaces and adjacent interfaces agree within the project's tolerance.

For reusable modules, build more than the source example: change a span or supported roof form and prove that field, corner, ridge, and termination connections still match without scaling. Do not claim this result from exact-cut tests.

Render the assembled roof with per-piece colors and an exploded counterpart. Check outward normals, the underside, eave closure, ridge continuity, and small terminal fragments. Reimport a representative assembled FBX and check that pieces remain separate objects with the intended transforms and units.

Keep extraction and export practical for family kits. Cache source triangulation and attributes, and process pieces by source/profile so a bounded cache does not rebuild a large roof for every hash-sorted cell. Deduplicate only when geometry, materials, UV policy, pivot, and connection contracts are truly equivalent.
