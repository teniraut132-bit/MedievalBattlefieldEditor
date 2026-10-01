extends Node

const MAP_RENDERER = preload("res://scripts/map_renderer.gd")
const BATTLE_SIMULATOR = preload("res://scripts/battle_simulator.gd")
const APP_VERSION := "6.0.0-alpha.2"

var map_renderer: MapRenderer
var battle := BattleSimulator.new()

var status_label: Label
var library_grid: GridContainer
var library_scroll: ScrollContainer
var open_dialog: FileDialog
var save_dialog: FileDialog
var result_box: RichTextLabel
var scale_spin: SpinBox
var rotation_spin: SpinBox
var selected_label: Label

func _ready() -> void:
    map_renderer = MAP_RENDERER.new()
    add_child(map_renderer)
    map_renderer.selection_changed.connect(_on_selection_changed)
    map_renderer.changed.connect(_on_document_changed)
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
    top.custom_minimum_size = Vector2(0, 58)
    root.add_child(top)
    var top_box := HBoxContainer.new()
    top.add_child(top_box)
    var title := Label.new()
    title.text = "  MEDIEVAL BATTLEFIELD EDITOR  •  GODOT ENGINE"
    title.add_theme_font_size_override("font_size", 20)
    top_box.add_child(title)
    var spacer := Control.new()
    spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    top_box.add_child(spacer)
    var version := Label.new()
    version.text = APP_VERSION
    top_box.add_child(version)

    var left := PanelContainer.new()
    left.position = Vector2(0,58)
    left.size = Vector2(315,842)
    root.add_child(left)
    var tabs := TabContainer.new()
    left.add_child(tabs)

    _build_terrain_tab(tabs)
    _build_network_tab(tabs)
    _build_object_tab(tabs)
    _build_file_tab(tabs)
    _build_battle_tab(tabs)

    var right := PanelContainer.new()
    right.position = Vector2(1280,58)
    right.size = Vector2(320,842)
    root.add_child(right)
    var info := VBoxContainer.new()
    right.add_child(info)
    var info_title := Label.new()
    info_title.text = "СВОЙСТВА ОБЪЕКТА"
    info_title.add_theme_font_size_override("font_size", 17)
    info.add_child(info_title)
    selected_label = Label.new()
    selected_label.text = "Ничего не выбрано"
    selected_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    info.add_child(selected_label)

    scale_spin = SpinBox.new()
    scale_spin.min_value = 10
    scale_spin.max_value = 500
    scale_spin.step = 5
    scale_spin.value = 100
    scale_spin.suffix = " %"
    scale_spin.value_changed.connect(_on_scale_changed)
    info.add_child(scale_spin)

    rotation_spin = SpinBox.new()
    rotation_spin.min_value = -180
    rotation_spin.max_value = 180
    rotation_spin.step = 1
    rotation_spin.suffix = "°"
    rotation_spin.value_changed.connect(_on_rotation_changed)
    info.add_child(rotation_spin)

    var reset_btn := Button.new()
    reset_btn.text = "Сбросить вид"
    reset_btn.pressed.connect(map_renderer.reset_view)
    info.add_child(reset_btn)

    status_label = Label.new()
    status_label.text = "Godot GPU renderer: готов"
    status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    info.add_child(status_label)

    result_box = RichTextLabel.new()
    result_box.bbcode_enabled = true
    result_box.fit_content = false
    result_box.custom_minimum_size = Vector2(0, 250)
    result_box.scroll_active = true
    result_box.text = "[b]Итоги боя[/b]\nБой ещё не проводился."
    info.add_child(result_box)

    open_dialog = FileDialog.new()
    open_dialog.access = FileDialog.ACCESS_FILESYSTEM
    open_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    open_dialog.filters = PackedStringArray(["*.json ; Карты Medieval Battlefield"])
    open_dialog.file_selected.connect(_on_file_open)
    root.add_child(open_dialog)

    save_dialog = FileDialog.new()
    save_dialog.access = FileDialog.ACCESS_FILESYSTEM
    save_dialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
    save_dialog.filters = PackedStringArray(["*.json ; Карты Medieval Battlefield"])
    save_dialog.file_selected.connect(_on_file_save)
    root.add_child(save_dialog)

func _build_terrain_tab(tabs: TabContainer) -> void:
    var terrain := VBoxContainer.new()
    terrain.name = "Ландшафт"
    tabs.add_child(terrain)
    var title := Label.new()
    title.text = "ЛАНДШАФТ"
    title.add_theme_font_size_override("font_size", 18)
    terrain.add_child(title)
    var hint := Label.new()
    hint.text = "Зажми ЛКМ и рисуй биом. Границы ландшафта находятся под реками и дорогами."
    hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    terrain.add_child(hint)
    var scroll := ScrollContainer.new()
    scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
    terrain.add_child(scroll)
    var box := VBoxContainer.new()
    scroll.add_child(box)
    for n in ["Луг","Лес","Пустыня","Пашня","Болото","Скалы","Редколесье","Снег"]:
        var b := Button.new()
        b.text = n
        b.pressed.connect(func(): map_renderer.set_terrain(n); status_label.text = "Ландшафт: "+n)
        box.add_child(b)
    var brush := HSlider.new()
    brush.min_value = 80
    brush.max_value = 1500
    brush.step = 10
    brush.value = 500
    brush.value_changed.connect(func(v): map_renderer.set_brush_size(v))
    terrain.add_child(brush)

func _build_network_tab(tabs: TabContainer) -> void:
    var roads := VBoxContainer.new()
    roads.name = "Дороги и реки"
    tabs.add_child(roads)
    var title := Label.new()
    title.text = "СЕТИ"
    title.add_theme_font_size_override("font_size", 18)
    roads.add_child(title)
    var hint := Label.new()
    hint.text = "Концы новых сегментов автоматически привязываются к существующей сети."
    hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    roads.add_child(hint)
    var river := Button.new()
    river.text = "Рисовать реку"
    river.pressed.connect(func(): map_renderer.set_tool("river"); status_label.text = "Река: зажми ЛКМ и проведи русло")
    roads.add_child(river)
    for n in ["Просёлочная","Мощенная","Брусчаточная"]:
        var b := Button.new()
        b.text = "Дорога: "+n
        b.pressed.connect(func(): map_renderer.set_road_type(n); status_label.text = "Дорога: "+n)
        roads.add_child(b)

func _build_object_tab(tabs: TabContainer) -> void:
    var objects := VBoxContainer.new()
    objects.name = "Объекты"
    tabs.add_child(objects)
    var title := Label.new()
    title.text = "БИБЛИОТЕКА ОБЪЕКТОВ"
    title.add_theme_font_size_override("font_size", 18)
    objects.add_child(title)
    var import_button := Button.new()
    import_button.text = "＋ Импортировать спрайты"
    import_button.pressed.connect(_on_import_pressed)
    objects.add_child(import_button)

    library_scroll = ScrollContainer.new()
    library_scroll.custom_minimum_size = Vector2(0, 720)
    library_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
    objects.add_child(library_scroll)
    library_grid = GridContainer.new()
    library_grid.columns = 3
    library_scroll.add_child(library_grid)
    _refresh_library()

func _build_file_tab(tabs: TabContainer) -> void:
    var file_tab := VBoxContainer.new()
    file_tab.name = "Файл"
    tabs.add_child(file_tab)
    for spec in [["Открыть старую карту (.json)",_on_open_pressed],["Сохранить",_on_save_pressed],["Сохранить как…",_on_save_as_pressed]]:
        var b := Button.new()
        b.text = spec[0]
        b.pressed.connect(spec[1])
        file_tab.add_child(b)
    var border_hint := Label.new()
    border_hint.text = "Граница карты рисуется в мировых координатах и сохраняет видимость при изменении масштаба."
    border_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    file_tab.add_child(border_hint)

func _build_battle_tab(tabs: TabContainer) -> void:
    var battle_tab := VBoxContainer.new()
    battle_tab.name = "Сражение"
    tabs.add_child(battle_tab)
    var title := Label.new()
    title.text = "СИМУЛЯЦИЯ БОЯ"
    title.add_theme_font_size_override("font_size", 18)
    battle_tab.add_child(title)
    var hint := Label.new()
    hint.text = "Один клик рассчитывает потери, мораль, обучение и состояние снаряжения."
    hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    battle_tab.add_child(hint)
    var attack := SpinBox.new()
    attack.name = "AttackIndex"
    attack.min_value = 0
    attack.step = 1
    attack.value = 0
    battle_tab.add_child(attack)
    var defend := SpinBox.new()
    defend.name = "DefendIndex"
    defend.min_value = 0
    defend.step = 1
    defend.value = 1
    battle_tab.add_child(defend)
    var run := Button.new()
    run.text = "ПРОВЕСТИ БОЙ"
    run.pressed.connect(func(): _run_battle(int(attack.value),int(defend.value)))
    battle_tab.add_child(run)
    var results := Label.new()
    results.text = "Результат выводится справа, не через всплывающие уведомления."
    results.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    battle_tab.add_child(results)

func _load_demo_map() -> void:
    map_renderer.document.data = {
        "version": 7,
        "name": "Godot migration demo",
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
        "units":[
            {"id":"unit_red","name":"Отряд атакующих","personnel":240,"training":55,"morale":45,"quality":60,"weapon_power":60,"armor_power":50,"combat_bonus":1.0},
            {"id":"unit_blue","name":"Отряд обороняющихся","personnel":220,"training":65,"morale":55,"quality":70,"weapon_power":70,"armor_power":65,"combat_bonus":1.05}
        ]
    }
    map_renderer.queue_redraw()
    status_label.text = "GPU renderer: демо-карта загружена. Готов к миграционной проверке."

func _refresh_library() -> void:
    if library_grid == null:
        return
    for child in library_grid.get_children():
        child.queue_free()
    for name in map_renderer.assets.builtin_names():
        var b := Button.new()
        b.text = str(name).get_file()
        b.custom_minimum_size = Vector2(95,90)
        var tex := map_renderer.assets.texture(name)
        if tex:
            b.icon = tex
            b.expand_icon = true
        b.pressed.connect(func(): map_renderer.choose_asset(name))
        library_grid.add_child(b)
    for name in map_renderer.assets.user_names():
        var b := Button.new()
        b.text = "user:"+name
        b.custom_minimum_size = Vector2(95,90)
        b.icon = map_renderer.assets.texture("user:"+name)
        b.expand_icon = true
        b.pressed.connect(func(): map_renderer.choose_asset("user:"+name))
        library_grid.add_child(b)

func _on_import_pressed() -> void:
    var dialog := FileDialog.new()
    dialog.access = FileDialog.ACCESS_FILESYSTEM
    dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILES
    dialog.filters = PackedStringArray(["*.png,*.webp,*.jpg,*.jpeg,*.svg ; Изображения"])
    dialog.files_selected.connect(func(paths: PackedStringArray):
        var count := map_renderer.assets.import_files(paths)
        status_label.text = "Импортировано спрайтов: %d. Каталог обновлён." % count
        _refresh_library()
        dialog.queue_free()
    )
    add_child(dialog)
    dialog.popup_centered_ratio(0.75)

func _on_open_pressed() -> void:
    open_dialog.popup_centered_ratio(0.75)

func _on_save_pressed() -> void:
    if map_renderer.save_map():
        status_label.text = "Карта сохранена: "+map_renderer.document.source_path
    else:
        _on_save_as_pressed()

func _on_save_as_pressed() -> void:
    save_dialog.current_file = str(map_renderer.document.data.get("name","map"))+".json"
    save_dialog.popup_centered_ratio(0.75)

func _on_file_open(path: String) -> void:
    if map_renderer.load_map(path):
        status_label.text = "Карта загружена: "+path
    else:
        status_label.text = "Ошибка загрузки карты: "+path

func _on_file_save(path: String) -> void:
    if map_renderer.save_map(path):
        status_label.text = "Карта сохранена: "+path
    else:
        status_label.text = "Ошибка сохранения карты."

func _on_selection_changed(index: int) -> void:
    if index < 0:
        selected_label.text = "Ничего не выбрано"
        return
    var obj := map_renderer.document.object_at(index)
    selected_label.text = "%s\nID: %s" % [str(obj.get("kind","Объект")),str(obj.get("id",""))]
    scale_spin.set_value_no_signal(float(obj.get("obj_scale",1.0))*100.0)
    rotation_spin.set_value_no_signal(rad_to_deg(float(obj.get("rotation",0.0))))

func _on_scale_changed(value: float) -> void:
    if map_renderer.selected_index < 0:return
    var obj:=map_renderer.document.object_at(map_renderer.selected_index)
    if obj.is_empty():return
    obj["obj_scale"]=clampf(value/100.0,0.1,5.0)
    map_renderer.document.objects()[map_renderer.selected_index]=obj
    map_renderer.document.touch()

func _on_rotation_changed(value: float) -> void:
    if map_renderer.selected_index < 0:return
    var obj:=map_renderer.document.object_at(map_renderer.selected_index)
    if obj.is_empty():return
    obj["rotation"]=deg_to_rad(value)
    map_renderer.document.objects()[map_renderer.selected_index]=obj
    map_renderer.document.touch()

func _on_document_changed() -> void:
    pass

func _run_battle(attacker_index: int, defender_index: int) -> void:
    var units := map_renderer.document.units()
    if attacker_index < 0 or defender_index < 0 or attacker_index >= units.size() or defender_index >= units.size() or attacker_index == defender_index:
        result_box.text = "[b]Итоги боя[/b]\nВыбери два разных подразделения."
        return
    var result := battle.resolve(units[attacker_index],units[defender_index])
    result_box.text = "[b]Итоги боя[/b]\n\n" + battle.format_result(result)
    map_renderer.document.touch()
