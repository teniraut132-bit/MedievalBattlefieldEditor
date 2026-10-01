class_name MapDocument
extends RefCounted

var data: Dictionary = {
    "version": 1,
    "name": "Новая карта",
    "objects": [],
    "units": [],
}

func _as_dict(value) -> Dictionary:
    return value if value is Dictionary else {}

func _normalize_points(value) -> Array[Vector2]:
    var result: Array[Vector2] = []
    if value is Array:
        for item in value:
            if item is Dictionary:
                result.append(Vector2(float(item.get("x", 0.0)), float(item.get("y", 0.0))))
            elif item is Array and item.size() >= 2:
                result.append(Vector2(float(item[0]), float(item[1])))
    return result

func load_json(path: String) -> bool:
    if not FileAccess.file_exists(path):
        return false
    var text := FileAccess.get_file_as_string(path)
    var parsed = JSON.parse_string(text)
    if not (parsed is Dictionary):
        return false
    data = parsed
    if not data.has("objects"):
        data["objects"] = []
    if not data.has("units"):
        data["units"] = []
    return true

func world_size() -> Vector2:
    var size = data.get("map_size", data.get("world_size", [8000, 5000]))
    if size is Array and size.size() >= 2:
        return Vector2(float(size[0]), float(size[1]))
    if size is Dictionary:
        return Vector2(float(size.get("x", 8000)), float(size.get("y", 5000)))
    return Vector2(8000, 5000)

func objects() -> Array:
    return data.get("objects", [])

func units() -> Array:
    return data.get("units", [])

func extract_paths(kind: String) -> Array:
    var result: Array = []
    for raw in objects():
        var obj := _as_dict(raw)
        if str(obj.get("kind", "")) != kind:
            continue
        var points := _normalize_points(obj.get("points", []))
        if points.size() >= 2:
            result.append({
                "points": points,
                "width": float(obj.get("width", 25.0)),
                "road_type": str(obj.get("road_type", "Просёлочная")),
                "terrain": str(obj.get("terrain", "Луг")),
                "id": str(obj.get("id", "")),
            })
    return result

func extract_terrain() -> Array:
    var result: Array = []
    for raw in objects():
        var obj := _as_dict(raw)
        var kind := str(obj.get("kind", ""))
        if kind not in ["terrain", "biome", "terrain_patch", "landscape", "biome_brush", "terrain_brush"]:
            continue
        var points := _normalize_points(obj.get("points", []))
        if points.size() >= 2:
            result.append({
                "points": points,
                "width": float(obj.get("width", 100.0)),
                "terrain": str(obj.get("terrain", "Луг")),
            })
    return result
