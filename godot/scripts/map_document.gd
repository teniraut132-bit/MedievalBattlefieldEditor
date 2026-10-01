class_name MapDocument
extends RefCounted

signal changed

var data: Dictionary = {
    "version": 7,
    "name": "Новая карта",
    "map_size": [8000, 5000],
    "objects": [],
    "units": [],
}

var source_path: String = ""

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

func _points_to_json(points: Array[Vector2]) -> Array:
    var result: Array = []
    for p in points:
        result.append({"x": p.x, "y": p.y})
    return result

func load_json(path: String) -> bool:
    if not FileAccess.file_exists(path):
        return false
    var text := FileAccess.get_file_as_string(path)
    var parsed = JSON.parse_string(text)
    if not (parsed is Dictionary):
        return false
    data = parsed
    source_path = path
    if not data.has("objects"):
        data["objects"] = []
    if not data.has("units"):
        data["units"] = []
    if not data.has("map_size"):
        data["map_size"] = [8000, 5000]
    if not data.has("version"):
        data["version"] = 7
    changed.emit()
    return true

func save_json(path: String = "") -> bool:
    var target := path
    if target.is_empty():
        target = source_path
    if target.is_empty():
        return false
    data["version"] = max(7, int(data.get("version", 7)))
    var file := FileAccess.open(target, FileAccess.WRITE)
    if file == null:
        return false
    file.store_string(JSON.stringify(data, "\t"))
    file.close()
    source_path = target
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

func touch() -> void:
    changed.emit()

func next_id(prefix: String = "obj") -> String:
    var n := 1
    var used: Dictionary = {}
    for raw in objects():
        if raw is Dictionary:
            used[str(raw.get("id", ""))] = true
    for raw in units():
        if raw is Dictionary:
            used[str(raw.get("id", ""))] = true
    while used.has("%s_%d" % [prefix, n]):
        n += 1
    return "%s_%d" % [prefix, n]

func object_at(index: int) -> Dictionary:
    if index < 0 or index >= objects().size():
        return {}
    return _as_dict(objects()[index])

func find_object_index(id: String) -> int:
    for i in range(objects().size()):
        var raw = objects()[i]
        if raw is Dictionary and str(raw.get("id", "")) == id:
            return i
    return -1

func upsert_object(obj: Dictionary) -> void:
    var id := str(obj.get("id", ""))
    var index := find_object_index(id)
    if index < 0:
        objects().append(obj)
    else:
        objects()[index] = obj
    touch()

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
                "id": str(obj.get("id", "")),
            })
    return result

func points_from_object(raw: Dictionary) -> Array[Vector2]:
    return _normalize_points(raw.get("points", []))

func set_points_for_object(index: int, points: Array[Vector2]) -> void:
    if index < 0 or index >= objects().size():
        return
    var obj := _as_dict(objects()[index])
    obj["points"] = _points_to_json(points)
    objects()[index] = obj
    touch()

func add_object(obj: Dictionary) -> int:
    objects().append(obj)
    touch()
    return objects().size() - 1

func remove_object(index: int) -> void:
    if index < 0 or index >= objects().size():
        return
    objects().remove_at(index)
    touch()

func add_unit(unit: Dictionary) -> int:
    units().append(unit)
    touch()
    return units().size() - 1
