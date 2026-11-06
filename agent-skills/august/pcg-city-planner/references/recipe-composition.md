# Recipe composition

## A recipe is a contract, not only a graph

Each independently useful recipe exposes typed settings and a common planning/generation interface. Implement with project-appropriate structs/interfaces; this is a conceptual contract, not a required literal schema.

| Record | Minimum useful information |
|---|---|
| Identity | Persistent recipe/item ID, parent ID, recipe type and schema version |
| Inputs | Local/world frame, boundary, settings, kit/profile references, deterministic seed |
| Context | Ground sampler, spatial reservation query, traversal profile, instance budget |
| Plan | Proposed placements, footprint/height range, entrances/ports, support needs, dependencies |
| Output | Owned actors/components/instances, bounds, sockets and emitted reservations |
| Result | Success/pending/rejected/failed/review, reason and location, actual counts and time |

Useful operations are Describe/Measure, Preflight, Plan, Generate, Validate and CleanupOwnedOutput. The implementation may merge some phases, but preserve their different effects. Measure and Preflight should not destroy or spawn the finished scene. A compound recipe can expose one PCG graph to the artist while composing several independently addressable child recipes internally.

In PCG, standardize point/attribute meaning at subgraph boundaries: item identity, role, transform space, seed, bounds, variant/profile, and support elevation. Avoid loose string attributes interpreted differently by neighboring graphs. Keep final surface projection and validation ordered consistently: validating against raw Landscape before applying an authored terrace height can incorrectly reject a valid statue or prop.

## Implement a small graph recipe

Start with one actor exposing a boundary/volume/spline, a typed settings struct, a kit reference and a PCG component. Keep its graph asset reusable; per-actor settings should come through supported parameters or a native settings/element adapter rather than duplicated graph assets for every variation. Verify parameter binding and default graph assignment on both the class default and placed instance.

A useful internal flow is input region/context -> deterministic candidates or planned transforms -> final support projection -> shape/slope/clearance filtering -> role/variant attributes -> mesh or child-recipe output -> completion report. For modular architecture, the layout solver supplies exact piece transforms; generic surface scatter is appropriate for vegetation, not wall-bay topology. Use subgraphs for repeated functions such as border openings, terrain-fit stones and supported prop clusters.

Keep structural, crop, water and optional-detail branches separately addressable where they have different update dependencies. Group spawn data by compatible mesh/material/collision settings and attach provenance to output batches. Do not rely on a graph-wide cleanup followed by regeneration when only one branch is changing and prior output must survive failures; route replacement through the owner/service or stage new branch output.

For a missing piece, inspect counts at the candidate, projected, filtered and spawned stages. Show rejection reasons or debug points for the relevant stage. This distinguishes bad defaults, unavailable ground, footprint rejection, a missing mesh, and a generation task that never completed. Validate the recipe alone before attaching it to a compound or district.

When adapting an existing generator, first identify its input settings, completion signal, cleanup ownership and automatic update hooks. Add a thin adapter that describes its footprint/reservations and routes managed edits to the shared queue. Preserve standalone behavior. Avoid rewriting functioning content merely to give every recipe an identical internal graph.

## Start with useful small parts

Select parts required by the current game; expand this catalog as needed.

| Recipe | Consumes | Emits / coordination rule |
|---|---|---|
| Building | Profile, support area, entry constraints | Shell, rooms, footprint, roof clearance, doors/windows, entry anchors |
| Entrance path | Road connection, building threshold, traversal profile | Supported path, stairs/landing, continuous access reservation |
| Boundary | Parcel perimeter and shared openings | Fence/wall/hedge segments; omit gates and accesses from a common opening plan |
| Agriculture/garden | Planting region, crop/bed profile, support datum | Soil/rows/rings/crops, gates; obey routes and property limits |
| Terrace/support | Grade, floor/soil datum, retaining policy | Closed supports, retaining faces, walkable tops and clearance edges |
| Water | Flood region, elevation mode, material and terrain suitability | Owned surface/body; expose unsupported depths or missing water-system requirements |
| Market/commercial cluster | Reserved parcel, aisle graph, loading/customer entries | Stalls and shops with clear circulation; optional perimeter buildings can be disabled |
| Yard/activity cluster | Building function, usable yard, access and window exclusions | Coherent storage, seating, work areas or household props |
| Vegetation | Suitable ground/surfaces, palette, mature size/height | Trees, shrubs, ivy or minor scatter outside protected spaces |
| Lighting/utilities | Routes/anchors, clearance, theme | Posts, fixtures and suspended connections that respect movement/headroom |
| Interior cluster | Room polygon, function, openings, support surfaces | Furniture and attached props with usable circulation |

Place clusters with a purpose, not uniform noise. A workshop needs a service route and work apron; a residence can have a small kitchen garden and storage; a commercial square needs visible entries and uninterrupted aisles. Reuse the same primitives for a medieval village, contemporary suburb, industrial campus, or science-fiction colony through different kits and profiles.

## Spatial reservations make composition deliberate

Represent reservation owner, stable ID, semantic kind, shape/frame, vertical interval, clearance margin, and optional connection/port identity. Useful kinds include building, roof, road, junction, entrance, stair/landing, door, window, garden gate, protected scenery, and utility/service access. Expand kinds only where consumers need different behavior.

Define a consumer compatibility table. Examples:

- Crops and fence segments cannot occupy entrance or gate space.
- Trees respect trunk and canopy clearance, not only point location.
- Wall ivy and art exclude door/window surface rectangles and access headroom.
- Roof and utility reservations may overlap ground paths only with sufficient vertical clearance.
- A building may intersect its own foundation; owner-aware filters prevent rejecting intended overlaps.
- All bordering recipes consume the same gate/entrance IDs; two independent border generators must not close each other's openings.

Use a spatial index to query only nearby reservations. Hash only reservations relevant to a recipe's influence region and compatibility mask. Including every city reservation in every farm's signature turns a tiny edit into a city-wide rebuild.

Where conflicts appear, resolve by declared priority or report them: protected authored scenery and required circulation generally constrain optional dressing. Do not delete authored rocks/trees or move pinned buildings to satisfy a scatter recipe. Avoid cycles by freezing planned interfaces for a pass, generating in dependency order, then doing bounded validation/correction.

## Compound properties

A home-plus-farm property is one selectable parent with a house, one or more farm plots, access, terraces, borders and yard children. Its property boundary reserves enough room for all of them. Similar compounds include shop/workshop, apartment/courtyard, station/service yard and civic/plaza.

Compute child placement from a shared local frame and common entrance plan. Align terraced farming to terrain contours where suitable, divide support into manageable levels, and keep routes between levels. Use actual farm bounds and garden radius when changing rectangular to circular layouts; actor pivot and boundary center may not coincide. Reset or translate only the layout data owned by that mode, preserving unrelated child settings.

One child edit must retain siblings and parent position. Child IDs and settings overrides persist independently. When a new layout cannot fit the property, retain edited content and mark the conflict; offer a separately scoped parent refit. Parent regeneration must not blindly reassign default settings over child overrides.

## Surface vegetation and water pitfalls

Ivy volume coverage depends on candidate distribution over usable height and width, surface search reach, segment length, pruning and instance caps. Diagnose spatial coverage separately from density. Seed candidates across the full requested surface/volume, use local surface normals, handle disconnected valid surfaces, and report skipped regions. Multiplying density cannot fix candidates confined to a narrow band at the base of a multistory wall.

For water, decide whether the project needs a Water plugin body, a generated surface, or another supported solution. Inspect actual plugin/material/zone/collision requirements for the engine. Supply a valid project default material when expected and report missing dependencies. Water level remains horizontal unless the chosen system supports another physical model. Terraces may need separate water regions and elevations; do not flood an entire sloped compound from one average ground height. Keep sculpting and crop replacement explicit choices.

Batch repeated meshes with compatible mesh/material/collision settings. Keep ownership sufficient to replace local batches. Separate architecture, crop and optional dressing counts; reduce minor scatter before deleting essential access or structure when budgets are exceeded.
