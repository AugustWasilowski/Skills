# Building construction

## Asset kit before procedural rules

Inspect representative authored buildings and their component transforms before inventing assembly offsets. Record each kit member's semantic role, authored dimensions, pivot, forward/up axes, material variants, collision, and usable attachment sockets. Distinguish physical occupancy from render bounds inflated by decorations or effects.

Useful roles include foundation, floor, wall bay, corner, opening bay, beam/post, straight roof field, eave, roof transition, ridge, cap, stair, railing, ceiling, and interior partition. Not every kit contains each role. Use validated fallbacks or report a missing role; do not substitute visually similar but geometrically incompatible pieces silently.

Put these records in Data Assets/Data Tables or the project's established equivalent. Profile data selects assemblies and constraints; algorithms should not embed mesh paths. Soft references need explicit preflight/loading and cook inclusion where runtime use is required. A kit audit should identify open-sided foundation meshes, missing collision, inconsistent pivots, and pieces that cannot be stretched safely.

## Produce a layout descriptor before spawning

A deterministic building evaluator should produce:

- Footprint polygons with local frame, occupied height range, roof overhang, and optional porches/wings.
- Floor levels, enclosed room regions, ceiling heights, stair voids and landings.
- Facade spans and openings: door/window geometry, sill/head heights, exterior clearance and interior approach space.
- Entrance anchors with position, orientation, threshold height, and required access width.
- Support footprint and load-bearing floor base; distinguish this from a decorative platform's height.
- Placement records for modular pieces and furnishing regions.

Use this same descriptor for lot fitting, spawning, map outlines, collision checks, and dependency previews. Measure generated or artist-edited actors when their actual geometry differs; do not retain a stale nominal rectangle. Consider multiple polygons for compounds and courtyards rather than treating their empty centers as solid buildings.

## Shell assembly

Derive wall bays and framing from a shared facade grid. Posts, rails, openings and interior walls consume this grid instead of independently choosing random positions. Reserve door and window intervals first; split framing spans around them. Frames may intentionally border openings, but unrelated beams must not cross glass or door clearance.

Solve roof courses by role and remaining run/rise. Repeat straight field pieces through the middle; place curved eave/terminal pieces only at their designated boundaries. Tall roofs must not repeat a complete short-roof motif whose curved ends create bumps in the middle. Fit left/right trims and ridge/corner caps to the resulting roof, with consistent handedness and winding. Test the tallest supported profile as well as the default.

For enclosed interiors, choose a supported construction mode:

- Flat ceiling at partition height with matching edge treatment and valid headroom, or
- Partitions extended/clipped to the roof underside, with matching gables/infill.

Do not accidentally create lofts by stopping partitions below a sloped roof when enclosed rooms are requested. Reserve stair openings and maintain a real connection between floors. Test inside/outside visibility, collision, and two-sidedness; a two-sided material alone does not close an open foundation mesh or create collision.

## Interior placement is shape-aware

Rectangular rooms: place wall-bound items against valid solid wall intervals, and place activity clusters in the remaining room polygon. Account for object depth, chair pull-out, door swing if gameplay uses it, and travel lanes. Scatter props on explicit support surfaces such as tables/shelves; do not infer a table height from arbitrary mesh origin.

Curved rooms: use the actual floor polygon and wall curve. Generate wall-adjacent candidates along arc length with inward normals and tangent-aligned furniture. Test the full transformed furniture footprint, not just its center. A tangential rectangular cabinet needs enough inward offset for its corners to clear curvature. Check ceiling clearance as well as floor containment.

Rugs and central clusters: test corners and edges against the walkable floor polygon, stair holes and circulation reservations. For concave rooms, corner-only tests are insufficient. Use polygon containment/intersection. Rugs may overlap furniture intentionally but must not bridge floor voids or cross door approaches unintentionally.

Wall art: select solid wall spans, subtract door/window regions at the art's actual height, and validate the entire art rectangle. Orientation and depth must match the wall surface. A wall hit at the art center is not proof that the rest of the frame avoids an opening.

Represent decor compatibility through placement tags and support requirements: wall-mounted, tabletop, floor-standing, ceiling-hung, exterior-only. A new theme supplies different palettes and profiles rather than replacing placement logic.

## Foundations and ground blending

Keep buildings upright unless the design explicitly permits tilting. Sample the support footprint, choose a finished-floor datum, and fill the gap down to terrain with closed geometry or confirmed all-sided meshes. The foundation top must meet the actual underside of the house; a thin raised plate beneath an already elevated house leaves a visible gap.

Generate retaining edges where exposed; fit bottom vertices/course heights to ground and avoid giant decorative steps masquerading as support. Derive stair count from actual rise and gameplay limits, with usable landing depth and collision. A gameplay profile defines maximum riser, slope and clear width; previous projects' measurements are examples, not universal constants.

Blend exposed edges with a ground-fitting soil skirt, local stone courses, embedded rocks, planting beds, or a compatible material treatment. Keep entry, window, stair and protected-scenery reservations clear. Vary stone sizes and embedment within bounded rules instead of making a regular wall of scaled blocks. Material blending does not repair missing geometry.

Landscape deformation is a separate, explicit feature. If authorized, use the engine's supported reversible terrain/layer workflow and track affected regions. Otherwise blend with generated support/dressing geometry; never quietly sculpt or hide terrain to make a building fit.

## Variety that still fits

Select family/profile from usable space and gameplay role before cosmetic randomness. Vary footprint, tiers, wing presence, finish, interior use, and accents within kit-supported combinations. Keep spatial and cosmetic seeds distinct. A shop or restaurant has service/entry/circulation requirements, not merely a different sign. Re-evaluate full occupancy and entrances when family, tier count or wings change.

For retries, try compatible smaller profiles or nearby eligible positions in a bounded, deterministic order. Do not scale all geometry down indiscriminately; that changes door sizes and traversal metrics. Report the profile actually chosen and why larger profiles failed.
