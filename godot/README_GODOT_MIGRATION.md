# Medieval Battlefield Editor — Godot GPU migration

This is a parallel editor implementation. The current Tkinter 5.x editor remains the stable application.

## Engine

The prototype targets Godot 4.7.2 stable. Godot provides a dedicated 2D renderer; CanvasItem custom drawing is cached until a redraw is queued, and viewport/canvas transforms are designed for efficient scrolling and zooming.

This prototype deliberately does not replace the existing launcher yet.

## What is already implemented

- GPU-backed 2D map surface.
- World-space camera with middle-mouse pan and wheel zoom.
- Stable world-space map border.
- Legacy JSON loader for objects, units, paths, and terrain/biome records.
- Separate rendering passes for terrain, rivers, roads, and decorative objects.
- Scrollable object library.
- User asset import into user://shared_assets.
- Object fields for size, scale and rotation are accepted from legacy JSON.
- A demo map with roads, a tributary river, biomes, and sample SVG art.

## Why the architecture is different

The 5.x editor currently relies on a Tkinter Canvas and repeated UI-driven redraws. The new branch moves the viewport to a GPU-friendly scene tree:

MapRenderer (Node2D)
  -> cached custom drawing for map layers
  -> transform-based camera movement
  -> texture-backed map objects
UI (CanvasLayer)
  -> fixed panels/tabs independent from map zoom

That separation is important: the UI remains fixed while the map transforms, and camera motion does not require rebuilding every UI element.

## Compatibility goal

The legacy JSON format is treated as the interchange format during migration. Unknown keys are preserved in the loaded document instead of being discarded by the importer.

The old 5.x editor is not deleted or replaced.

## Next migration milestones

1. Match the existing 5.8 road/water appearance exactly.
2. Add true road/river graph editing and endpoint snapping.
3. Port the terrain brush with smooth biome transitions.
4. Port object selection, drag, 10–500% scale and 360° rotation.
5. Port the 100+ object library and shared asset packs.
6. Port battle calculations and the dedicated battle-results panel.
7. Add migration validation against old/new map files.
8. Switch the launcher only after parity tests pass.
