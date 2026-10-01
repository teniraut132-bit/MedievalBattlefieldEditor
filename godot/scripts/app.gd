extends Node

const MAP_RENDERER = preload("res://scripts/map_renderer.gd")
const APP_VERSION := "6.0.0-alpha.1"

var map_renderer: MapRenderer
var status_label: Label
var library_grid: GridContainer
var library_scroll: ScrollContainer
var file_dialog: FileDialog

func _ready() -> void:
    map_renderer = MAP_RENDERER.new()
    add_child(map_renderer)
    _build_ui()
    _load_demo_map()

func _build_ui() -> void:
    var ui := CanvasLayer.new()
    add_child(ui)

    var root := Control.new()
    root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    ui.add_child(root)

    var top := PanelContainer.new()
    top.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
    top.custom_minimum_size = Vector2(0,64)
    root.add_child(top)
    var top_box := HBoxContainer.new()
    top.add_child(top_box)
    var title := Label.new()
    title.text = "  MEDIEVAL BATTLEFIELD EDITOR  •  GPU ENGINE"
    title.add_theme_font_size_override("font_size", 20)
    top_box.add_child(title)
    var spacer := Control.new()
    spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    top_box.add_child(spacer)
    var version := Label.new()
    version.text = APP_VERSION
    top_box.add_child(version)

    var left := PanelContainer.new()
    left.position = Vector2(0,64)
    left.size = Vector2(330,776)
    root.add_child(left)
    var tabs := TabContainer.new()
    left.add_child(tabs)

    var terrain := VBoxContainer.new()
    terrain.name = "Ландшафт"
    tabs.add_child(terrain)
    var terrain_title := Label.new()
    terrain_title.text = "ЛАНДШАФТ"
    terrain_title.add_theme_font_size_override("font_size", 18)
    terrain.add_child(terrain_title)
    var terrain_hint := Label.new()
    terrain_hint.text = "Кисть и слои будут работать здесь. Границы биомов не затрагивают сеть дорог и рек."
    terrain_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    terrain.add_child(terrain_hint)
    for n in ["Луг","Лес","Пустыня","Пашня","Болото","Скалы","Редколесье","Снег"]:
        var b := Button.new()
        b.text = n
        terrain.add_child(b)

    var roads := VBoxContainer.new()
    roads.name = "Дороги и реки"
    tabs.add_child(roads)
    var roads_title := Label.new()
    roads_title.text = "ДОРОГИ И РЕКИ"
    roads_title.add_theme_font_size_override("font_size", 18)
    roads.add_child(roads_title)
    var roads_hint := Label.new()
    roads_hint.text = "Слой сети отделён от ландшафта. Геометрию старого редактора не изменяем."
    roads_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    roads.add_child(roads_hint)
    for n in ["Просёлочная","Мощенная","Брусчаточная","Река"]:
        var b := Button.new()
        b.text = n
        roads.add_child(b)

    var objects := VBoxContainer.new()
    objects.name = "Объекты"
    tabs.add_child(objects)
    var object_title := Label.new()
    object_title.text = "БИБЛИОТЕКА ОБЪЕКТОВ"
    object_title.add_theme_font_size_override("font_size", 18)
    objects.add_child(object_title)
    var import_button := Button.new()
    import_button.text = "＋ Импортировать свои спрайты"
    import_button.pressed.connect(_on_import_pressed)
    objects.add_child(import_button)

    library_scroll = ScrollContainer.new()
    library_scroll.custom_minimum_size = Vector2(0, 640)
    library_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
    objects.add_child(library_scroll)
    library_grid = GridContainer.new()
    library_grid.columns = 3
    library_scroll.add_child(library_grid)
    _refresh_library()

    var right := PanelContainer.new()
    right.position = Vector2(1260,64)
    right.size = Vector2(340,776)
    root.add_child(right)
    var info := VBoxContainer.new()
    right.add_child(info)
    var info_title := Label.new()
    info_title.text = "СВОЙСТВА"
    info_title.add_theme_font_size_override("font_size", 18)
    info.add_child(info_title)
    status_label = Label.new()
    status_label.text = "GPU renderer: готов"
    status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    info.add_child(status_label)

    var open_btn := Button.new()
    open_btn.text = "Открыть старую карту (.json)"
    open_btn.pressed.connect(_on_open_pressed)
    info.add_child(open_btn)

    var center_btn := Button.new()
    center_btn.text = "Сбросить вид"
    center_btn.pressed.connect(map_renderer.reset_view)
    info.add_child(center_btn)

    file_dialog = FileDialog.new()
    file_dialog.access = FileDialog.ACCESS_FILESYSTEM
    file_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    file_dialog.filters = PackedStringArray(["*.json ; Карты Medieval Battlefield"])
    file_dialog.file_selected.connect(_on_file_selected)
    root.add_child(file_dialog)

func _load_demo_map() -> void:
    map_renderer.document.data = {
        "version": 1,
        "name": "GPU migration demo",
        "map_size": [8000,5000],
        "objects": [
            {"id":"river_main","kind":"river","points":[[-3300,-1800],[-2300,-1300],[-900,-850],[250,-900],[1500,-500],[3300,150]],"width":110},
            {"id":"river_tributary","kind":"river","points":[[-300,-1750],[-50,-1250],[250,-900]],"width":65},
            {"id":"road_west","kind":"road","points":[[-3800,1150],[-2500,950],[-1200,700],[0,650],[1350,900],[3300,1300]],"width":70,"road_type":"Просёлочная"},
            {"id":"road_north","kind":"road","points":[[-50,-2500],[-10,-1650],[120,-900],[0,650]],"width":58,"road_type":"Мощенная"},
            {"id":"forest_demo","kind":"terrain","terrain":"Лес","points":[[-2500,-700],[-2000,-400],[-1550,-550],[-1850,-1000]],"width":600},
            {"id":"field_demo","kind":"terrain","terrain":"Пашня","points":[[900,1200],[1600,1300],[2200,1500]],"width":500},
            {"id":"tree_demo","kind":"asset","asset":"sample_tree","x":-1600,"y":-250,"size":320,"obj_scale":1.0,"rotation":0.0},
            {"id":"house_demo","kind":"asset","asset":"sample_house","x":1100,"y":900,"size":360,"obj_scale":1.0,"rotation":0.0}
        ],
        "units":[]
    }
    map_renderer.queue_redraw()
    status_label.text = "GPU renderer: демо-карта загружена. Среда: Godot 4.7.2"

func _refresh_library() -> void:
    if library_grid == null:
        return
    for child in library_grid.get_children():
        child.queue_free()
    for name in map_renderer.assets.builtin_names():
        var b := Button.new()
        b.text = str(name).get_file()
        b.custom_minimum_size = Vector2(95,74)
        var tex := map_renderer.assets.texture(name)
        if tex:
            b.icon = tex
            b.expand_icon = true
        library_grid.add_child(b)
    for name in map_renderer.assets.user_names():
        var b := Button.new()
        b.text = "user:"+name
        b.custom_minimum_size = Vector2(95,74)
        b.icon = map_renderer.assets.texture("user:"+name)
        b.expand_icon = true
        library_grid.add_child(b)

func _on_import_pressed() -> void:
    var dialog := FileDialog.new()
    dialog.access = FileDialog.ACCESS_FILESYSTEM
    dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILES
    dialog.filters = PackedStringArray(["*.png,*.webp,*.jpg,*.jpeg,*.svg ; Изображения"])
    dialog.files_selected.connect(func(paths: PackedStringArray):
        var count := map_renderer.assets.import_files(paths)
        status_label.text = "Импортировано: %d. Файлы сохранены в общем пользовательском каталоге." % count
        _refresh_library()
        dialog.queue_free()
    )
    add_child(dialog)
    dialog.popup_centered_ratio(0.75)

func _on_open_pressed() -> void:
    file_dialog.popup_centered_ratio(0.75)

func _on_file_selected(path: String) -> void:
    if map_renderer.load_map(path):
        status_label.text = "Карта загружена: " + path
    else:
        status_label.text = "Не удалось прочитать карту: " + path
