---
name: pcg-city-planner
description: "Design, build, or debug modular Unreal Engine PCG buildings, reusable environment recipes, coordinated settlement or city planners, and their native map editors. Use for composing roads, parcels, architecture, interiors, terrain supports, and dressing with targeted regeneration and protected artist edits. Adapt to the game's kits and gameplay; not for unrelated scatter-only tasks."
---

# PCG City Planner

Build a settlement as cooperating generators with explicit ownership, spatial contracts, and edit dependencies. A city is not one scatter graph. Small recipes must work alone, expose their occupied space and connections, and compose into larger properties and districts without fighting one another.

This skill covers Unreal PCG and a native Unreal editor. Its planning model is portable across genres and game scales. If the user chooses another engine, retain the contracts and adapt the integration; do not introduce Unreal as an unsolicited dependency.

## Start with the actual project

Inspect the current engine version, modules, graph assets, actor classes, art tables, generation hooks, and named working level. Work in the user's exact files and level. Do not create alternate scenes, backup copies, or a new project unless requested or genuinely required. Do not change live game content merely to demonstrate this skill.

Recover requirements from the request and project before asking questions. Resolve only consequential unknowns: player/vehicle dimensions, traversal constraints, architectural style, intended settlement scale, editor-time versus runtime generation, and terrain modification policy. Distinguish width/length from area when changing scale. A fivefold increase in each dimension is 25 times the land area.

Inventory existing recipes and reuse them through adapters where possible. Keep art paths, theme proportions, budgets, physical dimensions, and default presets in project data. Do not carry over a previous game's names, maps, meshes, numerical limits, or hardcoded assumptions.

## Read the relevant reference

Load only the references needed for the current work; a targeted bug fix does not require rebuilding the entire system.

| Task | Reference |
|---|---|
| Modular shells, roofs, facade framing, interiors, curved buildings, foundations | [Building construction](references/building-construction.md) |
| Small PCG recipes, composition contracts, compound properties, dressing | [Recipe composition](references/recipe-composition.md) |
| Terrain, road networks, junctions, lots, terraces, access | [Settlement planning](references/settlement-planning.md) |
| Ownership, overrides, local updates, persistence, undo and failure handling | [Targeted regeneration](references/targeted-regeneration.md) |
| Dockable map, staged settings, road tools, selection, coordinate correctness | [Native editor](references/native-editor.md) |
| Build workflow, scripted and hands-on checks, performance and handoff | [Validation and delivery](references/validation-and-delivery.md) |

## Architecture that should survive a change of game

Separate these responsibilities even when an initial prototype places them in fewer files:

- **Art kit:** role-tagged mesh/material tables, assembly dimensions, sockets, collision and variation rules.
- **Building recipe:** design parameters become architecture, interior regions, openings, entrance anchors, and a measured footprint.
- **Local recipes:** yards, paths, agriculture, boundaries, commerce, furniture, vegetation, and detail clusters with declared inputs and outputs.
- **Compound property:** one addressable property composes a home and farm, shop and workshop, factory and loading yard, or other themed combination.
- **Planner:** terrain and road graph establish usable parcels; reservations coordinate recipe placement.
- **Update service:** one dependency-aware queue executes both editor and viewport edits.
- **Editor:** read-only map model plus temporary drafts; commits through the same update service.

Prefer a thin PCG graph wrapper over shared deterministic layout logic when topology, asset fitting, transactions, or ownership need native code. Use PCG for spatial sampling, filtering, instancing, and suitable subgraphs. Do not reproduce the same layout algorithm independently in Python, Blueprint, C++, and the editor.

The preferred dependency order is ground -> roads/junctions -> parcels/access -> architecture/compound properties -> yards/boundaries -> dressing. Refine phases to the game. Where access depends on the final building entrance, plan from a deterministic descriptor first and verify the generated result before final dressing; avoid recursive parent-child rebuilds.

## Essential invariants

1. Stable item identity is independent of array order, display name, position, and spline station index. Child identity is owned by its property, with independently editable descendants.
2. Seeds are derived from stable identity and recipe role. Editing one item must not consume a shared random stream that reshuffles others.
3. All placements declare footprints, height ranges, openings, access, support requirements, and relevant exclusions. AABB overlap is a broad phase, not proof that rotated or concave objects collide.
4. Ground sampling excludes generated output and distinguishes unavailable ground from unsuitable ground. Missing ground or assets must not erase valid saved output before a replacement exists.
5. Defaults generate on a genuinely new actor's completed placement. Loading a saved actor, opening a panel, or changing selection must not generate a new neighborhood.
6. Local edits preserve unrelated output, settings, selection, and IDs. Global changes announce their larger scope; never silently fall back to a full rebuild.
7. Position pinning and protected settings are separate. Editing one nested farm does not pin or rebuild every sibling.
8. Road edits retain existing buildings and recompute affected access. Repositioning plots is an explicit refit operation with pin/override rules.
9. Map rendering, picking, panning, zooming, and road dragging share one verified world-to-map transform and its inverse.
10. Planned, generated, pending-ground, rejected, failed, and needs-review are distinct states. Report actual outcomes, not just scheduled work.

## Implementation order

For an existing planner/editor, implement the update service before attaching new UI. For a new project, first establish one reliable building recipe and one compound property, then the planner and scheduler, then the editor. A useful vertical slice is one road, two different properties, one connected entrance per property, and a local edit that leaves the other property untouched.

Expand to junctions, loops, terrain, building variety, and detail recipes once that slice holds. Add density and scale after ownership, clearance, and incremental updates work. The requested scope determines which recipes to implement; this reference catalog is not a mandate to add every system.

Build native code against the project's actual engine. Python or a remote editor bridge may inspect assets, prepare kits, run tests, and capture screenshots; the shipping artist workflow should not depend on a chat connection. Check available automation capabilities before promising live inspection. Report compiled, scripted, visually checked, and still-unverified behavior separately.

Deliver the requested implementation and a short artist workflow in the user's chosen location. For a guide, prioritize place/open -> select -> edit -> preview -> apply -> inspect warnings -> save. Include only necessary artifacts and actual screenshots. Consult [validation and delivery](references/validation-and-delivery.md) for checks that catch the failure modes of this architecture.
