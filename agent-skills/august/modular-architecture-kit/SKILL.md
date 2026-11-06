---
name: modular-architecture-kit
description: "Create or extend procedural modular architecture kits for artist handoff and later procedural assembly. Use for turning building generators or approved meshes into grid-based reference pieces, Houdini HDAs, reconstructable roof kits, and named FBX exports. Style-independent; focuses on authoring the kit rather than implementing a city planner or scatter graph."
---

# Modular Architecture Kit

Turn architectural references and building recipes into an artist-editable kit with explicit assembly contracts. The output should explain what each piece is, how it connects, and how an engine can reconstruct the building after an artist replaces the geometry.

This method grew from a Houdini-to-Unreal workflow, but its style rules, dimensions, paths, and presets are project data. Reuse the method for other architectural traditions and genres. Do not transplant a previous project's source assets or introduce Houdini/Unreal when the user chose another stack.

## Recover the existing tool and the requested outcome

Inspect the named scene, asset definition, build scripts, resolver, presets, export callbacks, source catalog, and existing documentation before changing the architecture. Trace a parameter through the resolved building, piece geometry, viewport, kit manifest, and export. A UI checkbox is not proof that the exporter respects it.

Edit and save the user's named working file in place. Preserve instance settings, parameter names, material overrides, and existing export behavior unless the request changes them. Avoid alternate scenes, precautionary copies, extra galleries, and generated evidence unless they serve the requested delivery or a concrete verification need.

Identify the requested output level:

- **Reference kit:** dimensional grayboxes and connection contracts for a human artist.
- **Detailed procedural kit:** added construction detail, UVs, materials, collision, and export policies.
- **Finished art:** requires visual acceptance as well as technical checks. A successful cook does not establish this status.

Do not expand a reference-kit task into finished materials, interiors, gameplay, or an Unreal PCG implementation. Supplying placement metadata is different from implementing its engine consumer.

## Audit the source and derive the vocabulary

Read approved assets and representative authored assemblies. Record the dimensions and facts needed for the task: local bounds, pivot, orientation, material slots, representative transforms, sockets, collision, and render settings. Never infer the assembly grid solely from a thumbnail or mesh AABB; overhangs and trims can extend beyond connection planes.

Classify pieces by architectural function: foundations, floors, ceilings, columns, beams, walls, doors/windows, railings, stairs, roofs, trims, and ornaments. Identify field pieces, ends, corners, junctions, and transitions where the source actually supports them. Distinguish reusable modules, complete assemblies, decorations, duplicates, and unresolved motifs.

Use approved kit measurements to set style profiles. If historical references are involved, distinguish measured construction, documented rules, comparative examples, and production interpretations. Record adaptations needed to fit the game grid rather than presenting them as historical measurements.

## Resolve the grid before generating detail

Keep grid X/Y/Z sizes as floating-point physical dimensions. Use integer cells for major width, depth, height, storeys, and spans; use explicit integer subdivisions for smaller assembly offsets. Retain the project's default. A 400 x 400 x 400 cm grid is a possible starting point when none exists, not a universal kit standard.

Resolve effective dimensions once and expose them in the UI. Whole-cell widths can still produce fractional bay lines if divided arbitrarily: allocate bays, setbacks, upper-storey lines, and attachment zones in supported discrete steps. Do not use arbitrary bay ratios or proportional scaling to silently break the assembly grid. Preserve legacy fine controls when compatibility requires them, while routing the new grid mode through the shared resolver.

Declare units, up/forward axes, handedness, origin, allowed rotations/reflections, and span conventions. For Unreal handoff, contracts commonly use centimetres and +Z up; document any Houdini metre/Y-up conversion explicitly. An axis swap can change handedness: verify winding and normals through the actual adapter rather than adding a blanket normal reversal.

Treat connection planes and anchors as the snap contract. Bounds can extend beyond them for documented overlap. Do not resize architecture by applying non-unit scale to finished meshes. Allow appearance variation inside the contract, without moving mating surfaces or attachment zones.

## Separate shared machinery from style rules

Prefer a deterministic chain:

`design controls -> resolved layout -> piece descriptors and placements -> geometry -> DCC preview/export`

Keep style proportions, roof topology, opening patterns, construction details, material variants, and presets separate from shared grid arithmetic, geometry utilities, identity, export, and validation. In a Python/Houdini implementation, keep the resolver independent of Houdini and make the Houdini adapter responsible for scene geometry and UI.

Derive complete assemblies and their modular pieces from the same resolved surfaces. Do not author unrelated approximations and imply they will reconstruct the building. Keep existing graybox identities stable where compatible; distinguish geometry revisions, quality, UV/material policies, and other geometry-affecting settings in cache keys. Export names are human-facing labels, not stable identity.

Complete one representative building end to end before expanding its preset family. Then exercise the variants that introduce new topology, such as corners, multi-storey setbacks, different roof forms, or multiple eaves. Reuse common machinery for the next style while keeping its rules and identities independent.

## Extract a usable artist kit

Start from resolved piece descriptors and placements. Deduplicate equivalent local geometry and contracts; retain a manifest mapping every source placement to the retained piece. Similar-looking columns are not automatically identical: dimensions, tilt, pivot, sockets, materials, or attachment interfaces can differ. Conversely, transform-only duplicates do not need separate model files.

Keep two useful views when the workflow needs both:

- **Full references:** complete roofs and assemblies that explain the intended building.
- **Compact modeling brief:** required grid modules plus a curated set of openings, brackets, bells, ornaments, and other adjuncts.

Compact means a useful modeling brief, not a filter that deletes everything without a strict grid footprint. Explicitly check walls, windows, floors, ceilings, railings, and style-defining decoration. Keep non-grid decorations labeled as adjuncts with attachment anchors.

Partition long railings, floor/ceiling surfaces, and trims as well as roofs. Include end/corner conditions; assign shared posts and overlapping details to one owner so repetition does not double them. Distinguish normalized reusable modules from pieces extracted for one particular assembly.

For roof decomposition, read [Roof partition and reassembly](references/roof-partition.md). It covers exact grid cuts, profile compatibility, tile ownership, interpolation, and reconstructable placement records. Read it only when roofs or curved surface partitions are part of the task.

Stage pieces for inspection by applying display-only transforms. Keep their export pivots and local geometry unchanged. Make full-reference, compact-kit, current-building, and combined-output controls understandable, and verify what each actually exports.

## Publish names and assembly data together

Use the project's naming convention. A useful Unreal-facing pattern is:

`SM_<Family>_<Role>_<Variant>_W###_D###_H###_NN`

Dimensions in names are readable rounded centimetres; exact dimensions and cell spans belong in the manifest. Use a deterministic suffix to disambiguate equal rounded names. Keep hashes in identity fields rather than repeating them in filenames. Style/family is data, not a hardcoded dynasty name.

For each piece record its stable identity, export name, family, role/variant, local dimensions, nominal grid span, pivot, axis convention, material slots, connection anchors, source/profile identity, and applicable UV/collision policies. For each assembly record instance identity, referenced piece identity, rigid transform, and coordinate frame. Separate display staging from reconstruction transforms.

When FBX is requested, export individual local-space meshes and, when requested, a combined FBX containing separately named mesh objects. A combined FBX is not nested FBX files and must not be silently fused into one mesh. Include the currently constructed building when the selected export mode calls for it; do not substitute a default preset. Preserve complete reference roofs if requested.

Keep source-local and composed building-space transforms explicit for later PCG. Identify which whole instance a modular assembly replaces and which separate decorations or structural layers it retains; otherwise a consumer can double-spawn the full roof and its modules.

Package only requested deliverables and their runtime dependencies. Do not include tests, previous exports, unrelated caches, or review renders in a lean handoff unless requested. Update an existing manifest/exporter rather than adding competing delivery paths.

## Verify at the useful boundaries

Scale checks to the change and the user's speed preference. Prioritize actual invariants over tests that repeat implementation details:

- Deterministic geometry, unique IDs/names, and intended deduplication.
- Grid-aligned connections and pivots, unit-scale placements, correct axis conversion and dimensions.
- Reassembly without missing regions, unwanted overlap, repeated terminal posts, or incompatible seam profiles.
- Preserved normals/materials/UVs; production texel density measured using texture resolution and material transforms when that is in scope.
- Compact coverage of required roles and exclusion of labels, debug bounds, measurements, and staging geometry from clean output.
- One isolated HDA cook and an FBX reimport checking separate objects, bounds, pivots, normals, and UV channels. Verify Unreal baking/load behavior when engine integration is part of the request.

Inspect a useful visual, such as assembled versus exploded geometry. Passing bounds checks will not reveal every missing surface or shading problem. Report scripted checks, visual inspection, engine validation, and unfinished work separately.

In Houdini, refresh embedded code and UI in a separate process while preserving the named HIP's scene and instance parameters. Do not replace a customized HIP with a fresh default scene from a build script. Avoid reloading definitions into the user's active session unexpectedly; explain how to load the updated tool. Embedded code must include its resolver and required data; optional preview caches should be relocatable.

Finish with the authoritative file location, the shortest artist workflow, and any actual assembly limitations. Do not call a reference kit universal or finished art merely because it exports successfully.
