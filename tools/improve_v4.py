#!/usr/bin/env python3
"""Apply NeonRush 0.4 gameplay improvements to the unpacked 0.3 Turbo project."""
from pathlib import Path
import re
path=Path("game/scripts/game.gd")
s=path.read_text(encoding="utf-8")
def replace(old,new,label):
    global s
    if old not in s:
        raise RuntimeError("0.4 patch could not find: "+label)
    s=s.replace(old,new)

# Faster boost with noticeably bigger acceleration and more forgiving jump.
replace("const DASH_SPEED = 1580.0","const DASH_SPEED = 2380.0","dash speed")
replace("const JUMP_SPEED = -1060.0","const JUMP_SPEED = -1180.0","jump speed")
replace("var scenery: Array[Dictionary] = []",
"""var scenery: Array[Dictionary] = []
var projectiles: Array[Dictionary] = []
var touch_origins: Dictionary = {}
var swipe_used: Dictionary = {}
var jump_button := Rect2(1027, 235, 216, 186)
var section_length := 6200.0""","new state")
replace("    scenery.clear()\n    p = Vector2",
        "    scenery.clear()\n    projectiles.clear()\n    touch_origins.clear()\n    swipe_used.clear()\n    p = Vector2","reset")
replace('var enemy_type := "drone" if enemy_i % 4 == 1 else "crab"',
        'var enemy_type := ["crab", "drone", "hopper", "hunter", "turret"][enemy_i % 5]','enemy variety')
replace('enemies.append({"p": Vector2(enemy_x, 410.0 if enemy_type == "drone" else 535.0),',
        'enemies.append({"p": Vector2(enemy_x, 410.0 if enemy_type == "drone" else 535.0),','enemy spawn preserved')
replace('enemy_x += rng.randf_range(780.0, 1160.0 - level * 28.0)',
        'enemy_x += rng.randf_range(605.0, 990.0 - level * 22.0)',"enemy density")
replace('var platform_y: float = [400.0, 450.0, 350.0, 415.0, 380.0][step_i % 5]',
        'var platform_y: float = 315.0 + float((step_i * 71 + (int(platform_x / 6200.0) % 3) * 51) % 175)',"platform variation")

# More punch in speed, preserving gradual analog feeling after the boost.
replace("v.x = move_toward(v.x, desired, (5200.0 if grounded else 3250.0) * dt)",
        "v.x = move_toward(v.x, desired, (9300.0 if dash_time > 0.0 else (6100.0 if grounded else 4700.0)) * dt)", "acceleration")
replace("    dash_time = 1.15", "    dash_time = 1.75", "dash duration")
replace("    dash_time = .9", "    dash_time = 1.2", "roll dash duration")
replace("    roll_time = 2.1", "    roll_time = 2.4", "roll duration")
replace('    var desired := float(axis) * (DASH_SPEED if dash_time > 0 else RUN_SPEED)',
        '    var desired := float(axis) * (DASH_SPEED if dash_time > 0 else RUN_SPEED)',"desired speed")

# Replace simplistic enemy motion with 5 distinct combat behaviors.
pos=s.index("    for k in range(enemies.size()):")
s=s[:pos] + "    _advance_enemies(dt)\n" + s[pos:]
replace('        if enemies[k]["type"] == "drone":\n            ep.y += sin(game_time * 3.0 + float(enemies[k]["phase"])) * 21',
        '        # Each enemy has already moved in _advance_enemies().',
        'remove fake drone animation')
insert=s.index("func _emit_particles(")
new_enemy_code="""func _advance_enemies(dt: float) -> void:
    # Movement and attacks are simulated only near the player; distant enemies
    # use a deterministic patrol phase so they never disappear from their lanes.
    for k in range(enemies.size()):
        if not bool(enemies[k]["alive"]):
            continue
        var enemy: Dictionary = enemies[k]
        var home: float = float(enemy["start"])
        if absf(home - p.x) > 1850.0:
            continue
        var phase: float = float(enemy["phase"])
        var kind: String = str(enemy["type"])
        var current: Vector2 = enemy["p"]
        var next_x: float = current.x
        var next_y: float = current.y
        if kind == "crab":
            next_x = home + sin(game_time * 1.65 + phase) * 105.0
            next_y = 535.0
        elif kind == "drone":
            next_x = home + sin(game_time * 1.17 + phase) * 195.0
            next_y = 395.0 + sin(game_time * 2.9 + phase) * 65.0
        elif kind == "hopper":
            next_x = home + sin(game_time * 1.3 + phase) * 90.0
            next_y = 535.0 - absf(sin(game_time * 2.35 + phase)) * 180.0
        elif kind == "hunter":
            var target_x: float = home + sin(game_time * .7 + phase) * 100.0
            if absf(p.x - home) < 650.0 and absf(p.y - current.y) < 240.0:
                target_x = p.x
            next_x = move_toward(current.x, target_x, 270.0 * dt)
            next_y = 525.0
        elif kind == "turret":
            next_x = home
            next_y = 492.0
            if absf(p.x - home) < 870.0 and game_time >= float(enemy.get("fire_at", 0.0)):
                var origin := Vector2(home, 481.0)
                var shot_dir: Vector2 = (p + Vector2(0.0, -45.0) - origin).normalized()
                projectiles.append({"p": origin, "v": shot_dir * 550.0, "life": 2.4})
                enemy["fire_at"] = game_time + 2.6 + fposmod(phase, 1.0)
        if kind != "drone" and kind != "turret" and not _is_ground_at(next_x):
            next_x = home
        enemy["p"] = Vector2(next_x, next_y)
        enemies[k] = enemy
    for n in range(projectiles.size() - 1, -1, -1):
        var shot: Dictionary = projectiles[n]
        var next_shot: Vector2 = shot["p"] + shot["v"] * dt
        shot["p"] = next_shot
        shot["life"] = float(shot["life"]) - dt
        if float(shot["life"]) < 0.0:
            projectiles.remove_at(n)
            continue
        if next_shot.distance_to(p + Vector2(0.0, -50.0)) < 38.0:
            if dash_time > 0.0 or roll_time > 0.0:
                _emit_particles(next_shot, Color(.2, .9, 1), 9)
            elif i_frames <= 0.0:
                _hurt(false)
            projectiles.remove_at(n)
            continue
        projectiles[n] = shot

"""
s=s[:insert]+new_enemy_code+s[insert:]

# Improve gesture input. The jump pad can be touched with a second finger
# while another finger keeps running; an upward swipe also works in the lower half.
start=s.index("    elif event is InputEventScreenDrag:")
end=s.index("    elif event is InputEventMouseButton", start)
s=s[:start]+"""    elif event is InputEventScreenDrag:
        if touch_origins.has(event.index) and not swipe_used.has(event.index):
            var origin: Vector2 = touch_origins[event.index]
            if origin.y - event.position.y > 68.0:
                _jump()
                swipe_used[event.index] = true
""" + s[end:]
start=s.index("func _touch_start(id: int, pos: Vector2) -> void:")
end=s.index("func _update_touch_axis() -> void:", start)
s=s[:start]+"""func _touch_start(id: int, pos: Vector2) -> void:
    if state != "game":
        _menu_tap(pos)
        return
    if pos.x > 1180.0 and pos.y < 103.0:
        state = "pause"
        queue_redraw()
        return
    touch_origins[id] = pos
    if pos.y < 195.0 or jump_button.has_point(pos):
        touch_inputs[id] = 0
        swipe_used[id] = true
        _jump()
        return
    var side := -1 if pos.x < SCREEN_W / 2.0 else 1
    touch_inputs[id] = side
    _update_touch_axis()
    var now := float(Time.get_ticks_msec()) / 1000.0
    if side == last_tap_side and now - last_tap_time < .38:
        tap_chain += 1
    else:
        tap_chain = 1
    last_tap_time = now
    last_tap_side = side
    if tap_chain == 2:
        _dash(side)
    elif tap_chain >= 3:
        _roll(side)
        tap_chain = 0

func _touch_end(id: int) -> void:
    touch_origins.erase(id)
    swipe_used.erase(id)
    top_touch_origin.erase(id)
    touch_inputs.erase(id)
    _update_touch_axis()

""" + s[end:]

# Animate each zone using an actual switch and blending between five painted backgrounds.
a=s.index("func _draw_background() -> void:")
b=s.index("func _draw_world() -> void:",a)
s=s[:a]+"""func _draw_background() -> void:
    var stage: int = int(floor(camera_x / section_length))
    var blend: float = clampf((fposmod(camera_x, section_length) - (section_length - 1500.0)) / 1500.0, 0.0, 1.0)
    var primary: Texture2D = backgrounds[(level + stage) % 5]
    var secondary: Texture2D = backgrounds[(level + stage + 1) % 5]
    var slide := fposmod(camera_x * .12, 1920.0)
    for m in range(2):
        var rect := Rect2(-slide + float(m) * 1920.0, 0.0, 1920.0, 720.0)
        draw_texture_rect(primary, rect, false)
        if blend > 0.001:
            draw_texture_rect(secondary, rect, false, Color(1,1,1,blend))
    # Different lighting each sector: day, dusk, underwater glow, night, dawn.
    var tint: Array[Color] = [
        Color(.7, .9, 1, .05), Color(1, .63, .24, .11),
        Color(.12, .64, .32, .13), Color(.06, .03, .32, .28),
        Color(.95, .47, .85, .09)
    ]
    draw_rect(Rect2(0, 0, SCREEN_W, SCREEN_H), tint[stage % 5])
    var orb_x: float = 900.0 - fposmod(camera_x * .018, 360.0)
    var orb_y: float = 115.0 + float(stage % 3) * 32.0
    draw_circle(Vector2(orb_x, orb_y), 41.0 if stage % 5 != 3 else 28.0,
        Color(1, .93, .56, .29) if stage % 5 != 3 else Color(.8,.9,1,.34))
    draw_rect(Rect2(0, 510, SCREEN_W, 210), Color(.02,.07,.15,.08))

""" + s[b:]

# Replace repeated scenery flowers with thematic biomes within each long stage.
a=s.index("    for deco in scenery:")
b=s.index("    for ring in rings:",a)
s=s[:a]+"""    for deco in scenery:
        var dx: float = float(deco["x"])
        if dx < camera_x - 180.0 or dx > camera_x + SCREEN_W + 180.0:
            continue
        var phase: float = float(deco["phase"])
        var sector: int = int(floor(dx / section_length)) % 5
        var kind: int = int(deco["kind"])
        if sector == 0: # meadow - branches, blossoms, butterflies
            draw_line(Vector2(dx,565),Vector2(dx+sin(anim_time+phase)*9.0,489),Color(.08,.42,.25),8.0,true)
            for petal in range(6):
                var theta: float = float(petal)*TAU/6.0 + phase*.1
                draw_circle(Vector2(dx+cos(theta)*18, 491+sin(theta)*18),10,Color(1,.28,.65))
            draw_circle(Vector2(dx,491),10,Color(1,.95,.31))
        elif sector == 1: # canyon / coastal palms
            draw_line(Vector2(dx,565),Vector2(dx+22,380),Color(.44,.25,.14),18.0,true)
            for frond in range(7):
                var theta: float = float(frond)*TAU/7.0
                draw_line(Vector2(dx+22,380),Vector2(dx+22+cos(theta)*78,380+sin(theta)*38),
                    Color(.12,.52,.3),16.0,true)
            draw_circle(Vector2(dx+17,385),11,Color(.8,.56,.22))
        elif sector == 2: # ancient ruins with hanging vines
            draw_rect(Rect2(dx-21,440,42,124),Color(.16,.43,.38))
            draw_rect(Rect2(dx-28,430,56,15),Color(.49,.8,.7))
            draw_rect(Rect2(dx-28,548,56,15),Color(.14,.33,.39))
            draw_line(Vector2(dx+21,437),Vector2(dx+21+sin(anim_time+phase)*15,505),
                Color(.29,.77,.28),7.0,true)
        elif sector == 3: # neon towers / circuitry
            draw_rect(Rect2(dx-26,439,52,125),Color(.04,.09,.31))
            draw_rect(Rect2(dx-26,440,52,6),Color(.14,.95,1,.7))
            for light in range(4):
                draw_rect(Rect2(dx-16,455+light*24,10,10),Color(.12,.95,1,.7))
                draw_rect(Rect2(dx+6,455+light*24,10,10),Color(1,.23,.68,.8))
        else: # sky crystals / floating luminous shards
            var float_y: float = sin(anim_time*2.0+phase)*8.0
            draw_colored_polygon(PackedVector2Array([
                Vector2(dx-35,540+float_y),Vector2(dx,409+float_y),
                Vector2(dx+30,540+float_y),Vector2(dx,564+float_y)
            ]),Color(.48,.73,1,.65))
            draw_line(Vector2(dx,420+float_y),Vector2(dx,548+float_y),
                Color(.96,1,1,.8),5.0,true)
    for shot in projectiles:
        var sp: Vector2 = shot["p"]
        if absf(sp.x - (camera_x + SCREEN_W / 2.0)) < 850.0:
            draw_circle(sp, 13.0, Color(1,.24,.43,.72))
            draw_circle(sp, 7.0, Color(1,.96,.54))
""" + s[b:]

# Enemy illustration tint and animated rotor/face detail, plus projectile rendering.
replace("""        var dy := sin(game_time * 3.0 + float(ent["phase"])) * 21 if ent["type"] == "drone" else 0.0
        var tex: Texture2D = objects[ent["type"]]
        draw_texture_rect(tex,Rect2(ep.x-46,ep.y-52+dy,92,82),false)""",
"""        var kind: String = str(ent["type"])
        var tex: Texture2D = objects["drone" if kind in ["drone", "turret"] else "crab"]
        var tint := Color(1,1,1)
        if kind == "hopper":
            tint = Color(1,.79,.28)
        elif kind == "hunter":
            tint = Color(1,.31,.42)
        elif kind == "turret":
            tint = Color(.73,.36,1)
        elif kind == "drone":
            tint = Color(.54,1,1)
        draw_texture_rect(tex, Rect2(ep.x-47,ep.y-54,94,84), false, tint)
        if kind == "drone":
            draw_arc(ep+Vector2(0,-50), 32, game_time*5, game_time*5+PI, 18, Color(.15,1,1), 3, true)
        elif kind == "turret":
            draw_circle(ep + Vector2(0,-30), 9.0+sin(anim_time*5.0)*2.0,Color(1,.2,.66))
        elif kind == "hunter":
            draw_line(ep+Vector2(-14,-25),ep+Vector2(14,-25),Color(1,.11,.13),5)""",
"enemy rendering")
replace("        _text(\"ВЕРХ — ПРЫЖОК\",655,682,20,Color.WHITE,true)",
"""        _pill(jump_button, Color(.10,.71,.95,.55), Color(.96,1,1,.8), 48)
        _text("↑ ПРЫЖОК", jump_button.position.x + jump_button.size.x/2.0,
            jump_button.position.y + 104.0, 30, Color.WHITE, true)
        _text("↑ СВАЙП — ПРЫЖОК",655,682,20,Color.WHITE,true)""", "jump pad HUD")

# Indicator of zone variety and boost in HUD.
replace('    if notice_time > 0:\n        _pill',
"""    if dash_time > 0.0:
        _pill(Rect2(880,18,260,68),Color(.03,.35,.47,.9),Color(.43,1,.85,.85),18)
        _text("ТУРБО ×%.1f" % (DASH_SPEED/RUN_SPEED),1010,62,27,Color(.7,1,.9),true)
    if notice_time > 0:
        _pill""","boost HUD")

path.write_text(s,encoding="utf-8")
print("Gameplay v0.4: jump zone/swipe, boost, five enemy behaviours, projectiles and sector biomes.")
