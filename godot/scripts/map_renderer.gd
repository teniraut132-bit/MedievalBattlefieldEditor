class_name MapRenderer
extends Node2D

signal selection_changed(index: int)
signal changed

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
const ROAD_EDGE := Color("#514437")
const ROAD_SURF := {
    "Просёлочная": Color("#b79a70"),
    "Мощенная": Color("#756b5d"),
    "Брусчаточная": Color("#897a64"),
}
const RIVER_EDGE := Color("#4d463c")
const RIVER_SURF := Color("#55aaa3")
const RIVER_HIGHLIGHT := Color("#95d0c7")

var document := MapDocument.new()
var assets := AssetLibrary.new()

var zoom: float = 0.18
var pan: Vector2 = Vector2.ZERO
var map_origin := Vector2(-4000, -2500)
var min_zoom: float = 0.08
var max_zoom: float = 3.5

var tool := "select"
var terrain_type := "Луг"
var road_type := "Просёлочная"
var brush_size := 500.0
var selected_asset := ""
var selected_index := -1
var stroke: Array[Vector2] = []
var dragging_object := false
var rotating_object := false
var rotate_start_angle := 0.0
var rotate_start_mouse := Vector2.ZERO

var _network_cache: Dictionary = {}
var _network_dirty := true
var _smoothed_cache: Dictionary = {}
var _asset_cache: Dictionary = {}
var _map_dirty := true

func _ready() -> void:
    document.changed.connect(_on_document_changed)
    _apply_view()
    get_viewport().size_changed.connect(_on_viewport_resized)
    queue_redraw()

func _on_document_changed() -> void:
    _network_dirty = true
    _map_dirty = true
    changed.emit()
    queue_redraw()

func _on_viewport_resized() -> void:
    _apply_view()
    queue_redraw()

func load_map(path: String) -> bool:
    if not document.load_json(path):
        return false
    selected_index = -1
    _network_dirty = true
    _smoothed_cache.clear()
    _apply_view()
    queue_redraw()
    return true

func save_map(path: String = "") -> bool:
    return document.save_json(path)

func reset_view() -> void:
    zoom = 0.18
    pan = Vector2.ZERO
    _apply_view()
    queue_redraw()

func set_tool(value: String) -> void:
    tool = value
    stroke.clear()
    dragging_object = false
    rotating_object = false

func set_terrain(value: String) -> void:
    if TERRAIN_STYLE.has(value):
        terrain_type = value
    set_tool("terrain")

func set_road_type(value: String) -> void:
    road_type = value
    set_tool("road")

func choose_asset(value: String) -> void:
    selected_asset = value
    set_tool("asset")

func set_brush_size(value: float) -> void:
    brush_size = clampf(value, 80.0, 1500.0)

func select_object(index: int) -> void:
    selected_index = index
    selection_changed.emit(index)
    queue_redraw()

func _apply_view() -> void:
    position = get_viewport_rect().size * 0.5 + pan
    scale = Vector2.ONE * zoom

func _process(_delta: float) -> void:
    # Godot's CanvasItem keeps the draw list cached; only mark it dirty when
    # actual map/document state changes.
    if _map_dirty:
        _map_dirty = false
        queue_redraw()

func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseMotion:
        if Input.is_mouse_button_pressed(MOUSE_BUTTON_MIDDLE):
            pan += event.relative
            _apply_view()
            get_viewport().set_input_as_handled()
            return
        if rotating_object and selected_index >= 0:
            var obj := document.object_at(selected_index)
            if not obj.is_empty():
                var center := world_to_local_mouse(rotate_start_mouse)
                var now := world_to_local_mouse(event.position)
                var a0 := rotate_start_angle
                var a1 := center.angle_to_point(now)
                obj["rotation"] = a1 - a0
                document.objects()[selected_index] = obj
                document.touch()
                get_viewport().set_input_as_handled()
                return
        if dragging_object and selected_index >= 0 and tool == "select":
            var obj := document.object_at(selected_index)
            if not obj.is_empty() and obj.get("kind","") not in ["river","road","terrain","biome","terrain_patch","landscape","biome_brush","terrain_brush"]:
                obj["x"] = to_local(event.position).x
                obj["y"] = to_local(event.position).y
                document.objects()[selected_index] = obj
                document.touch()
                get_viewport().set_input_as_handled()
                return
        if not stroke.is_empty() and tool in ["terrain","road","river"]:
            var p := world_to_local_mouse(event.position)
            if stroke.is_empty() or p.distance_to(stroke.back()) >= maxf(12.0, brush_size * 0.07):
                stroke.append(p)
                queue_redraw()
                get_viewport().set_input_as_handled()
                return

    if event is InputEventMouseButton:
        if event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
            _zoom_at_mouse(1.12)
            get_viewport().set_input_as_handled()
            return
        if event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
            _zoom_at_mouse(1.0 / 1.12)
            get_viewport().set_input_as_handled()
            return
        if event.button_index == MOUSE_BUTTON_MIDDLE:
            get_viewport().set_input_as_handled()
            return
        if event.button_index == MOUSE_BUTTON_LEFT:
            if event.pressed:
                if Input.is_key_pressed(KEY_CTRL):
                    var hit_rot := _pick_object(event.position)
                    if hit_rot >= 0:
                        select_object(hit_rot)
                        rotating_object = true
                        rotate_start_mouse = event.position
                        rotate_start_angle = world_to_local_mouse(event.position).angle_to_point(to_local(event.position))
                        # Recalculate relative to object center on first motion.
                        var obj := document.object_at(selected_index)
                        rotate_start_angle = Vector2(float(obj.get("x",0.0)),float(obj.get("y",0.0))).angle_to_point(world_to_local_mouse(event.position))
                        get_viewport().set_input_as_handled()
                        return
                if tool == "asset":
                    var place := world_to_local_mouse(event.position)
                    if not selected_asset.is_empty():
                        document.add_object({"id":document.next_id("asset"),"kind":"asset","asset":selected_asset,"x":place.x,"y":place.y,"size":180.0,"obj_scale":1.0,"rotation":0.0})
                    get_viewport().set_input_as_handled()
                    return
                if tool == "terrain":
                    stroke = [world_to_local_mouse(event.position)]
                    get_viewport().set_input_as_handled()
                    return
                if tool in ["road","river"]:
                    var p := snap_network_point(world_to_local_mouse(event.position), tool)
                    stroke = [p]
                    get_viewport().set_input_as_handled()
                    return
                if tool == "select":
                    var hit := _pick_object(event.position)
                    select_object(hit)
                    dragging_object = hit >= 0
                    get_viewport().set_input_as_handled()
                    return
            else:
                if rotating_object:
                    rotating_object = false
                    return
                if tool == "terrain" and not stroke.is_empty():
                    _finish_terrain_stroke()
                    get_viewport().set_input_as_handled()
                    return
                if tool in ["road","river"] and stroke.size() >= 2:
                    _finish_network_stroke(tool)
                    get_viewport().set_input_as_handled()
                    return
                dragging_object = false

func world_to_local_mouse(screen: Vector2) -> Vector2:
    return to_local(screen)

func _zoom_at_mouse(factor: float) -> void:
    var mouse := get_viewport().get_mouse_position()
    var before := to_local(mouse)
    zoom = clampf(zoom * factor, min_zoom, max_zoom)
    _apply_view()
    var after := to_local(mouse)
    position += (after - before) * zoom
    pan = position - get_viewport_rect().size * 0.5
    queue_redraw()

func _pick_object(screen: Vector2) -> int:
    var local := to_local(screen)
    var best := -1
    var best_d := INF
    var objects := document.objects()
    for i in range(objects.size()):
        var raw = objects[i]
        if not (raw is Dictionary):
            continue
        var o: Dictionary = raw
        var kind := str(o.get("kind",""))
        if kind in ["river","road","terrain","biome","terrain_patch","landscape","biome_brush","terrain_brush"]:
            continue
        var p := Vector2(float(o.get("x",0.0)),float(o.get("y",0.0)))
        var size := float(o.get("size",100.0))*float(o.get("obj_scale",1.0))
        var d := local.distance_to(p)
        if d <= maxf(35.0,size*0.5) and d < best_d:
            best=i;best_d=d
    return best

func snap_network_point(p: Vector2, kind: String) -> Vector2:
    var best := p
    var best_d := 140.0
    for raw in document.extract_paths(kind):
        var pts: Array[Vector2] = raw.get("points",[])
        if pts.is_empty():
            continue
        for candidate in [pts.front(),pts.back()]:
            var d := p.distance_to(candidate)
            if d < best_d:
                best_d=d
                best=candidate
    return best

func _finish_terrain_stroke() -> void:
    if stroke.size() == 1:
        stroke.append(stroke[0] + Vector2(1,0))
    var points_json: Array = []
    for p in _smooth_path(stroke):
        points_json.append([p.x,p.y])
    document.add_object({
        "id": document.next_id("terrain"),
        "kind":"terrain",
        "terrain":terrain_type,
        "points":points_json,
        "width":brush_size,
    })
    stroke.clear()
    queue_redraw()

func _finish_network_stroke(kind: String) -> void:
    var points_json: Array = []
    for p in stroke:
        points_json.append([p.x,p.y])
    var obj := {
        "id": document.next_id(kind),
        "kind":kind,
        "points":points_json,
        "width":65.0 if kind == "road" else 90.0,
    }
    if kind == "road":
        obj["road_type"]=road_type
    document.add_object(obj)
    stroke.clear()
    queue_redraw()

func _network_key(kind: String) -> String:
    return kind

func _build_network_chains(kind: String) -> Array:
    var raw_paths := document.extract_paths(kind)
    var nodes: Array[Vector2] = []
    var edges: Array = []
    const SNAP := 140.0

    func node_for(p: Vector2) -> int:
        var nearest := -1
        var dist := SNAP
        for i in range(nodes.size()):
            var d := nodes[i].distance_to(p)
            if d < dist:
                dist=d;nearest=i
        if nearest >= 0:
            nodes[nearest]=(nodes[nearest]+p)*0.5
            return nearest
        nodes.append(p)
        return nodes.size()-1

    for path_index in range(raw_paths.size()):
        var pts: Array[Vector2] = raw_paths[path_index].get("points",[])
        if pts.size()<2:
            continue
        var a := node_for(pts.front())
        var b := node_for(pts.back())
        edges.append({"a":a,"b":b,"points":pts,"width":float(raw_paths[path_index].get("width",25.0)),"road_type":str(raw_paths[path_index].get("road_type","Просёлочная"))})

    var adj: Dictionary = {}
    for i in range(nodes.size()):
        adj[i]=[]
    for e in edges:
        adj[e.a].append(e)
        adj[e.b].append(e)

    var used: Dictionary = {}
    var chains: Array = []

    func edge_id(e: Dictionary) -> int:
        return edges.find(e)

    func traverse(start_node: int, first_edge: Dictionary) -> Array[Vector2]:
        var chain: Array[Vector2] = []
        var current_node := start_node
        var edge := first_edge
        while true:
            var eid := edge_id(edge)
            if used.has(eid):
                break
            used[eid]=true
            var forward := edge.a == current_node
            var pts: Array[Vector2] = edge.points.duplicate()
            if not forward:
                pts.reverse()
            if chain.is_empty():
                chain.append_array(pts)
            else:
                if chain.back().distance_to(pts.front()) < SNAP:
                    pts[0]=chain.back()
                chain.append_array(pts.slice(1))
            current_node = edge.b if forward else edge.a
            if adj[current_node].size() != 2:
                break
            var next_edge = adj[current_node][0] if edge_id(adj[current_node][0]) != eid else adj[current_node][1]
            edge = next_edge
        return chain

    # Start chains at leaves and junctions. Every degree-2 continuation is merged.
    for node in range(nodes.size()):
        if adj[node].size() == 2:
            continue
        for e in adj[node]:
            var eid := edge_id(e)
            if used.has(eid):
                continue
            var chain := traverse(node,e)
            if chain.size()>=2:
                chains.append({"points":chain,"width":float(e.width),"road_type":str(e.road_type)})

    # Closed loops without endpoints.
    for e in edges:
        var eid:=edge_id(e)
        if used.has(eid):continue
        var chain:=traverse(e.a,e)
        if chain.size()>=2:
            chains.append({"points":chain,"width":float(e.width),"road_type":str(e.road_type)})
    return chains

func _get_network(kind: String) -> Array:
    if _network_dirty or not _network_cache.has(kind):
        _network_cache[kind]=_build_network_chains(kind)
    return _network_cache[kind]

func _draw() -> void:
    var size := document.world_size()
    draw_rect(Rect2(map_origin,size),Color("#cbbd96"),true)
    _draw_parchment_texture(size)
    _draw_biomes()
    _draw_river_network()
    _draw_road_network()
    _draw_map_border()
    _draw_objects()
    _draw_selection_overlay()
    _draw_stroke_preview()

func _draw_parchment_texture(size: Vector2) -> void:
    # Stable low-frequency texture: generated once in world space and reused.
    var step := 160.0
    for y in range(int(map_origin.y),int(map_origin.y+size.y),int(step)):
        for x in range(int(map_origin.x),int(map_origin.x+size.x),int(step)):
            var n := sin(float(x)*0.013+float(y)*0.007)*0.5+0.5
            draw_circle(Vector2(x+42.0+n*56.0,y+30.0+n*54.0),2.2,Color(0.25,0.19,0.10,0.028))

func _smooth_path(points: Array[Vector2]) -> PackedVector2Array:
    var key := str(points.hash())
    if _smoothed_cache.has(key):
        return _smoothed_cache[key]
    if points.size() <= 2:
        var simple:=PackedVector2Array(points)
        _smoothed_cache[key]=simple
        return simple
    var out:=PackedVector2Array()
    const STEPS:=7
    for i in range(points.size()-1):
        var p0:=points[max(0,i-1)]
        var p1:=points[i]
        var p2:=points[i+1]
        var p3:=points[min(points.size()-1,i+2)]
        for step in range(STEPS):
            var t:=float(step)/float(STEPS)
            var t2:=t*t
            var t3:=t2*t
            var p:=0.5*((2.0*p1)+(-p0+p2)*t+(2.0*p0-5.0*p1+4.0*p2-p3)*t2+(-p0+3.0*p1-3.0*p2+p3)*t3)
            out.append(p)
    out.append(points.back())
    _smoothed_cache[key]=out
    return out

func _draw_river_network() -> void:
    var paths:=_get_network("river")
    for item in paths:
        var p:=_smooth_path(item.points)
        var w:=maxf(4.0,float(item.width))
        draw_polyline(p,RIVER_EDGE,w+28.0,true)
    for item in paths:
        var p:=_smooth_path(item.points)
        var w:=maxf(3.0,float(item.width))
        draw_polyline(p,RIVER_SURF,w,true)
    if zoom>0.16:
        for item in paths:
            var p:=_smooth_path(item.points)
            var w:=float(item.width)
            draw_polyline(p,RIVER_HIGHLIGHT,maxf(1.5,minf(3.0,w*0.08)),true)

func _draw_road_network() -> void:
    var paths:=_get_network("road")
    for item in paths:
        var p:=_smooth_path(item.points)
        var w:=maxf(3.0,float(item.width))
        draw_polyline(p,ROAD_EDGE,w+10.0,true)
    for item in paths:
        var p:=_smooth_path(item.points)
        var w:=maxf(2.0,float(item.width))
        draw_polyline(p,ROAD_SURF.get(str(item.road_type),Color("#b79a70")),w,true)
    if zoom>0.18:
        for item in paths:
            var p:=_smooth_path(item.points)
            var w:=float(item.width)
            draw_polyline(p,Color("#d7c29b"),maxf(1.0,minf(2.0,w*0.06)),true)

func _draw_biomes() -> void:
    for raw in document.extract_terrain():
        var p:=_smooth_path(raw.points)
        var terrain:=str(raw.terrain)
        var c:Color=TERRAIN_STYLE.get(terrain,TERRAIN_STYLE["Луг"])
        var w:=maxf(18.0,float(raw.width))
        # Soft outer/inner ribbons create an organic transition rather than a hard stamp.
        draw_polyline(p,Color(c.r,c.g,c.b,0.15),w+42.0,true)
        draw_polyline(p,Color(c.r,c.g,c.b,0.30),w+18.0,true)
        draw_polyline(p,Color(c.r,c.g,c.b,0.48),w,true)
        if zoom>0.10 and zoom<2.0:
            var detail:=Color(c.r*0.80,c.g*0.80,c.b*0.80,0.12)
            draw_polyline(p,detail,w+4.0,true)

func _draw_map_border() -> void:
    var rect:=Rect2(map_origin,document.world_size())
    # Keep a minimum screen-space border so it never visually disappears on zoom.
    var width:=clampf(18.0/maxf(zoom,0.01),5.0,34.0)
    draw_rect(rect,Color("#493627"),false,width)
    draw_rect(rect.grow(-width*0.34),Color("#dbc99b"),false,maxf(2.0,width*0.14))

func _draw_objects() -> void:
    var bounds:=Rect2(map_origin,document.world_size()).grow(600.0)
    for i in range(document.objects().size()):
        var raw=document.objects()[i]
        if not (raw is Dictionary):continue
        var obj:Dictionary=raw
        var kind:=str(obj.get("kind",""))
        if kind in ["river","road","terrain","biome","terrain_patch","landscape","biome_brush","terrain_brush"]:
            continue
        var pos:=Vector2(float(obj.get("x",0.0)),float(obj.get("y",0.0)))
        if not bounds.has_point(pos):continue
        var asset_name:=str(obj.get("asset",obj.get("sprite","")))
        var tex:Texture2D=assets.texture(asset_name)
        var object_scale:=float(obj.get("obj_scale",1.0))
        var size_px:=maxf(8.0,float(obj.get("size",100.0))*object_scale)
        var rot:=float(obj.get("rotation",0.0))
        if tex:
            var dims:=tex.get_size()
            var ratio:=minf(size_px/maxf(1.0,dims.x),size_px/maxf(1.0,dims.y))
            var tex_size:=dims*ratio
            draw_set_transform(pos,rot,Vector2.ONE)
            draw_texture_rect(tex,Rect2(-tex_size*0.5,tex_size),false)
            draw_set_transform(Vector2.ZERO,0.0,Vector2.ONE)
        else:
            draw_circle(pos,maxf(12.0,size_px*0.22),Color("#7b2e28"))
            draw_arc(pos,maxf(12.0,size_px*0.22),0,TAU,24,Color("#e3b19b"),3)
            draw_string(ThemeDB.fallback_font,pos+Vector2(-7,6),"?",HORIZONTAL_ALIGNMENT_LEFT,-1,22,Color("#f6ddce"))

func _draw_selection_overlay() -> void:
    if selected_index<0 or selected_index>=document.objects().size():
        return
    var o:=document.object_at(selected_index)
    if o.is_empty():return
    var p:=Vector2(float(o.get("x",0)),float(o.get("y",0)))
    var r:=maxf(30.0,float(o.get("size",100))*float(o.get("obj_scale",1.0))*0.6)
    draw_arc(p,r,0,TAU,48,Color("#d9b76b"),3.0)

func _draw_stroke_preview() -> void:
    if stroke.size()<1:return
    var p:=_smooth_path(stroke)
    if tool=="terrain":
        var c:=TERRAIN_STYLE.get(terrain_type,TERRAIN_STYLE["Луг"])
        draw_polyline(p,Color(c.r,c.g,c.b,0.35),brush_size,true)
    elif tool=="river":
        draw_polyline(p,RIVER_SURF,maxf(3.0,90.0),true)
    elif tool=="road":
        draw_polyline(p,ROAD_SURF["Просёлочная"],maxf(3.0,65.0),true)
