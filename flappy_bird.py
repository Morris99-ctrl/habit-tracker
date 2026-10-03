# ══════════════════════════════════════════════════════════════════════════════
#  Flappy Bird Deluxe  –  Realistic, Alive & Polished
#  Requires: pygame-ce  (pip install pygame-ce)
# ══════════════════════════════════════════════════════════════════════════════

import pygame
import random
import math
import json
import os
import array

# ─────────────────────────────────────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────────────────────────────────────
WIDTH, HEIGHT      = 480, 700
FPS                = 60
PIPE_GAP           = 190
PIPE_SPAWN_DIST    = 210
GROUND_H           = 80
SKY_H              = HEIGHT - GROUND_H

# ── Difficulty scaling (start easy → ramp to max at score DIFF_MAX_SCORE) ───
DIFF_MAX_SCORE   = 30      # score at which difficulty fully peaks
GRAVITY_START    = 0.20    # gentle fall at the beginning
GRAVITY_MAX      = 0.50    # full gravity once experienced
FLAP_START       = -6.5    # a comfortable jump early on
FLAP_MAX         = -10.0   # snappier, harder flap at high scores
PIPE_SPEED_START = 2.0     # relaxed pipe speed at start
PIPE_SPEED_MAX   = 5.2     # fast pace at high scores

def get_difficulty(score: int) -> tuple[float, float, float]:
    """Return (gravity, flap_strength, pipe_speed) scaled to current score."""
    t = min(1.0, score / DIFF_MAX_SCORE)   # 0.0 (easy) → 1.0 (max)
    gravity     = GRAVITY_START    + t * (GRAVITY_MAX    - GRAVITY_START)
    flap        = FLAP_START       + t * (FLAP_MAX       - FLAP_START)
    pipe_speed  = PIPE_SPEED_START + t * (PIPE_SPEED_MAX - PIPE_SPEED_START)
    return gravity, flap, pipe_speed

HIGHSCORE_FILE     = os.path.join(os.path.dirname(__file__), "flappy_highscore.json")

# ─────────────────────────────────────────────────────────────────────────────
#  Colour Palette
# ─────────────────────────────────────────────────────────────────────────────
SKY_TOP    = (  30,  90, 200)
SKY_BOT    = ( 140, 210, 255)
GROUND_COL = (  85,  55,  30)
GRASS_TOP  = (  50, 180,  40)
GRASS_MID  = (  35, 140,  30)
GRASS_BOT  = (  20, 100,  20)

PIPE_BASE  = (  40, 160,  40)
PIPE_LIGHT = ( 100, 220,  90)
PIPE_DARK  = (  15,  80,  15)
PIPE_SPEC  = ( 200, 255, 180)
PIPE_FLANGE= (  55, 180,  55)
PIPE_RIM   = (  25,  90,  25)

BIRD_BODY  = (255, 210,   0)
BIRD_BELLY = (255, 240, 140)
BIRD_WING  = (220, 170,   0)
BIRD_EYE   = (255, 255, 255)
BIRD_PUPIL = (  0,   0,   0)
BIRD_BEAK  = (255, 130,   0)

WHITE      = (255, 255, 255)
BLACK      = (  0,   0,   0)
GOLD       = (255, 215,   0)
SILVER     = (192, 192, 192)
BRONZE     = (205, 127,  50)
PLATINUM   = (220, 240, 255)


# ─────────────────────────────────────────────────────────────────────────────
#  Utility helpers
# ─────────────────────────────────────────────────────────────────────────────
def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def sc(r, g, b):
    """Safe colour – clamp all channels to [0, 255] for pygame."""
    return (clamp(int(r), 0, 255), clamp(int(g), 0, 255), clamp(int(b), 0, 255))


# ─────────────────────────────────────────────────────────────────────────────
#  Procedural Sound Manager
# ─────────────────────────────────────────────────────────────────────────────
class SoundManager:
    RATE = 22050

    def __init__(self):
        try:
            pygame.mixer.init(frequency=self.RATE, size=-16, channels=1, buffer=512)
            self._sounds = {
                "flap":  self._make_flap(),
                "score": self._make_score(),
                "hit":   self._make_hit(),
                "die":   self._make_die(),
            }
            self.ok = True
        except Exception:
            self.ok = False

    # ── waveform helpers ──────────────────────────────────────────────────────
    def _buf(self, samples):
        return array.array("h", [clamp(int(s), -32768, 32767) for s in samples])

    def _sine(self, freq, dur, vol=8000, decay=True):
        n = int(self.RATE * dur)
        env = [math.exp(-4 * i / n) if decay else 1.0 for i in range(n)]
        return [vol * env[i] * math.sin(2 * math.pi * freq * i / self.RATE) for i in range(n)]

    def _noise(self, dur, vol=4000):
        n = int(self.RATE * dur)
        return [vol * (random.random() * 2 - 1) * math.exp(-6 * i / n) for i in range(n)]

    def _mix(self, *waves):
        length = max(len(w) for w in waves)
        out = [0.0] * length
        for w in waves:
            for i, s in enumerate(w):
                out[i] += s
        return out

    # ── individual sounds ─────────────────────────────────────────────────────
    def _make_flap(self):
        w = self._mix(
            self._sine(440, 0.07, 5000),
            self._sine(660, 0.05, 3000),
        )
        snd = pygame.sndarray.make_sound(self._buf(w))
        snd.set_volume(0.4)
        return snd

    def _make_score(self):
        w = self._mix(
            self._sine(880, 0.12, 6000),
            self._sine(1100, 0.10, 4000),
        )
        snd = pygame.sndarray.make_sound(self._buf(w))
        snd.set_volume(0.5)
        return snd

    def _make_hit(self):
        w = self._mix(
            self._sine(180, 0.10, 7000),
            self._noise(0.10, 6000),
        )
        snd = pygame.sndarray.make_sound(self._buf(w))
        snd.set_volume(0.6)
        return snd

    def _make_die(self):
        n = int(self.RATE * 0.4)
        w = [5000 * math.exp(-3 * i / n) * math.sin(
            2 * math.pi * (600 - 400 * i / n) * i / self.RATE) for i in range(n)]
        snd = pygame.sndarray.make_sound(self._buf(w))
        snd.set_volume(0.5)
        return snd

    def play(self, name):
        if self.ok and name in self._sounds:
            self._sounds[name].stop()
            self._sounds[name].play()


# ─────────────────────────────────────────────────────────────────────────────
#  Particle System
# ─────────────────────────────────────────────────────────────────────────────
class Particle:
    __slots__ = ["x", "y", "vx", "vy", "life", "max_life", "color", "size", "kind"]

    def __init__(self, x, y, vx, vy, life, color, size, kind="circle"):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = size
        self.kind = kind

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.18
        self.vx *= 0.97
        self.life -= 1

    def draw(self, surf):
        alpha = self.life / self.max_life
        r, g, b = self.color
        col = (int(r * alpha), int(g * alpha), int(b * alpha))
        sz  = max(1, int(self.size * alpha))
        if self.kind == "feather":
            end_x = int(self.x + self.vx * 3)
            end_y = int(self.y + self.vy * 3)
            pygame.draw.line(surf, col, (int(self.x), int(self.y)), (end_x, end_y), sz)
        else:
            pygame.draw.circle(surf, col, (int(self.x), int(self.y)), sz)


class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []

    def emit_flap(self, x, y):
        for _ in range(5):
            vx = random.uniform(-2.5, -0.5)
            vy = random.uniform(-1.0,  1.0)
            col = random.choice([WHITE, (200, 240, 255)])
            self.particles.append(Particle(x, y, vx, vy, random.randint(10, 20), col, random.uniform(2, 5)))

    def emit_score(self, x, y):
        for _ in range(14):
            ang = random.uniform(0, math.pi * 2)
            spd = random.uniform(1.5, 4.5)
            self.particles.append(Particle(x, y, math.cos(ang)*spd, math.sin(ang)*spd,
                                           random.randint(20, 40), GOLD, random.uniform(3, 6)))

    def emit_death(self, x, y):
        for _ in range(22):
            ang  = random.uniform(0, math.pi * 2)
            spd  = random.uniform(2.0, 6.0)
            col  = random.choice([BIRD_BODY, BIRD_WING, BIRD_BELLY, WHITE])
            self.particles.append(Particle(x, y, math.cos(ang)*spd, math.sin(ang)*spd,
                                           random.randint(25, 55), col,
                                           random.uniform(2, 4), "feather"))

    def emit_ground_dust(self, x, y):
        for _ in range(8):
            vx = random.uniform(-3, 3)
            vy = random.uniform(-3, -0.5)
            col = (180, 140, 80)
            self.particles.append(Particle(x, y, vx, vy, random.randint(12, 25), col, random.uniform(2, 5)))

    def update_and_draw(self, surf):
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.update()
            p.draw(surf)


# ─────────────────────────────────────────────────────────────────────────────
#  Gradient Sky + Parallax Background
# ─────────────────────────────────────────────────────────────────────────────
class Background:
    def __init__(self, width, height, ground_h):
        self.W, self.H, self.GH = width, height, ground_h
        self.sky_surf  = self._make_sky()
        self.cloud_surf= pygame.Surface((width * 3, height), pygame.SRCALPHA)
        self.clouds    = [self._new_cloud(random.randint(0, width * 3)) for _ in range(14)]
        self.scroll    = [0.0, 0.0, 0.0, 0.0]   # 4 parallax layers
        self.trees     = self._generate_trees()
        self.bushes    = self._generate_bushes()
        self.ground_x  = 0.0
        self.tile_w    = width

    # ── sky gradient ──────────────────────────────────────────────────────────
    def _make_sky(self):
        surf = pygame.Surface((self.W, self.H - self.GH))
        for y in range(self.H - self.GH):
            t = y / (self.H - self.GH)
            col = lerp_color(SKY_TOP, SKY_BOT, t)
            pygame.draw.line(surf, col, (0, y), (self.W, y))
        return surf

    # ── cloud helper ──────────────────────────────────────────────────────────
    def _new_cloud(self, x=None):
        w = random.randint(70, 170)
        h = random.randint(30, 55)
        y = random.randint(20, int((self.H - self.GH) * 0.45))
        if x is None:
            x = self.W + w
        return {"x": float(x), "y": y, "w": w, "h": h,
                "speed": random.uniform(0.2, 0.55),
                "alpha": random.randint(160, 240)}

    def _draw_cloud(self, surf, c):
        s = pygame.Surface((c["w"] + 40, c["h"] + 20), pygame.SRCALPHA)
        col = (*WHITE, c["alpha"])
        # draw puffs
        for ox, oy, r in [(0, 10, c["h"]//2),
                          (c["w"]//3, 0, int(c["h"] * 0.65)),
                          (c["w"]*2//3, 5, c["h"]//2),
                          (c["w"], 12, c["h"]//3)]:
            pygame.draw.ellipse(s, col, (ox, oy, r*2, int(r*1.3)))
        surf.blit(s, (int(c["x"]), c["y"]))

    # ── vegetation ────────────────────────────────────────────────────────────
    def _generate_trees(self):
        trees = []
        x = 0
        while x < self.W * 2:
            h = random.randint(55, 110)
            w_trunk = random.randint(8, 14)
            trees.append({"x": float(x), "h": h, "wt": w_trunk,
                          "shade": random.randint(-20, 20)})
            x += random.randint(55, 130)
        return trees

    def _generate_bushes(self):
        bushes = []
        x = 0
        while x < self.W * 2:
            r = random.randint(14, 28)
            bushes.append({"x": float(x), "r": r,
                           "shade": random.randint(-15, 15)})
            x += random.randint(28, 75)
        return bushes

    def _draw_tree(self, surf, x, h, wt, shade, gnd_y):
        # trunk
        tx = int(x - wt // 2)
        ty = int(gnd_y - h)
        trunk_col = sc(100 + shade, 65 + shade, 30 + shade)
        highlight  = sc(130 + shade, 90 + shade, 50 + shade)
        pygame.draw.rect(surf, trunk_col, (tx, ty, wt, h))
        pygame.draw.rect(surf, highlight, (tx, ty, max(2, wt//3), h))

        # foliage layers
        cx = int(x)
        for i, (rw, rh, dy) in enumerate([
            (int(wt*3.5), int(h*0.38), 0),
            (int(wt*4.8), int(h*0.30), int(h*0.22)),
            (int(wt*3.0), int(h*0.22), int(h*0.40)),
        ]):
            fy = ty + dy - int(rh * 0.5)
            base = sc(35 + shade + i*6, 140 + shade - i*10, 35 + shade)
            lit  = sc(60 + shade + i*6, 190 + shade - i*10, 50 + shade)
            shd  = sc(15 + shade,        80 + shade - i*8,  15 + shade)
            # main ellipse
            pygame.draw.ellipse(surf, base, (cx - rw, fy, rw*2, rh))
            # highlight (upper-left)
            hl_rect = (cx - rw + rw//5, fy + rh//8, rw, rh//2)
            pygame.draw.ellipse(surf, lit, hl_rect)
            # shadow (lower-right)
            sh_rect = (cx + rw//6, fy + rh//2, rw*4//5, rh//2)
            pygame.draw.ellipse(surf, shd, sh_rect)

    def _draw_bush(self, surf, x, r, shade, gnd_y):
        cx, cy = int(x), int(gnd_y - r // 2)
        base = sc(40 + shade, 160 + shade, 40 + shade)
        lit  = sc(70 + shade, 200 + shade, 60 + shade)
        shd  = sc(15 + shade,  80 + shade, 15 + shade)
        for dx, dy, rs, col in [
            (0,     0,   r,    base),
            (-r//2, r//4, r*3//4, base),
            ( r//2, r//4, r*3//4, base),
            (-r//5, -r//5, r*2//3, lit),
            ( r//4,  r//4, r//2,  shd),
        ]:
            pygame.draw.circle(surf, col, (cx + dx, cy + dy), rs)

    # ── ground tile ───────────────────────────────────────────────────────────
    def _draw_ground_tile(self, surf, x, y):
        W, GH = self.W, self.GH
        # soil
        pygame.draw.rect(surf, GROUND_COL, (x, y + 18, W, GH - 18))
        # soil detail streaks
        for i in range(0, GH - 18, 12):
            col = lerp_color(GROUND_COL, (120, 80, 40), 0.3 + 0.3 * (i / GH))
            pygame.draw.line(surf, col, (x, y + 20 + i), (x + W, y + 20 + i))
        # grass layers
        pygame.draw.rect(surf, GRASS_TOP, (x, y,      W, 8))
        pygame.draw.rect(surf, GRASS_MID, (x, y + 8,  W, 6))
        pygame.draw.rect(surf, GRASS_BOT, (x, y + 14, W, 4))
        # grass blade tufts
        random.seed(42)
        for gx in range(x, x + W, 6):
            hh = random.randint(3, 9)
            col = random.choice([(50, 190, 40), (35, 150, 30), (70, 210, 55)])
            pygame.draw.line(surf, col, (gx, y), (gx + random.randint(-2, 2), y - hh))
        random.seed()

    # ── full frame render ─────────────────────────────────────────────────────
    def update_and_draw(self, surf, speed_factor=1.0):
        # parallax offsets
        for i in range(4):
            self.scroll[i] = (self.scroll[i] + speed_factor * (0.15 + i * 0.45)) % (self.W * 2)

        # sky
        surf.blit(self.sky_surf, (0, 0))

        # clouds (slowest layer)
        gnd_y = self.H - self.GH
        for c in self.clouds:
            c["x"] -= c["speed"] * speed_factor
            if c["x"] + c["w"] < 0:
                c.update(self._new_cloud())
                c["x"] = float(self.W + c["w"])
            self._draw_cloud(surf, c)

        # distant hills / mountain silhouettes
        self._draw_hills(surf, gnd_y)

        # midground: trees (wrap seamlessly)
        tree_scroll = self.scroll[2]
        for t in self.trees:
            tx = (t["x"] - tree_scroll) % (self.W * 2)
            if -150 < tx < self.W + 50:
                self._draw_tree(surf, tx, t["h"], t["wt"], t["shade"], gnd_y)

        # foreground: bushes
        bush_scroll = self.scroll[3]
        for b in self.bushes:
            bx = (b["x"] - bush_scroll) % (self.W * 2)
            if -60 < bx < self.W + 60:
                self._draw_bush(surf, bx, b["r"], b["shade"], gnd_y)

        # ground strip (two tiles for seamless scroll)
        gx = -int(self.scroll[3]) % self.W
        self._draw_ground_tile(surf, gx - self.W, gnd_y)
        self._draw_ground_tile(surf, gx,          gnd_y)

    def _draw_hills(self, surf, gnd_y):
        """Atmospheric layered hill silhouettes."""
        for layer, (col, amp, freq, offset) in enumerate([
            ((100, 160, 200), 55, 0.007, 0),
            (( 70, 140, 100), 75, 0.010, 300),
            (( 50, 120,  60), 60, 0.015, 600),
        ]):
            scroll_speed = 0.08 + layer * 0.06
            ox = self.scroll[0] * scroll_speed
            pts = [(0, gnd_y)]
            for x in range(0, self.W + 5, 4):
                y = int(gnd_y - amp * (0.5 + 0.5 * math.sin((x + offset + ox) * freq)))
                pts.append((x, y))
            pts.append((self.W, gnd_y))
            pygame.draw.polygon(surf, col, pts)


# ─────────────────────────────────────────────────────────────────────────────
#  3-D Stylised Pipe  (single pipe = top or bottom half)
# ─────────────────────────────────────────────────────────────────────────────
class Pipe:
    W = 72          # pipe body width

    def __init__(self, x, y, h, facing_down=True):
        """
        facing_down = True  → top pipe (opening faces downward)
        facing_down = False → bottom pipe (opening faces upward)
        """
        self.x  = float(x)
        self.y  = y          # top-left y of the pipe rectangle
        self.h  = h
        self.facing_down = facing_down
        self.passed = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x), self.y, self.W, self.h)

    def hitbox(self):
        """Slightly inset hitbox for fairness."""
        return pygame.Rect(int(self.x) + 6, self.y, self.W - 12, self.h)

    def draw(self, surf):
        x, y, w, h = int(self.x), self.y, self.W, self.h

        # ── Body cylinder ──────────────────────────────────────────────────────
        # Left-edge shadow band
        pygame.draw.rect(surf, PIPE_DARK,  (x,          y, 10, h))
        # Main body fill
        pygame.draw.rect(surf, PIPE_BASE,  (x + 10,     y, w - 20, h))
        # Right-edge mid-shade band
        pygame.draw.rect(surf, lerp_color(PIPE_BASE, PIPE_DARK, 0.55),
                         (x + w - 14,  y, 8, h))
        # Far-right dark edge
        pygame.draw.rect(surf, PIPE_DARK,  (x + w - 6,  y, 6, h))
        # Primary specular highlight (vertical stripe)
        pygame.draw.rect(surf, PIPE_LIGHT, (x + 12,     y, 8, h))
        # Secondary specular (narrower, brighter)
        pygame.draw.rect(surf, PIPE_SPEC,  (x + 14,     y, 3, h))

        # ── Rivet / seam lines every 28 px ───────────────────────────────────
        for sy in range(y + 28, y + h, 28):
            pygame.draw.line(surf, PIPE_DARK,  (x, sy), (x + w, sy), 1)

        # ── Flange (cap/rim) ──────────────────────────────────────────────────
        fw = w + 16          # flange is wider than body
        fh = 26              # flange thickness
        fh_inner = 10        # inner thinner ring thickness
        if self.facing_down:
            fy = y + h - fh  # flange at bottom of top pipe
        else:
            fy = y           # flange at top of bottom pipe

        # Outer flange shadow (bottom edge of flange for top pipe, top for bottom)
        if self.facing_down:
            # drop shadow below
            pygame.draw.rect(surf, PIPE_DARK,  (x - 8, fy + fh, fw, 5))
        else:
            # drop shadow above
            pygame.draw.rect(surf, PIPE_DARK,  (x - 8, fy - 5,  fw, 5))

        # Flange dark edge left + right
        pygame.draw.rect(surf, PIPE_DARK,   (x - 8,       fy, 10, fh))
        pygame.draw.rect(surf, PIPE_DARK,   (x + w - 2,   fy, 10, fh))
        # Flange base
        pygame.draw.rect(surf, PIPE_FLANGE, (x - 8,       fy, fw, fh))
        # Flange highlight (upper portion)
        pygame.draw.rect(surf, PIPE_LIGHT,  (x - 8,       fy, fw, fh // 2))
        # Flange specular top stripe
        pygame.draw.rect(surf, PIPE_SPEC,   (x - 6,       fy + 2, fw - 4, 4))
        # Flange rim line at opening
        if self.facing_down:
            pygame.draw.rect(surf, PIPE_RIM, (x - 8, fy,             fw, 4))
        else:
            pygame.draw.rect(surf, PIPE_RIM, (x - 8, fy + fh - 4,  fw, 4))

        # Inner rim highlight ring
        if self.facing_down:
            pygame.draw.rect(surf, PIPE_LIGHT, (x - 4, fy + 4, fw - 8, fh_inner))
        else:
            pygame.draw.rect(surf, PIPE_LIGHT, (x - 4, fy + fh - fh_inner - 4, fw - 8, fh_inner))

        # ── Ambient occlusion thin outline ────────────────────────────────────
        pygame.draw.rect(surf, PIPE_DARK, (x, y, w, h), 1)


class PipeManager:
    def __init__(self, width, sky_height):
        self.W  = width
        self.SH = sky_height
        self.pairs: list[tuple[Pipe, Pipe]] = []
        self.last_x = width + 50

    def reset(self):
        self.pairs.clear()
        self.last_x = self.W + 50

    def update(self, score_callback, pipe_speed: float = PIPE_SPEED_START):
        # spawn
        if not self.pairs or self.pairs[-1][0].x < self.W - PIPE_SPAWN_DIST:
            self._spawn()

        # scroll & score
        dead = []
        for pair in self.pairs:
            top, bot = pair
            top.x -= pipe_speed
            bot.x  = top.x
            # score when bird passes right edge of pipe
            if not top.passed and top.x + Pipe.W < 80:
                top.passed = bot.passed = True
                score_callback()
            if top.x + Pipe.W < 0:
                dead.append(pair)
        for pair in dead:
            self.pairs.remove(pair)

    def _spawn(self):
        margin = 80
        max_top = self.SH - PIPE_GAP - margin
        top_h   = random.randint(margin, max_top)
        bot_y   = top_h + PIPE_GAP
        bot_h   = self.SH - bot_y
        x       = self.W + Pipe.W
        self.pairs.append((
            Pipe(x, 0,     top_h, facing_down=True),
            Pipe(x, bot_y, bot_h, facing_down=False),
        ))

    def draw(self, surf):
        for top, bot in self.pairs:
            top.draw(surf)
            bot.draw(surf)

    def collides(self, bird_rect: pygame.Rect) -> bool:
        for top, bot in self.pairs:
            if bird_rect.colliderect(top.hitbox()) or bird_rect.colliderect(bot.hitbox()):
                return True
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  Bird
# ─────────────────────────────────────────────────────────────────────────────
class Bird:
    X = 80
    R = 18           # hitbox radius

    def __init__(self, sky_h):
        self.sky_h  = sky_h
        self.reset()

    def reset(self):
        self.y      = float(self.sky_h // 2)
        self.vy     = 0.0
        self.angle  = 0.0      # degrees; positive = nose up
        self.wing_t = 0.0      # 0..1 wing flap cycle phase
        self.wing_dir = 1
        self.alive  = True
        self.blink_timer = random.randint(60, 180)

    def flap(self, snd: SoundManager, flap_strength: float = FLAP_START):
        self.vy = flap_strength
        self.wing_t = 1.0
        snd.play("flap")

    def update(self, gravity: float = GRAVITY_START):
        self.vy     = clamp(self.vy + gravity, -18, 15)
        self.y     += self.vy

        # pitch based on velocity
        target_angle = clamp(-self.vy * 5, -80, 25)
        self.angle  += (target_angle - self.angle) * 0.12

        # wing flap cycle
        self.wing_t  = max(0.0, self.wing_t - 0.06)

        # blink
        self.blink_timer -= 1
        if self.blink_timer <= 0:
            self.blink_timer = random.randint(60, 180)

    def hover(self, t):
        """Gentle sine-wave hover for title/game-over screen."""
        self.y = self.sky_h // 2 + math.sin(t * 0.05) * 12

    @property
    def rect(self):
        r = self.R
        return pygame.Rect(self.X - r, int(self.y) - r, r * 2, r * 2)

    @property
    def circle(self):
        return (self.X, int(self.y), self.R)

    def draw(self, surf):
        cx, cy = self.X, int(self.y)
        r      = self.R

        # ── rotation transform via surface ───────────────────────────────────
        d = r * 2 + 20
        bird_surf = pygame.Surface((d, d), pygame.SRCALPHA)
        bc = d // 2          # local centre

        # wing (draw behind body)
        wing_angle = math.radians(self.wing_t * 60 - 15)
        wx1 = bc - int(r * 0.3)
        wy1 = bc + int(r * 0.1)
        wing_len = int(r * 1.1)
        wx2 = wx1 - int(wing_len * math.cos(wing_angle))
        wy2 = wy1 + int(wing_len * math.sin(wing_angle) + r * 0.3)
        pygame.draw.polygon(bird_surf, BIRD_WING, [
            (wx1, wy1),
            (wx2, wy2),
            (wx2 + int(r * 0.6), wy2 - int(r * 0.2)),
        ])
        # wing highlight
        pygame.draw.polygon(bird_surf, lerp_color(BIRD_WING, WHITE, 0.3), [
            (wx1, wy1),
            (wx2 + 2, wy2 - 3),
            (wx2 + int(r * 0.4), wy2 - int(r * 0.15)),
        ])

        # body
        pygame.draw.ellipse(bird_surf, BIRD_BODY,  (bc - r, bc - r + 2, r * 2, int(r * 1.8)))
        # belly
        pygame.draw.ellipse(bird_surf, BIRD_BELLY, (bc - int(r*0.5), bc, int(r * 1.0), int(r * 0.9)))
        # body sheen
        pygame.draw.ellipse(bird_surf, lerp_color(BIRD_BODY, WHITE, 0.55),
                            (bc - int(r*0.6), bc - r + 3, int(r * 0.9), int(r * 0.5)))

        # beak
        beak_pts = [
            (bc + r - 4, bc - 4),
            (bc + r + 10, bc + 1),
            (bc + r - 4, bc + 6),
        ]
        pygame.draw.polygon(bird_surf, BIRD_BEAK, beak_pts)
        pygame.draw.polygon(bird_surf, lerp_color(BIRD_BEAK, WHITE, 0.4), [
            (bc + r - 4, bc - 4), (bc + r + 10, bc + 1), (bc + r + 4, bc - 2)])

        # eye
        ex, ey = bc + int(r * 0.35), bc - int(r * 0.22)
        er = max(4, r // 3)
        blinking = self.blink_timer < 5
        if blinking:
            pygame.draw.line(bird_surf, BLACK, (ex - er, ey), (ex + er, ey), 2)
        else:
            pygame.draw.circle(bird_surf, BIRD_EYE,   (ex, ey), er)
            pygame.draw.circle(bird_surf, BIRD_PUPIL, (ex + 1, ey), max(2, er - 2))
            pygame.draw.circle(bird_surf, WHITE,       (ex + er//2 - 1, ey - er//2 + 1), max(1, er//3))

        # rotate and blit
        rotated = pygame.transform.rotate(bird_surf, self.angle)
        rr      = rotated.get_rect(center=(cx, cy))
        surf.blit(rotated, rr)


# ─────────────────────────────────────────────────────────────────────────────
#  High-Score persistence
# ─────────────────────────────────────────────────────────────────────────────
def load_highscore():
    try:
        with open(HIGHSCORE_FILE) as f:
            return json.load(f).get("best", 0)
    except Exception:
        return 0

def save_highscore(score):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            json.dump({"best": score}, f)
    except Exception:
        pass

def medal_for(score):
    if score >= 40:  return ("Platinum", PLATINUM)
    if score >= 20:  return ("Gold",     GOLD)
    if score >= 10:  return ("Silver",   SILVER)
    if score >= 5:   return ("Bronze",   BRONZE)
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Game
# ─────────────────────────────────────────────────────────────────────────────
class Game:
    STATE_TITLE    = "title"
    STATE_PLAYING  = "playing"
    STATE_GAMEOVER = "gameover"

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Flappy Bird Deluxe 🐦")
        self.clock  = pygame.time.Clock()

        self.snd    = SoundManager()
        self.bg     = Background(WIDTH, HEIGHT, GROUND_H)
        self.bird   = Bird(SKY_H)
        self.pipes  = PipeManager(WIDTH, SKY_H)
        self.parts  = ParticleSystem()

        self.score      = 0
        self.best       = load_highscore()
        self.state      = self.STATE_TITLE
        self.tick       = 0
        self.shake      = 0
        self.flash      = 0

        # UI font
        self.font_big   = pygame.font.SysFont("Arial Black", 52, bold=True)
        self.font_med   = pygame.font.SysFont("Arial Black", 30, bold=True)
        self.font_sm    = pygame.font.SysFont("Arial", 22)
        self.font_tiny  = pygame.font.SysFont("Arial", 16)

        # Game-over panel slide-in
        self.panel_y    = HEIGHT + 10
        # cached flap strength (updated each frame by get_difficulty)
        self._cur_flap_str = FLAP_START

    # ── input ─────────────────────────────────────────────────────────────────
    def _handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                key = getattr(ev, "key", None)
                if key == pygame.K_ESCAPE:
                    return False
                if self.state == self.STATE_TITLE:
                    if key == pygame.K_SPACE or ev.type == pygame.MOUSEBUTTONDOWN:
                        self._start_game()
                elif self.state == self.STATE_PLAYING:
                    if key == pygame.K_SPACE or ev.type == pygame.MOUSEBUTTONDOWN:
                        self.bird.flap(self.snd, self._cur_flap_str)
                        self.parts.emit_flap(self.bird.X - 20, int(self.bird.y))
                elif self.state == self.STATE_GAMEOVER:
                    if key == pygame.K_SPACE or ev.type == pygame.MOUSEBUTTONDOWN:
                        self._start_game()
        return True

    def _start_game(self):
        self.bird.reset()
        self.pipes.reset()
        self.parts.particles.clear()
        self.score         = 0
        self.shake         = 0
        self.flash         = 0
        self.panel_y       = HEIGHT + 10
        self._cur_flap_str = FLAP_START
        self.state         = self.STATE_PLAYING

    def _on_score(self):
        self.score += 1
        self.snd.play("score")
        # emit sparkle at the centre of the gap
        for top, bot in self.pipes.pairs:
            if top.passed:
                gap_x = int(top.x + Pipe.W + 40)
                gap_y = int(top.h + PIPE_GAP // 2)
                self.parts.emit_score(gap_x, gap_y)
                break

    def _trigger_death(self):
        self.snd.play("hit")
        self.snd.play("die")
        self.shake = 14
        self.flash  = 8
        self.parts.emit_death(self.bird.X, int(self.bird.y))
        if int(self.bird.y) >= SKY_H - 10:
            self.parts.emit_ground_dust(self.bird.X, SKY_H)
        if self.score > self.best:
            self.best = self.score
            save_highscore(self.best)
        self.state   = self.STATE_GAMEOVER
        self.panel_y = HEIGHT + 10

    # ── update ────────────────────────────────────────────────────────────────
    def _update(self):
        self.tick += 1

        if self.state == self.STATE_TITLE:
            self.bird.hover(self.tick)

        elif self.state == self.STATE_PLAYING:
            grav, flap_str, p_speed = get_difficulty(self.score)
            self.bird.update(grav)
            self.pipes.update(self._on_score, p_speed)
            self._cur_flap_str = flap_str   # cache so handle_events can use it
            self.bg.update_and_draw    # called in draw

            # collision: ground / ceiling
            if self.bird.y <= 0 or self.bird.y >= SKY_H - self.bird.R:
                self._trigger_death()
                return

            # collision: pipes
            if self.pipes.collides(self.bird.rect):
                self._trigger_death()
                return

        elif self.state == self.STATE_GAMEOVER:
            # gentle slide-in for panel
            target = HEIGHT // 2 - 110
            self.panel_y += (target - self.panel_y) * 0.12

        # decay
        if self.shake > 0: self.shake -= 1
        if self.flash  > 0: self.flash  -= 1

    # ── draw ──────────────────────────────────────────────────────────────────
    def _draw(self):
        speed = 1.0 if self.state == self.STATE_PLAYING else 0.3

        # camera shake offset
        sx = random.randint(-self.shake, self.shake) if self.shake else 0
        sy = random.randint(-self.shake, self.shake) if self.shake else 0

        target = pygame.Surface((WIDTH, HEIGHT))
        self.bg.update_and_draw(target, speed)
        self.pipes.draw(target)
        self.parts.update_and_draw(target)
        self.bird.draw(target)

        # impact flash
        if self.flash > 0:
            fl = pygame.Surface((WIDTH, HEIGHT))
            fl.set_alpha(int(self.flash * 20))
            fl.fill(WHITE)
            target.blit(fl, (0, 0))

        self.screen.blit(target, (sx, sy))

        # ── HUD overlays (no shake) ───────────────────────────────────────────
        if self.state == self.STATE_TITLE:
            self._draw_title()
        elif self.state == self.STATE_PLAYING:
            self._draw_hud()
        elif self.state == self.STATE_GAMEOVER:
            self._draw_hud()
            self._draw_gameover_panel()

    def _shadow_text(self, surf, font, text, color, cx, cy):
        sh = font.render(text, True, BLACK)
        sr = sh.get_rect(center=(cx + 2, cy + 2))
        surf.blit(sh, sr)
        tx = font.render(text, True, color)
        tr = tx.get_rect(center=(cx, cy))
        surf.blit(tx, tr)

    def _draw_hud(self):
        self._shadow_text(self.screen, self.font_big, str(self.score), WHITE, WIDTH // 2, 55)

    def _draw_title(self):
        # semi-transparent dark title backdrop
        panel = pygame.Surface((340, 160), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 130))
        self.screen.blit(panel, (WIDTH // 2 - 170, 120))

        self._shadow_text(self.screen, self.font_big, "FLAPPY BIRD", GOLD,   WIDTH // 2, 165)
        self._shadow_text(self.screen, self.font_med, "DELUXE",      WHITE,  WIDTH // 2, 218)

        # pulsing prompt
        alpha = int(140 + 115 * abs(math.sin(self.tick * 0.05)))
        prompt_surf = self.font_sm.render("Press SPACE or Click to Flap!", True, WHITE)
        prompt_surf.set_alpha(alpha)
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH // 2, 275)))

    def _draw_gameover_panel(self):
        py = int(self.panel_y)
        pw, ph = 300, 220

        # panel background
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((20, 20, 20, 200))
        pygame.draw.rect(panel, GOLD, (0, 0, pw, ph), 3)
        self.screen.blit(panel, (WIDTH // 2 - pw // 2, py))

        cx = WIDTH // 2
        self._shadow_text(self.screen, self.font_med, "GAME OVER",  (255, 80, 80), cx, py + 30)

        self._shadow_text(self.screen, self.font_sm,  f"Score: {self.score}", WHITE, cx, py + 75)
        self._shadow_text(self.screen, self.font_sm,  f"Best:  {self.best}",  GOLD,  cx, py + 105)

        # medal
        medal = medal_for(self.score)
        if medal:
            name, col = medal
            self._shadow_text(self.screen, self.font_sm, f"🏅 {name}!", col, cx, py + 140)

        # restart hint (pulsing)
        alpha = int(140 + 115 * abs(math.sin(self.tick * 0.07)))
        hint = self.font_tiny.render("Press SPACE or Click to Retry", True, WHITE)
        hint.set_alpha(alpha)
        self.screen.blit(hint, hint.get_rect(center=(cx, py + 195)))

    # ── main loop ─────────────────────────────────────────────────────────────
    def run(self):
        running = True
        while running:
            running = self._handle_events()
            self._update()
            self._draw()
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()


# ─────────────────────────────────────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    Game().run()
