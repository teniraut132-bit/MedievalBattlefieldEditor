class_name AssetLibrary
extends RefCounted

signal changed

const USER_ROOT := "user://shared_assets"
const PACK_VERSION := 1

var builtins: Dictionary = {}
var user_files: Array[String] = []

func _init() -> void:
    DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(USER_ROOT))
    _scan_user_assets()
    _scan_builtins()

func _scan_builtins() -> void:
    builtins.clear()
    _scan_dir("res://assets", "")

func _scan_dir(base_path: String, prefix: String) -> void:
    var dir := DirAccess.open(base_path)
    if dir == null:
        return
    dir.list_dir_begin()
    while true:
        var name := dir.get_next()
        if name.is_empty():
            break
        if name.begins_with("."):
            continue
        var full := base_path.path_join(name)
        if dir.current_is_dir():
            _scan_dir(full, prefix + name + "/")
        elif name.to_lower().ends_with(".svg") or name.to_lower().ends_with(".png") or name.to_lower().ends_with(".webp"):
            builtins[prefix + name.get_basename()] = full
    dir.list_dir_end()

func _scan_user_assets() -> void:
    user_files.clear()
    var dir := DirAccess.open(USER_ROOT)
    if dir == null:
        return
    dir.list_dir_begin()
    while true:
        var name := dir.get_next()
        if name.is_empty():
            break
        if dir.current_is_dir():
            continue
        var lower := name.to_lower()
        if lower.ends_with(".png") or lower.ends_with(".webp") or lower.ends_with(".jpg") or lower.ends_with(".jpeg") or lower.ends_with(".svg"):
            user_files.append(name)
    dir.list_dir_end()
    user_files.sort()

func builtin_names() -> Array:
    return builtins.keys()

func user_names() -> Array[String]:
    return user_files.duplicate()

func texture(name: String) -> Texture2D:
    if name.begins_with("user:"):
        return _user_texture(name.trim_prefix("user:"))
    if builtins.has(name):
        return load(builtins[name])
    var key := name.get_file().get_basename()
    for k in builtins.keys():
        if str(k).get_file().get_basename().to_lower() == key.to_lower():
            return load(builtins[k])
    return null

func _user_texture(filename: String) -> Texture2D:
    var path := USER_ROOT.path_join(filename)
    if not FileAccess.file_exists(path):
        return null
    var image := Image.load_from_file(ProjectSettings.globalize_path(path))
    if image == null:
        return null
    return ImageTexture.create_from_image(image)

func import_files(paths: PackedStringArray) -> int:
    DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(USER_ROOT))
    var count := 0
    for source in paths:
        var source_path := source
        var target := USER_ROOT.path_join(source_path.get_file())
        var data := FileAccess.get_file_as_bytes(source_path)
        if data.is_empty():
            continue
        var file := FileAccess.open(target, FileAccess.WRITE)
        if file:
            file.store_buffer(data)
            file.close()
            count += 1
    _scan_user_assets()
    changed.emit()
    return count

func export_shared_pack(path: String) -> bool:
    var packer := ZIPPacker.new()
    if packer.open(path) != OK:
        return false
    packer.start_file("manifest.json")
    packer.write_file(JSON.stringify({
        "format": "medieval_battlefield_asset_pack",
        "version": PACK_VERSION,
        "count": user_files.size()
    }).to_utf8_buffer())
    packer.close_file()

    for filename in user_files:
        var data := FileAccess.get_file_as_bytes(USER_ROOT.path_join(filename))
        if data.is_empty():
            continue
        if packer.start_file("assets/"+filename) != OK:
            packer.close()
            return false
        packer.write_file(data)
        packer.close_file()
    return packer.close() == OK

func import_shared_pack(path: String) -> int:
    var reader := ZIPReader.new()
    if reader.open(path) != OK:
        return 0
    var imported := 0
    for file_name in reader.get_files():
        if not file_name.begins_with("assets/"):
            continue
        var filename := file_name.trim_prefix("assets/").get_file()
        if filename.is_empty():
            continue
        var data := reader.read_file(file_name)
        if data.is_empty():
            continue
        var target := USER_ROOT.path_join(filename)
        var file := FileAccess.open(target, FileAccess.WRITE)
        if file:
            file.store_buffer(data)
            file.close()
            imported += 1
    reader.close()
    _scan_user_assets()
    changed.emit()
    return imported
