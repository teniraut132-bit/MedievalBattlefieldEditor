# Medieval Battlefield Editor — Godot GPU migration

The Godot implementation is developed in parallel with the stable Tkinter 5.x editor. The legacy editor and launcher remain untouched while feature parity is built and validated.

## Engine

Target: Godot 4.7.2 stable. This is an official stable maintenance release from 18 August 2026. citeturn395378search0turn395378search2

The new viewport uses a Node2D-based renderer with a world-space transform and Godot's retained CanvasItem draw list. UI is separated into a CanvasLayer so the map can zoom and pan without rebuilding the fixed UI.

## Ported in alpha.2

- Legacy JSON map loader with unknown keys preserved.
- JSON save/save-as support.
- Stable world-space map border.
- Scrollable object library.
- Built-in and user asset lookup.
- User asset import into user://shared_assets.
- Legacy object fields: position, size, 10–500% scale, rotation.
- Ctrl+LMB object rotation path.
- Freehand terrain/biome brush with multiple terrain styles and soft layered edges.
- Freehand river and road tools with endpoint snapping.
- Road type tabs: rural, paved, cobblestone.
- Network-aware road/river rendering that merges degree-2 connected segments into continuous chains instead of drawing disconnected overlapping caps.
- Separate layer order: terrain -> rivers -> roads -> objects.
- Dedicated battle results panel and single-click battle simulation using personnel, training, morale, quality, weapons, armor and equipment condition.
- Compact tabbed UI.
- GPU-oriented renderer with cached smoothed geometry.

## Migration bridge

tools/import_legacy_assets_to_godot.py extracts the legacy embedded PNG resources from the archived 5.x source into godot/assets/legacy during CI. MapDocument remains the compatibility boundary: maps are still JSON and legacy object records are not discarded.

## Next parity milestones

1. Port full unit placement/dragging and troop details editor.
2. Port siege entities and equipment/item cost breakdowns.
3. Port battle result history and post-battle equipment destruction states.
4. Add shared asset-pack import/export so users can exchange custom sprite packs.
5. Port generator with seeded terrain, biome transitions and random asset placement.
6. Finish the 100+ asset library and category browsing.
7. Add project migration validation: load legacy map -> save with Godot -> reload legacy -> compare structural data.
8. Add launcher integration only after parity tests pass.

## Validation

.github/workflows/godot-migration.yml imports the project, parses the Godot scripts and exports a Windows build with Godot 4.7.2. The stable 5.x application is not replaced until the migration branch passes feature-parity tests.
