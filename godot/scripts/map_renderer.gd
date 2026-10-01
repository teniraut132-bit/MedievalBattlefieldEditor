class_name MapRenderer
extends Node2D

const TERRAIN_STYLE := {
    "Луг": Color("#9ea979"),
    "Лес": Color("#667956"),
    "Пустыня": Color("#d3b779"),
    "Пашня": Color("#b09261"),
    "Болото": Color("#718e7b"),
    "Скалы": Color("#88857c"),
    "Редколесье": Color("#89986a"),
    "Снег": Color("#d6d9d3"),
}

var document := MapDocument.new()
var assets := AssetLibrary.new()
var zoom: float = 0.18
var pan: Vector2 = Vector2.ZERO
var dirty: bool = true
var map_origin := Vector2(-4000, -2500)
var min_zoom: float = 0.08
var max_zoom: float = 3.5

func _ready() -> void:
    _apply_view()
    get_viewport().size_changed.connect(_on_viewport_resized)
    queue_redraw()

func _on_viewport_resized() -> void:
    _apply_view()

func load_map(path: String) -> bool:
    if not document.load_json(path):
        return false
    dirty = true
    queue_redraw()
    return true

func reset_view() -> void:
    zoom = 0.18
    pan = Vector2.ZERO
    _apply_view()

func _apply_view() -> void:
    position = get_viewport_rect().size * 0.5 + pan
    scale = Vector2.ONE * zoom

func _process(_delta: float) -> void:
    if dirty:
        dirty = false
        queue_redraw()

func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_MIDDLE):
        pan += event.relative
        _apply_view()
        get_viewport().set_input_as_handled()
    elif event is InputEventMouseButton and event.pressed:
        if event.button_index == MOUSE_BUTTON_WHEEL_UP:
            _zoom_at_mouse(1.12)
            get_viewport().set_input_as_handled()
        elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
            _zoom_at_mouse(1.0 / 1.12)
            get_viewport().set_input_as_handled()
        elif event.button_index == MOUSE_BUTTON_MIDDLE:
            get_viewport().set_input_as_handled()

func _zoom_at_mouse(factor: float) -> void:
    var mouse: Vector2 = get_viewport().get_mouse_position()
    var before: Vector2 = to_local(mouse)
    zoom = clampf(zoom * factor, min_zoom, max_zoom)
    _apply_view()
    var after: Vector2 = to_local(mouse)
    position += (after - before) * zoom
    pan = position - get_viewport_rect().size * 0.5

func _draw() -> void:
    var size: Vector2 = document.world_size()
    draw_rect(Rect2(map_origin, size), Color("#cbbd96"), true)
    _draw_parchment_texture(size)
    _draw_biomes()
    _draw_river_network()
    _draw_road_network()
    _draw_map_border()
    _draw_objects()

func _draw_parchment_texture(size: Vector2) -> void:
    # One-time cached draw data; camera transforms do not rebuild this.
    var step: float = 96.0
    var rng := RandomNumberGenerator.new()
    rng.seed = 56001
    for y in range(int(map_origin.y), int(map_origin.y + size.y), int(step)):
        for x in range(int(map_origin.x), int(map_origin.x + size.x), int(step)):
            var a: float = rng.randf_range(0.012, 0.035)
            draw_circle(
                Vector2(x + rng.randf_range(0, step), y + rng.randf_range(0, step)),
                rng.randf_range(2, 7),
                Color(0.24,0.18,0.10,a)
            )

func _smooth_path(points: Array[Vector2]) -> PackedVector2Array:
    if points.size() <= 2:
        return PackedVector2Array(points)
    var out := PackedVector2Array()
    const STEPS: int = 7
    for i in range(points.size() - 1):
        var p0: Vector2 = points[max(0, i - 1)]
        var p1: Vector2 = points[i]
        var p2: Vector2 = points[i + 1]
        var p3: Vector2 = points[min(points.size() - 1, i + 2)]
        for step in range(STEPS):
            var t: float = float(step) / float(STEPS)
            var t2: float = t * t
            var t3: float = t2 * t
            var p: Vector2 = 0.5 * (
                (2.0 * p1)
                + (-p0 + p2) * t
                + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
                + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
            )
            out.append(p)
    out.append(points[points.size() - 1])
    return out

func _draw_river_network() -> void:
    var paths: Array = document.extract_paths("river")
    # v5.8-style appearance: banks first for the full network, water second,
    # highlight third. No per-segment junction marker or circular stamp.
    for raw in paths:
        var item: Dictionary = raw
        var p: PackedVector2Array = _smooth_path(item.get("points", []))
        var width: float = maxf(4.0, float(item.get("width", 25.0)))
        draw_polyline(p, Color("#4d463c"), width + 28.0, true)
    for raw in paths:
        var item: Dictionary = raw
        var p: PackedVector2Array = _smooth_path(item.get("points", []))
        var width: float = maxf(3.0, float(item.get("width", 25.0)))
        draw_polyline(p, Color("#55aaa3"), width, true)
    if zoom > 0.16:
        for raw in paths:
            var item: Dictionary = raw
            var p: PackedVector2Array = _smooth_path(item.get("points", []))
            var width: float = float(item.get("width", 25.0))
            draw_polyline(p, Color("#95d0c7"), maxf(1.5, minf(3.0, width * 0.08)), true)

func _road_surface_color(road_type: String) -> Color:
    match road_type:
        "Мощенная":
            return Color("#756b5d")
        "Брусчаточная":
            return Color("#897a64")
        _:
            return Color("#b79a70")

func _draw_road_network() -> void:
    var paths: Array = document.extract_paths("road")
    # Same three-pass order as the established 5.8 renderer.
    for raw in paths:
        var item: Dictionary = raw
        var p: PackedVector2Array = _smooth_path(item.get("points", []))
        var width: float = maxf(3.0, float(item.get("width", 25.0)))
        draw_polyline(p, Color("#514437"), width + 10.0, true)
    for raw in paths:
        var item: Dictionary = raw
        var p: PackedVector2Array = _smooth_path(item.get("points", []))
        var width: float = maxf(2.0, float(item.get("width", 25.0)))
        draw_polyline(p, _road_surface_color(str(item.get("road_type", "Просёлочная"))), width, true)
    if zoom > 0.18:
        for raw in paths:
            var item: Dictionary = raw
            var p: PackedVector2Array = _smooth_path(item.get("points", []))
            var width: float = float(item.get("width", 25.0))
            draw_polyline(p, Color("#d7c29b"), maxf(1.0, minf(2.0, width * 0.06)), true)

func _draw_biomes() -> void:
    var paths: Array = document.extract_terrain()
    for raw in paths:
        var item: Dictionary = raw
        var p: PackedVector2Array = _smooth_path(item.get("points", []))
        var terrain: String = str(item.get("terrain", "Луг"))
        var c: Color = TERRAIN_STYLE["Луг"]
        if TERRAIN_STYLE.has(terrain):
            c = Color(TERRAIN_STYLE[terrain])
        var width: float = maxf(18.0, float(item.get("width", 100.0)))
        draw_polyline(p, Color(c.r, c.g, c.b, 0.42), width, true)
        if zoom > 0.11:
            draw_polyline(p, Color(c.r*0.82, c.g*0.82, c.b*0.82, 0.18), width + 4.0, true)

func _draw_map_border() -> void:
    var rect := Rect2(map_origin, document.world_size())
    # Border is world-space and therefore remains visible and stable at every zoom.
    var width: float = clampf(18.0 / maxf(0.01, zoom), 4.0, 34.0)
    draw_rect(rect, Color("#4a3829"), false, width)
    draw_rect(rect.grow(-width * 0.32), Color("#dbc99b"), false, maxf(2.0, width * 0.16))

func _draw_objects() -> void:
    var bounds := Rect2(map_origin, document.world_size()).grow(500)
    for raw in document.objects():
        if not (raw is Dictionary):
            continue
        var obj: Dictionary = raw
        var kind: String = str(obj.get("kind", ""))
        if kind in ["river","road","terrain","biome","terrain_patch","landscape","biome_brush","terrain_brush"]:
            continue
        var pos := Vector2(float(obj.get("x", 0.0)), float(obj.get("y", 0.0)))
        if not bounds.has_point(pos):
            continue
        var asset_name: String = str(obj.get("asset", obj.get("sprite", "")))
        var tex: Texture2D = assets.texture(asset_name)
        var object_scale: float = float(obj.get("obj_scale", 1.0))
        var size: float = float(obj.get("size", 100.0)) * object_scale
        var rotation: float = float(obj.get("rotation", 0.0))
        if tex:
            var dims: Vector2 = tex.get_size()
            var ratio: float = minf(size / maxf(1.0,dims.x), size / maxf(1.0,dims.y))
            var texture_size: Vector2 = dims * ratio
            draw_set_transform(pos, rotation, Vector2.ONE)
            draw_texture_rect(tex, Rect2(-texture_size*0.5, texture_size), false)
            draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
        else:
            draw_circle(pos, maxf(12.0, size*0.22), Color("#7b2e28"))
            draw_arc(pos, maxf(12.0, size*0.22), 0, TAU, 24, Color("#e3b19b"), 3)
            draw_string(ThemeDB.fallback_font, pos + Vector2(-7,6), "?", HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color("#f6ddce"))
