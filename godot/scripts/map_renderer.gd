class_name MapRenderer
extends Node2D

const MAP_SIZE := Vector2(8000, 5000)
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
var zoom := 0.18
var pan := Vector2.ZERO
var dirty := true
var map_origin := Vector2(-4000, -2500)
var min_zoom := 0.08
var max_zoom := 3.5

func _ready() -> void:
    _apply_view()
    queue_redraw()
    set_process_unhandled_input(true)

func _notification(what: int) -> void:
    if what == NOTIFICATION_RESIZED:
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
    elif event is InputEventMouseButton:
        if event.button_index == MOUSE_BUTTON_MIDDLE:
            get_viewport().set_input_as_handled()
        elif event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
            _zoom_at_mouse(1.12)
            get_viewport().set_input_as_handled()
        elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
            _zoom_at_mouse(1.0 / 1.12)
            get_viewport().set_input_as_handled()

func _zoom_at_mouse(factor: float) -> void:
    var mouse := get_viewport().get_mouse_position()
    var before := to_local(mouse)
    zoom = clamp(zoom * factor, min_zoom, max_zoom)
    _apply_view()
    var after := to_local(mouse)
    position += (after - before) * zoom
    pan = position - get_viewport_rect().size * 0.5

func _draw() -> void:
    var size := document.world_size()
    draw_rect(Rect2(map_origin, size), Color("#cbbd96"), true)
    _draw_parchment_texture()
    _draw_biomes()
    _draw_river_network()
    _draw_road_network()
    _draw_map_border()
    _draw_objects()

func _draw_parchment_texture() -> void:
    var size := document.world_size()
    var step := 96.0
    var rng := RandomNumberGenerator.new()
    rng.seed = 56001
    for y in range(int(map_origin.y), int(map_origin.y + size.y), int(step)):
        for x in range(int(map_origin.x), int(map_origin.x + size.x), int(step)):
            var a := rng.randf_range(0.012, 0.035)
            draw_circle(Vector2(x + rng.randf_range(0, step), y + rng.randf_range(0, step)), rng.randf_range(2, 7), Color(0.24,0.18,0.10,a))

func _smooth_path(points: Array[Vector2]) -> PackedVector2Array:
    if points.size() <= 2:
        return PackedVector2Array(points)
    var out := PackedVector2Array()
    const STEPS := 7
    for i in range(points.size() - 1):
        var p0 := points[max(0, i - 1)]
        var p1 := points[i]
        var p2 := points[i + 1]
        var p3 := points[min(points.size() - 1, i + 2)]
        for s in range(STEPS):
            var t := float(s) / float(STEPS)
            var t2 := t * t
            var t3 := t2 * t
            var p := 0.5 * ((2.0*p1) + (-p0+p2)*t + (2.0*p0-5.0*p1+4.0*p2-p3)*t2 + (-p0+3.0*p1-3.0*p2+p3)*t3)
            out.append(p)
    out.append(points[points.size()-1])
    return out

func _draw_river_network() -> void:
    var paths := document.extract_paths("river")
    for item in paths:
        var p := _smooth_path(item.points)
        var w := max(4.0, item.width)
        draw_polyline(p, Color("#4d463c"), w + 28.0, true)
    for item in paths:
        var p := _smooth_path(item.points)
        var w := max(3.0, item.width)
        draw_polyline(p, Color("#55aaa3"), w, true)
    if zoom > 0.16:
        for item in paths:
            var p := _smooth_path(item.points)
            draw_polyline(p, Color("#95d0c7"), max(1.5, min(3.0, item.width * 0.08)), true)

func _road_surface_color(road_type: String) -> Color:
    match road_type:
        "Мощенная":
            return Color("#756b5d")
        "Брусчаточная":
            return Color("#897a64")
        _:
            return Color("#b79a70")

func _draw_road_network() -> void:
    var paths := document.extract_paths("road")
    for item in paths:
        var p := _smooth_path(item.points)
        var w := max(3.0, item.width)
        draw_polyline(p, Color("#514437"), w + 10.0, true)
    for item in paths:
        var p := _smooth_path(item.points)
        var w := max(2.0, item.width)
        draw_polyline(p, _road_surface_color(item.road_type), w, true)
    if zoom > 0.18:
        for item in paths:
            var p := _smooth_path(item.points)
            draw_polyline(p, Color("#d7c29b"), max(1.0, min(2.0, item.width * 0.06)), true)

func _draw_biomes() -> void:
    for item in document.extract_terrain():
        var p := _smooth_path(item.points)
        var terrain := str(item.terrain)
        var c: Color = TERRAIN_STYLE.get(terrain, TERRAIN_STYLE["Луг"])
        var width := max(18.0, float(item.width))
        draw_polyline(p, Color(c.r, c.g, c.b, 0.42), width, true)
        if zoom > 0.11:
            draw_polyline(p, Color(c.r*0.82, c.g*0.82, c.b*0.82, 0.18), width + 4.0, true)

func _draw_map_border() -> void:
    var rect := Rect2(map_origin, document.world_size())
    var w := clamp(18.0 / zoom, 4.0, 34.0)
    draw_rect(rect, Color("#4a3829"), false, w)
    draw_rect(rect.grow(-w * 0.32), Color("#dbc99b"), false, max(2.0, w * 0.16))

func _draw_objects() -> void:
    var bounds := Rect2(map_origin, document.world_size()).grow(500)
    for raw in document.objects():
        if not (raw is Dictionary):
            continue
        var obj: Dictionary = raw
        var kind := str(obj.get("kind", ""))
        if kind in ["river","road","terrain","biome","terrain_patch","landscape","biome_brush","terrain_brush"]:
            continue
        var pos := Vector2(float(obj.get("x", 0.0)), float(obj.get("y", 0.0)))
        if not bounds.has_point(pos):
            continue
        var name := str(obj.get("asset", obj.get("sprite", "")))
        var tex := assets.texture(name)
        var object_scale := float(obj.get("obj_scale", 1.0))
        var size := float(obj.get("size", 100.0)) * object_scale
        var rotation := float(obj.get("rotation", 0.0))
        if tex:
            var dims := tex.get_size()
            var ratio := min(size / max(1.0,dims.x), size / max(1.0,dims.y))
            var tsize := dims * ratio
            draw_set_transform(pos, rotation, Vector2.ONE)
            draw_texture_rect(tex, Rect2(-tsize*0.5, tsize), false)
            draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
        else:
            draw_circle(pos, max(12.0, size*0.22), Color("#7b2e28"))
            draw_arc(pos, max(12.0, size*0.22), 0, TAU, 24, Color("#e3b19b"), 3)
            draw_string(ThemeDB.fallback_font, pos + Vector2(-7,6), "?", HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color("#f6ddce"))
