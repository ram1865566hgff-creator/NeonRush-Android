#!/usr/bin/env python3
"""NeonRush v0.3 upgrade. Applied to the existing game.zip by GitHub Actions.
Creates higher-detail, original vector character art and upgrades level/physics code.
"""
from pathlib import Path
import re, math

root = Path("game")
gd = root / "scripts/game.gd"
pr = root / "project.godot"
assert gd.exists() and pr.exists(), "Unpack game.zip before applying upgrade"

p = pr.read_text(encoding="utf-8")
p = p.replace("window/handheld/orientation=1", "window/handheld/orientation=4")
p = p.replace('config/name="Неоновый рывок"', 'config/name="Неоновый рывок: Турбо"')
p = p.replace('config/description="Пять красочных миров: оригинальная мобильная 2D-аркада"', 'config/description="Пять длинных уровней, динамичный бег и обновлённая графика"')
pr.write_text(p, encoding="utf-8")

s = gd.read_text(encoding="utf-8")
def sub(old, new):
    global s
    assert old in s, "Expected source text not found: " + old[:100]
    s = s.replace(old, new)

sub("const WORLD_W = 3750.0", "const WORLD_W = 85000.0")
sub("const GRAVITY = 1720.0", "const GRAVITY = 2250.0")
sub("const RUN_SPEED = 370.0", "const RUN_SPEED = 890.0")
sub("const DASH_SPEED = 680.0", "const DASH_SPEED = 1580.0")
sub("const JUMP_SPEED = -760.0", "const JUMP_SPEED = -1060.0")
sub("var platforms: Array[Rect2] = []",
    "var level_end := 42000.0\nvar air_jumps := 1\nvar platforms: Array[Rect2] = []\nvar scenery: Array[Dictionary] = []")

sub("for n in [\"idle\", \"run_0\", \"run_1\", \"run_2\", \"run_3\", \"jump\", \"roll\"]:\n        hero[n] = load(\"res://assets/characters/%s.png\" % n)",
    'for n in ["idle", "run_0", "run_1", "run_2", "run_3", "run_4", "run_5", "run_6", "run_7", "jump", "roll"]:\n        hero[n] = load("res://assets/deluxe/%s.svg" % n)')
sub('    _load_save()\n    _build_level(0)', '    if OS.has_feature("mobile"):\n        DisplayServer.screen_set_orientation(DisplayServer.SCREEN_SENSOR_LANDSCAPE)\n    _load_save()\n    _build_level(0)')

start=s.index("func _build_level(index: int) -> void:")
stop=s.index("func _add_ring(pos: Vector2) -> void:", start)
new_level = """func _build_level(index: int) -> void:
    level = clampi(index, 0, 4)
    level_end = 42000.0 + float(level) * 8500.0
    platforms.clear()
    rings.clear()
    enemies.clear()
    springs.clear()
    checkpoints.clear()
    particles.clear()
    scenery.clear()
    p = Vector2(155.0, 565.0)
    respawn = p
    v = Vector2.ZERO
    grounded = true
    air_jumps = 1
    facing = 1
    rings_count = 0
    score = 0
    game_time = 0.0
    dash_time = 0.0
    roll_time = 0.0
    camera_x = 0.0
    input_direction = 0
    touch_inputs.clear()
    top_touch_origin.clear()
    var rng := RandomNumberGenerator.new()
    rng.seed = 9331 + level * 703

    # Fully authored-length procedural course: multiple sectors, safe ground,
    # short jumpable gaps, aerial routes, collectibles and frequent checkpoints.
    var section_start := 0.0
    while section_start < level_end:
        var ground_end: float = minf(level_end, section_start + rng.randf_range(1950.0, 3000.0))
        platforms.append(Rect2(section_start, 565.0, ground_end - section_start, 175.0))
        if ground_end >= level_end:
            break
        var gap_width: float = rng.randf_range(150.0, 235.0 + level * 15.0)
        # Reward a good jump with a ring bridge across each gap.
        for z in range(5):
            var ax: float = ground_end + 12.0 + float(z) * (gap_width / 5.0)
            _add_ring(Vector2(ax, 405.0 - sin(float(z) / 4.0 * PI) * 65.0))
        section_start = ground_end + gap_width

    # Aerial routes, with gentle variation in height and width.
    var platform_x := 400.0
    var step_i := 0
    while platform_x < level_end - 300.0:
        var platform_y: float = [400.0, 450.0, 350.0, 415.0, 380.0][step_i % 5]
        var platform_w: float = rng.randf_range(205.0, 310.0)
        platforms.append(Rect2(platform_x, platform_y, platform_w, 46.0))
        for z in range(5):
            _add_ring(Vector2(platform_x + 27.0 + z * (platform_w - 54.0) / 4.0, platform_y - 55.0))
        platform_x += rng.randf_range(570.0, 820.0)
        step_i += 1

    # Animated rings lead players through the world.
    var ring_x := 240.0
    while ring_x < level_end - 250.0:
        var ring_y: float = 492.0 - sin(ring_x * 0.009) * (46.0 + level * 5.0)
        if not _is_ground_at(ring_x):
            ring_y = 375.0
        _add_ring(Vector2(ring_x, ring_y))
        ring_x += rng.randf_range(92.0, 141.0)

    var enemy_x := 800.0
    var enemy_i := 0
    while enemy_x < level_end - 500.0:
        if _is_ground_at(enemy_x):
            var enemy_type := "drone" if enemy_i % 4 == 1 else "crab"
            enemies.append({"p": Vector2(enemy_x, 410.0 if enemy_type == "drone" else 535.0),
                "start": enemy_x, "phase": float(enemy_i), "type": enemy_type, "alive": true})
        enemy_x += rng.randf_range(780.0, 1160.0 - level * 28.0)
        enemy_i += 1

    var spring_x := 1200.0
    while spring_x < level_end - 500.0:
        while spring_x < level_end - 500.0 and not _is_ground_at(spring_x):
            spring_x += 95.0
        if spring_x < level_end - 500.0:
            springs.append(Vector2(spring_x, 545.0))
        spring_x += rng.randf_range(3500.0, 5100.0)

    var cp_x := 6200.0
    while cp_x < level_end - 1200.0:
        while cp_x < level_end - 1200.0 and not _is_ground_at(cp_x):
            cp_x += 100.0
        checkpoints.append({"x": cp_x, "used": false})
        cp_x += 6200.0

    var scenery_x := 350.0
    var deco_i := 0
    while scenery_x < level_end:
        if _is_ground_at(scenery_x):
            scenery.append({"x": scenery_x, "kind": deco_i % 4, "phase": rng.randf_range(0.0, TAU)})
        scenery_x += rng.randf_range(285.0, 520.0)
        deco_i += 1

    notification = "МИР %d — %s  •  ТУРБО!" % [level + 1, NAMES[level]]
    notice_time = 3.1

"""
s=s[:start]+new_level+s[stop:]

sub("v.x = move_toward(v.x, desired, (1700.0 if grounded else 850.0) * dt)",
    "v.x = move_toward(v.x, desired, (5200.0 if grounded else 3250.0) * dt)")
sub("v.y = minf(1050.0, v.y + GRAVITY * dt)",
    "v.y = minf(1650.0, v.y + (GRAVITY * (0.78 if v.y < 0.0 else 1.22)) * dt)")
sub("p.x = clampf(p.x, 30, WORLD_W - 60.0)",
    "p.x = clampf(p.x, 30.0, level_end - 60.0)")
sub("                    grounded = true\n                    break",
    "                    grounded = true\n                    air_jumps = 1\n                    break")
sub("if p.x > WORLD_W - 190.0:", "if p.x > level_end - 190.0:")
sub("camera_x = clampf(p.x - 375.0, 0, WORLD_W - SCREEN_W)",
    "var camera_target: float = clampf(p.x - (400.0 if facing == 1 else 860.0), 0.0, level_end - SCREEN_W)\n    camera_x = lerpf(camera_x, camera_target, minf(1.0, dt * 6.0))")
sub("    if state == \"game\" and (grounded or jump_cooldown > 0 and v.y > 0 and v.y < 100):\n        v.y = JUMP_SPEED",
    "    if state == \"game\" and (grounded or air_jumps > 0):\n        if not grounded:\n            air_jumps -= 1\n        v.y = JUMP_SPEED")
sub("    dash_time = .85", "    dash_time = 1.15")
sub("    roll_time = 2.3", "    roll_time = 2.1")
sub("    dash_time = .7", "    dash_time = .9")
sub("    var portal_x := WORLD_W - 130", "    var portal_x := level_end - 130.0")
sub('sprite = hero["run_%d" % (int(anim_time*11) % 4)]',
    'sprite = hero["run_%d" % (int(anim_time * (12.0 + absf(v.x) * 0.014)) % 8)]')
sub("        var sprite_sz := Vector2(106,108) if roll_time > 0 else Vector2(123,135)\n        draw_set_transform(Vector2(p.x-camera_x, p.y-18), 0, Vector2(float(facing),1))",
    """        var sprite_sz := Vector2(128, 128) if roll_time > 0 else Vector2(170, 168)
        var lean: float = -float(facing) * minf(.19, absf(v.x) / DASH_SPEED * .19)
        var bob: float = (sin(anim_time * 24.0) * 4.0) if grounded and absf(v.x) > 80 else 0.0
        var stretch_y: float = 1.07 if not grounded and v.y < 0 else 1.0
        draw_set_transform(Vector2(p.x-camera_x, p.y-19+bob), lean if grounded else 0.0,
            Vector2(float(facing), stretch_y))""")

# More speed feedback: streaks and sparks behind the real character.
sub('    if i_frames <= 0 or int(anim_time*14)%2 == 0:',
"""    if absf(v.x) > 580.0:
        var streak_intensity: float = clampf(absf(v.x) / DASH_SPEED, 0.0, 1.0)
        for streak in range(7):
            var sy: float = p.y - 18.0 - float(streak) * 15.0
            var length: float = 55.0 + float(streak % 3) * 43.0 + streak_intensity * 105.0
            var from := Vector2(p.x - facing * (28.0 + length), sy)
            var to := Vector2(p.x - facing * 37.0, sy + sin(anim_time * 7.0 + streak) * 4.0)
            draw_line(from, to, Color(.19,.95,1.0,.16 + .26 * streak_intensity), 1.5 + streak_intensity * 2.3, true)
    if i_frames <= 0 or int(anim_time*14)%2 == 0:""")

# More vibrant scenery cues, ground flowers, crystals and sparks that match each world.
sub('    for ring in rings:\n        if not ring["taken"]:',
"""    for deco in scenery:
        var dx: float = float(deco["x"])
        if dx < camera_x - 160.0 or dx > camera_x + SCREEN_W + 160.0:
            continue
        var phase: float = float(deco["phase"])
        if level <= 2:
            draw_line(Vector2(dx,565), Vector2(dx+sin(anim_time*1.4+phase)*10.0,501), Color(.10,.34,.22), 7.0)
            for f in range(5):
                var theta: float = float(f)*TAU/5.0+anim_time*.14+phase
                draw_circle(Vector2(dx+cos(theta)*16.0,497+sin(theta)*16.0),9.0,
                    Color(.98,.27,.61) if level==0 else Color(.9,.64,.24))
            draw_circle(Vector2(dx,497),7.0,Color(1,.89,.39))
        elif level == 3:
            draw_colored_polygon(PackedVector2Array([Vector2(dx-21,565),Vector2(dx+4,494),Vector2(dx+24,565)]),
                Color(.04,.87,1.0,.65))
            draw_line(Vector2(dx+4,500),Vector2(dx+4,553),Color(1,.2,.9,.8),4.0)
        else:
            var shimmer: float = sin(anim_time*3.0+phase)*4.0
            draw_colored_polygon(PackedVector2Array([Vector2(dx-20,556),Vector2(dx,480+shimmer),Vector2(dx+20,556)]),
                Color(.52,.74,1,.65))
            draw_circle(Vector2(dx,485+shimmer),5.0,Color(1,1,1,.85))
    for ring in rings:
        if not ring["taken"]:""")

# Camera and title remain in world dimensions; foreground accent.
gd.write_text(s, encoding="utf-8")

# Detailed original blue "Aurora Fox" with amber visor, cyan fur, two glowing tails.
# All poses share one rig; changing feet, forearms and tail curves creates fluid run cycles.
out = root / "assets/deluxe"
out.mkdir(parents=True, exist_ok=True)

def sprite(pose: str, frame: int = 0) -> str:
    t = frame * math.pi / 4
    jump = pose == "jump"
    roll = pose == "roll"
    fast = pose == "run"
    swing = math.sin(t) * 30 if fast else 0
    lift = math.cos(t) * 20 if fast else 0
    if jump:
        swing, lift = -31, 35
    bg = '''<defs>
<linearGradient id="fur" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#8afcff"/><stop offset=".32" stop-color="#11c9f2"/><stop offset=".75" stop-color="#0576d4"/><stop offset="1" stop-color="#172f91"/></linearGradient>
<linearGradient id="fur2" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#a5ffff"/><stop offset=".6" stop-color="#18b3fa"/><stop offset="1" stop-color="#063779"/></linearGradient>
<linearGradient id="shoe" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff7ec"/><stop offset=".55" stop-color="#fa494e"/><stop offset="1" stop-color="#94155c"/></linearGradient>
<linearGradient id="visor" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff7b6"/><stop offset=".44" stop-color="#ffa531"/><stop offset="1" stop-color="#d93c7f"/></linearGradient>
<radialGradient id="glow"><stop stop-color="#2efcff" stop-opacity=".85"/><stop offset="1" stop-color="#1b9aff" stop-opacity="0"/></radialGradient>
</defs>'''
    if roll:
        body = '''<circle cx="155" cy="163" r="110" fill="url(#glow)"/>
<circle cx="155" cy="162" r="81" fill="url(#fur)" stroke="#0d297a" stroke-width="8"/>
<path d="M 105,100 Q 175,94 213,157 Q 213,218 158,238" fill="none" stroke="#9bfeff" stroke-width="16" stroke-linecap="round"/>
<path d="M 155,84 Q 97,135 108,191 M 199,113 Q 180,157 143,210" fill="none" stroke="#07317e" stroke-width="14" stroke-linecap="round"/>
<path d="M 125,105 L 138,80 L 153,110" fill="#fff7a5"/>
<path d="M 93,191 Q 142,219 196,192" fill="none" stroke="#71efff" stroke-width="8"/>
<ellipse cx="151" cy="155" rx="27" ry="19" fill="url(#visor)" transform="rotate(-18 151 155)"/>'''
    else:
        # Back tails, back limbs, body, front limbs, head, face, and speed accents.
        body = f'''
<!-- two luminous tails -->
<path d="M119 196 Q58 {150+lift/4:.1f} 16 214 Q50 190 84 231 Q40 260 25 249 Q78 291 131 240Z" fill="url(#fur2)" stroke="#07488a" stroke-width="5"/>
<path d="M115 207 Q45 172 28 154 Q66 161 88 194 Q46 202 37 217 Q100 231 140 225Z" fill="#27dfff" stroke="#0a3f85" stroke-width="4"/>
<path d="M40 193 Q62 197 79 217" fill="none" stroke="#c8ffff" stroke-width="7" stroke-linecap="round"/>
<!-- legs with distinct running poses -->
<g transform="translate(143 236) rotate({-swing*.8:.1f})">
<path d="M-9 -3 Q-20 18 -25 35 L-8 48 L18 7 Z" fill="#064f9d" stroke="#10357b" stroke-width="5"/>
<g transform="translate(-16 42) rotate({-lift*.4:.1f})">
<path d="M-24 -17 Q2 -30 34 -16 L46 7 Q14 23 -31 12Z" fill="url(#shoe)" stroke="#451e67" stroke-width="6"/>
<path d="M-26 7 Q5 18 45 4" fill="none" stroke="white" stroke-width="8" stroke-linecap="round"/>
<path d="M2 -13 L14 -13 M5 -5 L19 -7" stroke="#fff4db" stroke-width="4"/>
</g></g>
<g transform="translate(174 237) rotate({swing:.1f})">
<path d="M-14 0 Q-8 19 0 40 L26 40 L13 -4Z" fill="url(#fur)" stroke="#06357e" stroke-width="6"/>
<g transform="translate(0 38) rotate({lift*.5:.1f})">
<path d="M-28 -16 Q1 -29 40 -15 L51 6 Q22 25 -29 12Z" fill="url(#shoe)" stroke="#451e67" stroke-width="6"/>
<path d="M-27 7 Q13 17 49 3" fill="none" stroke="white" stroke-width="8" stroke-linecap="round"/>
<path d="M1 -12 L21 -12 M3 -5 L24 -5" stroke="#fff4db" stroke-width="4"/>
</g></g>
<!-- torso and lightning bolt chest -->
<path d="M133 180 Q162 166 194 191 Q211 229 184 258 Q146 273 125 242Z" fill="url(#fur)" stroke="#063978" stroke-width="7"/>
<path d="M154 190 Q185 184 192 209 Q195 233 173 247 Q141 241 144 215Z" fill="#ebfdff"/>
<path d="M176 193 L159 221 L174 219 L163 239 L187 210 L172 212Z" fill="#ffbd32"/>
<!-- left arm -->
<g transform="translate(144 193) rotate({-swing*.65-18:.1f})">
<path d="M0 0 Q-18 12 -27 48" fill="none" stroke="#0754a4" stroke-width="22" stroke-linecap="round"/>
<path d="M-39 48 Q-38 28 -19 29 Q-3 30 -7 53 Q-18 74 -35 65Z" fill="#fffaf3" stroke="#47617f" stroke-width="5"/>
<path d="M-33 42 L-14 44" stroke="#c2e5f6" stroke-width="4"/>
</g>
<!-- front arm -->
<g transform="translate(188 197) rotate({swing*.85+20:.1f})">
<path d="M0 0 Q27 14 24 42" fill="none" stroke="#063f94" stroke-width="21" stroke-linecap="round"/>
<path d="M13 34 Q35 16 44 35 Q54 58 30 69 Q5 63 13 34Z" fill="#fffef2" stroke="#375e8d" stroke-width="5"/>
<path d="M20 38 Q32 37 41 44" stroke="#c2e5f6" stroke-width="4"/>
</g>
<!-- unmistakable fox head with upright ears -->
<path d="M144 140 L124 47 Q148 58 168 95 L202 28 Q229 62 220 123" fill="url(#fur)" stroke="#11366e" stroke-width="7" stroke-linejoin="round"/>
<path d="M144 115 L137 70 Q157 94 164 117 M192 94 L201 52 Q214 73 210 101" fill="#ffabbd"/>
<path d="M107 143 Q113 96 176 91 Q238 93 253 142 Q256 191 206 205 Q150 226 116 191 Q95 172 107 143Z" fill="url(#fur)" stroke="#0b3880" stroke-width="8"/>
<path d="M113 168 Q88 175 87 203 L124 196 M225 178 Q251 180 256 199 L214 192" fill="#76e8ff" stroke="#0c5da5" stroke-width="5"/>
<!-- warm gold visor, original mascot feature -->
<path d="M126 135 Q166 112 224 127 L243 147 Q225 166 161 160 Q135 154 126 135Z" fill="url(#visor)" stroke="#713572" stroke-width="5"/>
<path d="M142 132 Q180 118 216 132" fill="none" stroke="#fffed5" stroke-width="6" stroke-linecap="round" opacity=".9"/>
<ellipse cx="214" cy="153" rx="16" ry="21" fill="#ffffff"/>
<ellipse cx="221" cy="157" rx="7" ry="15" fill="#082954"/>
<ellipse cx="224" cy="151" rx="3" ry="5" fill="#ffffff"/>
<path d="M193 173 Q235 161 239 188 Q212 216 175 191Z" fill="#e7ffff"/>
<ellipse cx="238" cy="182" rx="10" ry="8" fill="#13366a"/>
<path d="M201 191 Q218 204 231 192" fill="none" stroke="#1c3968" stroke-width="4" stroke-linecap="round"/>
<!-- frosted stripe crown -->
<path d="M121 129 Q141 104 181 105" stroke="#b8ffff" stroke-width="8" fill="none" stroke-linecap="round"/>
'''
        if jump:
            body += '<path d="M171 240 Q154 269 186 278" fill="none" stroke="#a7fbff" stroke-width="7"/>'
    result = f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 320 320">{bg}{body}</svg>'
    return result

for i in range(8):
    (out/f"run_{i}.svg").write_text(sprite("run", i), encoding="utf-8")
for name in ["idle", "jump", "roll"]:
    (out/f"{name}.svg").write_text(sprite(name), encoding="utf-8")

print("Applied NeonRush Turbo upgrade: original animated vector fox, 5 extended worlds, speed, camera, jumping, and autorotation.")
