# Settlement planning

## Terrain is a shared service

Use one ground-sampling contract for planner and managed recipes. Return location, normal, surface identity/type, validity and a reason when unavailable. Prefer reliable direct terrain sampling when available, allow explicitly selected mesh ground, and support ordinary collision ground for new prototypes. Exclude owned generated geometry so a regenerated roof or farm surface cannot become the next pass's ground.

Sample enough points to measure slope and relief over the occupied region, not only the center. Cache by spatial region and ground revision. In World Partition or similar streaming systems, distinguish unloaded cells from empty or too-steep sites; preserve existing output and mark pending rather than using zero elevation or erasing actors.

Buildings generally stay upright; terrain-following roads and planting may use local normals. Carry the final support plane or terrace surface through dependent recipes so crops, water, stairs and foundations agree on elevation. Do not let each recipe independently choose a different mean height.

## Build a connected road graph before lots

Keep the artist-authored spline and derived terrain-following render/collision surface separate. Sample curves by arc length or adaptive error, retaining point types, tangents, transforms and loop state. Build graph nodes for endpoints, intersections and connection ports; graph edges identify the source road and its stable interval.

Detect crossings, T connections, endpoint-to-segment joins, collinear joins, and closed-loop seams. Compare elevations and grade separation before joining XY crossings; an overpass is not an intersection. Reserve junction clearance before parcels. Trim overlapping road strips into shared junction geometry with compatible materials/UVs, continuous support, and collision. Lanterns, borders, sidewalks, and other edge recipes consume junction gaps too.

Use project profiles for main streets, lanes, paths, sidewalks, loading routes and vehicle turn radii. Do not scatter independent decorative road slabs and call them connected navigation. Verify the collision and traversable surface at seams and stair transitions.

## Automatic routing versus authored intent

For initial routes, use sampled terrain costs: grade, curvature, protected obstacles, water/unavailable ground, earthwork limits and desired connections. A grid/graph search with grade-constrained edges and bounded smoothing is a reasonable implementation; choose resolution relative to road width and terrain detail. Revalidate after smoothing so a visually gentle spline does not cross a forbidden region.

After artist edits, preserve authored spline shapes and elevations unless they explicitly request Fit to Ground or rerouting. Flag unsuitable sections. Never silently move edited control points merely to restore a default road plan. Treat bridges, tunnels and terrain sculpting as separate capabilities when the game requires them.

## Allocate usable parcels

1. Reserve protected scenery, road corridors, junctions and requested central anchors such as markets/civic spaces.
2. Evaluate available frontage and depth with terrain and boundary constraints.
3. Choose role and compatible building/compound profiles. Measure the full footprint, overhang, service space, yard and entrance.
4. Solve access to a specific road connection using the real entrance/threshold, then validate support and occupancy together.
5. Retry compatible smaller profiles or nearby eligible positions in a deterministic bounded search before rejecting a candidate.
6. Commit a persistent parcel ID and explicit road attachment record. Report generated versus planned counts separately.

Spatial indices accelerate broad-phase overlap; use oriented polygons/boxes and height ranges for final tests. Concave parcel containment requires edge/intersection tests. Keep setback, stair-run and yard requirements mathematically consistent. A narrow setback cannot simultaneously satisfy a longer required stair approach.

Do not identify plots by rounded station or array position. Persist attachment records such as parcel ID, road ID, edge/connection identity, side and access anchor. Station is an editable locator, not identity. Road insertion/deletion should reconnect affected access, not rename every subsequent plot.

Distribute functional variety intentionally: local shops near usable frontage, a market at a connected center, larger service lots where geometry permits, residential clusters with shared spaces. Profile weights guide choices but do not guarantee a fit. Keep unsupported candidates and diagnostic reasons visible rather than inventing successful counts.

## Access, terraces and support

Use the game's character capsule, vehicle envelope, step height, slope and headroom rules. Derive access from actual required rise. For stairs, choose step count with ceiling(rise / maximum riser), then fit tread run and landings. Check width and headroom continuously; a spline connecting two endpoints does not prove a traversable route.

Validate sampled support beneath roads, entrances and stairs plus swept/overlap clearance above them. Ignore the intended support surface appropriately while still detecting obstructions. Use actual collision where meaningful; do not globally ignore all generated actors or the target building. Report the obstructing object and location.

Where retaining height is too large, try a longer approach, split terrain support, or smaller eligible property before failure. Put allowable retaining height in project configuration. Keep visible review markers for unresolved sites and preserve pinned/edited content.

Terraced farms should follow useful contours and allow manageable changes in level, connected gates and access between bands. Reuse local wall stone palettes for retaining courses when they suit the kit. Avoid broad rectangular blocks that expose excessive vertical faces on mild terrain. See building construction for closed supports and edge blending.

## Cross-planner coordination

Each planner owns only its outputs, but reads neighboring planner and protected-world occupancy. Define whether their roads connect automatically, through explicit ports, or only with an artist action. Use shared stable identities and world-space reservations across rotated/scaled local frames. Never delete or regenerate the neighboring planner's content as a side effect of local cleanup.

Budget for streaming and scale. A larger boundary does not imply rebuilding or loading every district at once. Spatial chunks and explicit local dependencies let large settlements remain editable; see targeted regeneration.
