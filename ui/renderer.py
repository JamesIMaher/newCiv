"""Isometric map drawing in the style of Alpha Centauri.

Tiles are diamonds (width tw, height th = tw/2) on the staggered grid defined in game.world.
Terrain is pre-rendered into cached sprites (texture + hill shading + improvements); roads,
borders, fog, bases and units are drawn on top every frame for the visible tiles only.
"""
import math
import random

import pygame

from game.world import ARID, MOIST, RAINY, FLAT, ROLLING, ROCKY
from . import theme

ZOOMS = [32, 48, 64, 96, 128]   # diamond width in pixels (must be divisible by 4)

# Alpha Centauri-like palette: rust and ochre soils, olive-green wetlands, teal seas, magenta fungus.
LAND_COLORS = {ARID: (172, 116, 70), MOIST: (132, 116, 66), RAINY: (84, 112, 58)}
ROCK_COLOR = (118, 96, 84)
FUNGUS_COLOR = (186, 52, 104)
FUNGUS_LIGHT = (242, 128, 176)
DEEP = (12, 34, 70)
SHELF = (26, 88, 118)
SHADE_LEVELS = 5            # hill shading levels either side of flat


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def diamond(cx, cy, tw, inset=0):
    hw, hh = tw / 2 - inset, tw / 4 - inset / 2
    return [(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)]


def edge_points(cx, cy, tw, direction, inset=1):
    """Endpoints of the diamond edge facing an edge neighbour (NE/SE/SW/NW)."""
    top, right, bottom, left = diamond(cx, cy, tw, inset)
    return {"NE": (top, right), "SE": (right, bottom), "SW": (bottom, left), "NW": (left, top)}[direction]


def terrain_color(t):
    if t.is_ocean:
        f = (t.elevation + 3000) / 3000
        return theme.mix(DEEP, SHELF, max(0.0, min(1.0, f)) ** 1.6)
    c = LAND_COLORS[t.rainfall]
    if t.rockiness == ROCKY:
        c = theme.mix(c, ROCK_COLOR, 0.55)
    elif t.rockiness == ROLLING:
        c = theme.mix(c, ROCK_COLOR, 0.18)
    return theme.shade(c, t.elevation / 3500 * 26 - 8)


def tile_shade(world, t):
    """Hill shading from the slope, lit from the upper left. Returns an int level."""
    if t.is_ocean:
        return 0

    def elev(d):
        p = world.step(t.x, t.y, d)
        if p is None:
            return t.elevation
        return max(0, world.tiles[p[0]][p[1]].elevation)

    gx = elev("E") - elev("W")
    gy = elev("S") - elev("N")
    v = (gx + gy) / 1800
    return max(-SHADE_LEVELS, min(SHADE_LEVELS, int(round(v * SHADE_LEVELS))))


# ---------------------------------------------------------------------------
# Terrain sprites
# ---------------------------------------------------------------------------
_sprites = {}
_masks = {}


def _mask(tw):
    if tw not in _masks:
        m = pygame.Surface((tw, tw // 2), pygame.SRCALPHA)
        pygame.draw.polygon(m, (255, 255, 255, 255), diamond(tw / 2, tw / 4, tw))
        _masks[tw] = m
    return _masks[tw]


def _rand_point(rng, tw, th, margin=0.15):
    while True:
        x = rng.uniform(0, tw)
        y = rng.uniform(0, th)
        if abs(x - tw / 2) / (tw / 2) + abs(y - th / 2) / (th / 2) <= 1 - margin:
            return x, y


def tile_sprite(world, t, tw):
    variant = (t.x * 7919 + t.y * 104729) % 4
    shade = tile_shade(world, t)
    kind = "deep" if t.is_ocean and not t.is_shelf else "shelf" if t.is_ocean else "land"
    imps = tuple(sorted(i for i in t.improvements if i != "road"))
    key = (kind, t.rainfall, t.rockiness, t.fungus, variant, shade, imps, t.special, t.supply_pod,
           t.elevation // 500, tw)
    spr = _sprites.get(key)
    if spr is None:
        spr = _build_sprite(t, tw, variant, shade)
        _sprites[key] = spr
    return spr


def _build_sprite(t, tw, variant, shade):
    th = tw // 2
    s = pygame.Surface((tw, th), pygame.SRCALPHA)
    base = terrain_color(t)
    lit = theme.shade(base, shade * 9)
    s.fill(lit)
    rng = random.Random(hash((t.is_ocean, t.rainfall, t.rockiness, t.fungus, variant)))
    k = tw / 64
    if t.is_ocean:
        for _ in range(int(10 * k * k) + 3):
            x, y = _rand_point(rng, tw, th, 0.1)
            w = rng.uniform(3, 8) * k
            pygame.draw.line(s, theme.shade(lit, rng.choice((14, 22, -8))), (x - w, y), (x + w, y), 1)
    else:
        # mottled soil
        for _ in range(int(26 * k * k) + 6):
            x, y = _rand_point(rng, tw, th, 0.0)
            r = rng.uniform(1.5, 5) * k
            pygame.draw.ellipse(s, theme.shade(lit, rng.randint(-16, 14)), (x - r, y - r / 2, 2 * r, r))
        if t.rockiness == ROLLING:
            for _ in range(3):
                x, y = _rand_point(rng, tw, th, 0.3)
                w = rng.uniform(8, 14) * k
                pygame.draw.arc(s, theme.shade(lit, -24), (x - w, y - w / 3, 2 * w, w / 1.5), 0.3, math.pi - 0.3, 1)
                pygame.draw.arc(s, theme.shade(lit, 18), (x - w, y - w / 3 + 1, 2 * w, w / 1.5), 0.5, math.pi - 0.5, 1)
        if t.rockiness == ROCKY:
            for _ in range(int(5 * k) + 3):
                x, y = _rand_point(rng, tw, th, 0.2)
                r = rng.uniform(3, 7) * k
                pts = [(x - r, y + r / 3), (x - r / 3, y - r * 0.7), (x + r / 2, y - r / 2), (x + r, y + r / 3)]
                pygame.draw.polygon(s, theme.shade(ROCK_COLOR, -34 + shade * 6), pts)
                pygame.draw.lines(s, theme.shade(ROCK_COLOR, 40 + shade * 6), False, pts[:3], 1)
    if t.fungus:
        fc = FUNGUS_COLOR if t.is_land else (150, 60, 130)
        for _ in range(int(20 * k * k) + 6):
            x, y = _rand_point(rng, tw, th, 0.05)
            r = rng.uniform(2.5, 7) * k
            pygame.draw.ellipse(s, theme.shade(fc, rng.randint(-30, 24) + shade * 6), (x - r, y - r / 2, 2 * r, r))
        for _ in range(int(10 * k * k) + 3):
            x, y = _rand_point(rng, tw, th, 0.1)
            pygame.draw.circle(s, FUNGUS_LIGHT, (int(x), int(y)), max(1, int(1.2 * k)))
        for _ in range(3):
            x, y = _rand_point(rng, tw, th, 0.2)
            pts = [(x + i * 3 * k, y + math.sin(i + variant) * 2 * k) for i in range(5)]
            pygame.draw.lines(s, (110, 20, 60), False, pts, 1)
    _draw_improvements(s, t, tw, rng)
    s.blit(_mask(tw), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return s


def _draw_improvements(s, t, tw, rng):
    th = tw // 2
    cx, cy = tw / 2, th / 2
    k = tw / 64
    imp = t.improvements
    if "farm" in imp:
        # furrows running parallel to the NE edge
        col = (206, 186, 104)
        for i in range(-3, 4):
            ox, oy = i * 5 * k, i * 2.5 * k
            a = (cx - 14 * k + ox, cy + 7 * k - oy + i * 0)
            b = (cx + 14 * k + ox, cy - 7 * k - oy + i * 0)
            pygame.draw.line(s, col, (a[0], a[1] + i * 5 * k), (b[0], b[1] + i * 5 * k), max(1, int(1.4 * k)))
    if "forest" in imp:
        spots = [(cx - 12 * k, cy - 2 * k), (cx + 2 * k, cy - 6 * k), (cx + 14 * k, cy), (cx - 3 * k, cy + 6 * k),
                 (cx + 8 * k, cy + 7 * k), (cx - 16 * k, cy + 6 * k)]
        for x, y in sorted(spots, key=lambda p: p[1]):
            h = rng.uniform(9, 13) * k
            w = h * 0.45
            pygame.draw.ellipse(s, (20, 30, 18), (x - w, y - 1.5 * k, 2 * w, 3 * k))
            pygame.draw.polygon(s, (30, 78, 40), [(x - w, y), (x, y - h), (x + w, y)])
            pygame.draw.line(s, (80, 140, 80), (x, y - h), (x - w * 0.6, y - 1), 1)
    if "mine" in imp:
        x, y = cx - 4 * k, cy + 2 * k
        pygame.draw.ellipse(s, (70, 56, 46), (x - 10 * k, y - 4 * k, 20 * k, 9 * k))
        pygame.draw.ellipse(s, (20, 16, 14), (x - 4 * k, y - 2 * k, 8 * k, 4 * k))
        # headframe
        pygame.draw.line(s, (180, 170, 150), (x + 6 * k, y), (x + 10 * k, y - 12 * k), max(1, int(k)))
        pygame.draw.line(s, (180, 170, 150), (x + 14 * k, y), (x + 10 * k, y - 12 * k), max(1, int(k)))
        pygame.draw.circle(s, (220, 200, 120), (int(x + 10 * k), int(y - 12 * k)), max(1, int(1.5 * k)))
    if "solar" in imp:
        x, y = cx + 10 * k, cy - 2 * k
        panel = [(x - 8 * k, y), (x, y - 5 * k), (x + 8 * k, y - 1 * k), (x, y + 4 * k)]
        pygame.draw.line(s, (60, 60, 60), (x, y + 2 * k), (x, y + 7 * k), max(1, int(k)))
        pygame.draw.polygon(s, (40, 70, 160), panel)
        pygame.draw.polygon(s, (240, 210, 90), panel, 1)
        pygame.draw.line(s, (120, 170, 240), panel[0], panel[2], 1)
    if t.special:
        x, y = cx - 14 * k, cy + 1 * k
        kind = {"nutrient": "nutrients", "mineral": "minerals", "energy": "energy"}[t.special]
        glow = pygame.Surface((int(16 * k) + 2, int(10 * k) + 2), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (*theme.RESOURCE_COLORS[kind], 90), glow.get_rect())
        s.blit(glow, (x - 8 * k, y - 5 * k))
        theme.resource_icon(s, kind, (int(x), int(y)), max(3, int(5 * k)))
    if t.supply_pod:
        x, y = cx + 2 * k, cy
        pygame.draw.ellipse(s, (20, 20, 20), (x - 8 * k, y + 1 * k, 16 * k, 5 * k))
        body = pygame.Rect(0, 0, 12 * k, 9 * k)
        body.center = (x, y)
        pygame.draw.rect(s, (205, 225, 235), body, border_radius=max(1, int(2 * k)))
        pygame.draw.rect(s, (30, 110, 150), body, max(1, int(k)), border_radius=max(1, int(2 * k)))
        pygame.draw.line(s, (240, 90, 60), (body.left + 2, body.centery), (body.right - 2, body.centery), max(1, int(k)))


# ---------------------------------------------------------------------------
# Roads, bases and units (drawn every frame)
# ---------------------------------------------------------------------------
def draw_roads(surf, world, t, cx, cy, tw, base_pos):
    if "road" not in t.improvements and (t.x, t.y) not in base_pos:
        return
    col = (104, 82, 58)
    w = max(2, tw // 22)
    linked = False
    for d, (ddx, ddy) in world.DIRS.items():
        p = world.step(t.x, t.y, d)
        if p is None:
            continue
        n = world.tiles[p[0]][p[1]]
        if "road" in n.improvements or p in base_pos:
            ex = cx + ddx * tw / 4
            ey = cy + ddy * tw / 8
            pygame.draw.line(surf, col, (cx, cy), (ex, ey), w)
            linked = True
    if not linked:
        pygame.draw.ellipse(surf, col, (cx - tw / 10, cy - tw / 20, tw / 5, tw / 10))


def draw_base(surf, game, base, cx, cy, tw, label=True):
    col = game.players[base.owner].color
    k = tw / 64
    # landing pad
    pad = pygame.Rect(0, 0, 46 * k, 20 * k)
    pad.center = (cx, cy + 2 * k)
    pygame.draw.ellipse(surf, (40, 44, 48), pad)
    pygame.draw.ellipse(surf, theme.shade(col, -40), pad, max(1, int(2 * k)))
    # domes (back to front)
    domes = [(-12, -3, 9), (10, -4, 8), (-1, 3, 11)]
    if base.pop >= 4:
        domes.insert(0, (2, -9, 7))
    if base.pop >= 8:
        domes.insert(0, (-18, 2, 6))
    for dx, dy, r in domes:
        x, y, r = cx + dx * k, cy + dy * k, r * k
        rect = pygame.Rect(x - r, y - r, 2 * r, 2 * r)
        pygame.draw.ellipse(surf, (22, 26, 30), (x - r, y - r * 0.3, 2 * r, r * 0.9))
        pygame.draw.ellipse(surf, (196, 208, 214), (rect.x, rect.y, rect.w, rect.h * 1.0))
        pygame.draw.ellipse(surf, (236, 244, 248), (x - r * 0.6, y - r * 0.8, r * 0.8, r * 0.6))
        pygame.draw.arc(surf, col, (rect.x, rect.y + r * 0.2, rect.w, rect.h * 0.9), math.pi * 1.05, math.pi * 1.95,
                        max(1, int(2 * k)))
    # comms tower and faction flag
    tx, ty = cx + 18 * k, cy - 6 * k
    pygame.draw.line(surf, (170, 176, 180), (tx, ty + 8 * k), (tx, ty - 16 * k), max(1, int(1.5 * k)))
    pygame.draw.rect(surf, col, (tx, ty - 16 * k, 10 * k, 6 * k))
    pygame.draw.rect(surf, (10, 10, 10), (tx, ty - 16 * k, 10 * k, 6 * k), 1)
    # population box
    size = max(12, int(18 * k))
    box = pygame.Rect(0, 0, max(14, int(15 * k)), max(12, int(14 * k)))
    box.center = (cx - 22 * k, cy - 10 * k)
    pygame.draw.rect(surf, col, box)
    pygame.draw.rect(surf, (0, 0, 0), box, 1)
    lum = sum(col) / 3
    theme.text(surf, base.pop, box.center, size, (10, 10, 10) if lum > 150 else (255, 255, 255), bold=True, center=True)
    if label and tw >= 48:
        img = theme.font(max(15, int(19 * k))).render(base.name, True, (255, 255, 255))
        lr = img.get_rect(midtop=(cx, cy + tw / 4 - 2))
        bg = lr.inflate(8, 2)
        panel = pygame.Surface(bg.size, pygame.SRCALPHA)
        panel.fill((0, 0, 0, 160))
        surf.blit(panel, bg)
        pygame.draw.line(surf, col, bg.bottomleft, (bg.right - 1, bg.bottom), 2)
        surf.blit(img, lr)


def _figure(surf, x, y, col, k, weapon=False):
    pygame.draw.ellipse(surf, (0, 0, 0, 0), (x - 3 * k, y, 6 * k, 2 * k))
    pygame.draw.rect(surf, theme.shade(col, -50), (x - 2 * k, y - 4 * k, 1.6 * k, 4 * k))
    pygame.draw.rect(surf, theme.shade(col, -50), (x + 0.5 * k, y - 4 * k, 1.6 * k, 4 * k))
    pygame.draw.rect(surf, col, (x - 2.5 * k, y - 10 * k, 5 * k, 6.5 * k), border_radius=max(1, int(k)))
    pygame.draw.circle(surf, (230, 200, 170), (int(x), int(y - 12 * k)), max(1, int(2.2 * k)))
    pygame.draw.circle(surf, theme.shade(col, -30), (int(x), int(y - 13 * k)), max(1, int(2.2 * k)), 1)
    if weapon:
        pygame.draw.line(surf, (60, 60, 70), (x + 2 * k, y - 8 * k), (x + 7 * k, y - 10 * k), max(1, int(1.3 * k)))


def _rover(surf, x, y, col, k, gun=0, hover=False):
    body = [(x - 11 * k, y - 2 * k), (x - 2 * k, y - 7 * k), (x + 11 * k, y - 3 * k), (x + 2 * k, y + 2 * k)]
    if hover:
        glow = pygame.Surface((int(26 * k), int(8 * k)), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (120, 220, 255, 110), glow.get_rect())
        surf.blit(glow, (x - 13 * k, y))
        body = [(px, py - 3 * k) for px, py in body]
    else:
        for wx, wy in ((-8, 0), (-3, 2), (4, 0), (8, -2)):
            pygame.draw.ellipse(surf, (25, 25, 25), (x + wx * k - 2.5 * k, y + wy * k - 1.5 * k, 5 * k, 4 * k))
    side = [(px, py + 4 * k) for px, py in body]
    pygame.draw.polygon(surf, theme.shade(col, -60), [body[0], body[3], side[3], side[0]])
    pygame.draw.polygon(surf, theme.shade(col, -35), [body[3], body[2], side[2], side[3]])
    pygame.draw.polygon(surf, col, body)
    pygame.draw.polygon(surf, (10, 10, 10), body, 1)
    if gun:
        tx, ty = x, y - 4 * k - (3 * k if hover else 0)
        pygame.draw.ellipse(surf, theme.shade(col, 30), (tx - 4 * k, ty - 3 * k, 8 * k, 5 * k))
        pygame.draw.line(surf, (50, 50, 55), (tx + 2 * k, ty - 1 * k), (tx + (8 + 3 * gun) * k, ty - (3 + gun) * k),
                         max(1, int((1 + gun * 0.5) * k)))


def _hull(surf, x, y, col, k, length=14, tower=False, cargo=False):
    hull = [(x - length * k, y - 1 * k), (x - 6 * k, y - 5 * k), (x + length * k, y - 4 * k), (x + 6 * k, y + 2 * k)]
    wake = pygame.Surface((int(34 * k), int(9 * k)), pygame.SRCALPHA)
    pygame.draw.ellipse(wake, (200, 240, 255, 70), wake.get_rect())
    surf.blit(wake, (x - 17 * k, y - 3 * k))
    pygame.draw.polygon(surf, col, hull)
    pygame.draw.polygon(surf, (10, 10, 10), hull, 1)
    if cargo:
        for i in range(3):
            pygame.draw.rect(surf, theme.shade(col, 40 - i * 15), (x - 7 * k + i * 5 * k, y - 7 * k + i * 0.5 * k, 4 * k, 4 * k))
    if tower:
        pygame.draw.rect(surf, theme.shade(col, 40), (x - 2 * k, y - 11 * k, 5 * k, 7 * k))
        pygame.draw.line(surf, (50, 50, 55), (x + 3 * k, y - 8 * k), (x + 12 * k, y - 10 * k), max(1, int(1.5 * k)))


def draw_unit_shape(surf, u, x, y, col, k):
    """The unit itself, standing on (x, y)."""
    tid = u.type_id
    shadow = pygame.Surface((int(26 * k), int(8 * k)), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())
    if u.type.domain != "sea":
        surf.blit(shadow, (x - 13 * k, y - 3 * k))
    if tid == "xenoworm":
        glow = pygame.Surface((int(30 * k), int(14 * k)), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 90, 180, 70), glow.get_rect())
        surf.blit(glow, (x - 15 * k, y - 8 * k))
        for w in range(3):
            pts = [(x + (i - 4) * 2.4 * k + w * 3 * k - 3 * k, y - 4 * k - w * 2 * k + math.sin(i * 1.1 + w) * 2.5 * k)
                   for i in range(8)]
            pygame.draw.lines(surf, (236, 120, 170), False, pts, max(2, int(2.5 * k)))
            pygame.draw.circle(surf, (120, 20, 60), (int(pts[-1][0]), int(pts[-1][1])), max(1, int(1.8 * k)))
    elif tid in ("scout", "laser_squad"):
        n = 2 if tid == "scout" else 3
        for i in range(n):
            _figure(surf, x + (i - (n - 1) / 2) * 6 * k, y + (i % 2) * 2 * k, col, k, weapon=tid != "scout")
    elif tid.endswith("garrison"):
        lvl = {"synth_garrison": 0, "plasma_garrison": 1, "fusion_garrison": 2}[tid]
        # armoured trooper with a shield
        pygame.draw.rect(surf, theme.shade(col, -50), (x - 4 * k, y - 5 * k, 8 * k, 5 * k))
        pygame.draw.rect(surf, col, (x - 5 * k, y - 15 * k, 10 * k, 11 * k), border_radius=max(1, int(2 * k)))
        pygame.draw.circle(surf, theme.shade(col, 40), (int(x), int(y - 17 * k)), max(2, int(3 * k)))
        shield = pygame.Rect(0, 0, 9 * k, 12 * k)
        shield.center = (x - 7 * k, y - 8 * k)
        pygame.draw.ellipse(surf, [(150, 160, 170), (190, 120, 220), (120, 230, 255)][lvl], shield)
        pygame.draw.ellipse(surf, (10, 10, 10), shield, 1)
    elif tid == "colony_pod":
        pygame.draw.rect(surf, (40, 40, 40), (x - 10 * k, y - 3 * k, 20 * k, 4 * k), border_radius=max(1, int(2 * k)))
        dome = pygame.Rect(x - 9 * k, y - 15 * k, 18 * k, 16 * k)
        pygame.draw.ellipse(surf, (215, 222, 228), dome)
        pygame.draw.ellipse(surf, (245, 250, 252), (x - 5 * k, y - 13 * k, 7 * k, 5 * k))
        pygame.draw.rect(surf, col, (x - 9 * k, y - 7 * k, 18 * k, 3 * k))
        pygame.draw.ellipse(surf, (10, 10, 10), dome, 1)
    elif tid == "former":
        _rover(surf, x, y, (214, 180, 60), k)
        pygame.draw.line(surf, (90, 90, 90), (x - 12 * k, y + 1 * k), (x - 5 * k, y + 4 * k), max(2, int(3 * k)))
        pygame.draw.rect(surf, col, (x - 2 * k, y - 9 * k, 7 * k, 4 * k))
    elif tid in ("speeder", "impact_rover", "missile_rover"):
        _rover(surf, x, y, col, k, gun={"speeder": 1, "impact_rover": 2, "missile_rover": 3}[tid])
    elif tid == "grav_tank":
        _rover(surf, x, y, col, k, gun=3, hover=True)
    elif tid == "transport":
        _hull(surf, x, y, col, k, 15, cargo=True)
    elif tid == "gun_foil":
        _hull(surf, x, y, col, k, 12, tower=True)
    elif tid == "cruiser":
        _hull(surf, x, y, col, k, 18, tower=True)
    else:
        pygame.draw.circle(surf, col, (int(x), int(y - 6 * k)), int(7 * k))


def draw_unit(surf, game, u, cx, cy, tw, count=1, blink=False, small=False):
    k = tw / 64 * (1.0 if small else 1.3)
    col = game.players[u.owner].color
    x, y = cx, cy + 3 * k
    draw_unit_shape(surf, u, x, y, col, k)
    if tw < 48 and not blink:
        return
    # Faction flag with health bar and status letter, as in the classics.
    fw, fh = max(9, int(11 * k)), max(12, int(15 * k))
    fx, fy = x - 20 * k, y - 26 * k
    pole_col = (220, 220, 220)
    pygame.draw.line(surf, pole_col, (fx, fy), (fx, fy + fh + 6 * k), 1)
    flag = pygame.Rect(fx + 1, fy, fw, fh)
    pygame.draw.rect(surf, col, flag)
    hp = u.hp / 10
    hcol = (80, 220, 80) if hp > 0.6 else (230, 200, 60) if hp > 0.3 else (230, 70, 60)
    pygame.draw.rect(surf, (20, 20, 20), (flag.x + 1, flag.y + 1, 3, flag.height - 2))
    hh = int((flag.height - 2) * hp)
    pygame.draw.rect(surf, hcol, (flag.x + 1, flag.bottom - 1 - hh, 3, hh))
    status = {"fortify": "F", "sentry": "S", "terraform": "T", "auto": "A", "explore": "E", "goto": "G"}.get(u.orders, "")
    if u.terraform:
        status = str(u.terraform[1])
    lum = sum(col) / 3
    if status:
        theme.text(surf, status, (flag.x + 5, flag.y + 1), max(12, int(15 * k)),
                   (10, 10, 10) if lum > 150 else (255, 255, 255), bold=True)
    pygame.draw.rect(surf, (0, 0, 0), flag, 1)
    if count > 1:
        theme.text(surf, f"x{count}", (flag.x, flag.bottom + 2), max(12, int(15 * k)), (255, 255, 255), bold=True)


# ---------------------------------------------------------------------------
# The map view
# ---------------------------------------------------------------------------
class MapView:
    def __init__(self, game):
        self.game = game
        self.zoom_index = 2
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.minimap = None
        self.minimap_dirty = True
        self.rect = pygame.Rect(0, 0, 100, 100)
        self._fog = {}
        self._coast = None

    @property
    def z(self):
        return ZOOMS[self.zoom_index]

    @property
    def tw(self):
        return ZOOMS[self.zoom_index]

    # -- coordinates -----------------------------------------------------
    def tile_world_center(self, x, y):
        tw = self.tw
        return x * tw + (y & 1) * tw / 2 + tw / 2, y * tw / 4 + tw / 4

    def world_size(self):
        tw = self.tw
        return self.game.world.width * tw, (self.game.world.height + 1) * tw / 4

    def center_on(self, x, y):
        wx, wy = self.tile_world_center(x, y)
        self.cam_x = wx - self.rect.width / 2
        self.cam_y = wy - self.rect.height / 2
        self.clamp()

    def clamp(self):
        ww, wh = self.world_size()
        self.cam_x %= ww
        lo = -self.rect.height * 0.25
        hi = wh - self.rect.height * 0.75
        if hi < lo:
            self.cam_y = (wh - self.rect.height) / 2
        else:
            self.cam_y = max(lo, min(hi, self.cam_y))

    def zoom(self, delta, anchor=None):
        new = max(0, min(len(ZOOMS) - 1, self.zoom_index + delta))
        if new == self.zoom_index:
            return
        if anchor is None:
            anchor = self.rect.center
        ax, ay = anchor[0] - self.rect.x, anchor[1] - self.rect.y
        old = self.tw
        wx, wy = (self.cam_x + ax) / old, (self.cam_y + ay) / old
        self.zoom_index = new
        self.cam_x = wx * self.tw - ax
        self.cam_y = wy * self.tw - ay
        self.clamp()

    def pan(self, dx, dy):
        self.cam_x -= dx
        self.cam_y -= dy
        self.clamp()

    def screen_to_tile(self, pos):
        if not self.rect.collidepoint(pos):
            return None
        tw = self.tw
        hw, hh = tw / 2, tw / 4
        wx = pos[0] - self.rect.x + self.cam_x
        wy = pos[1] - self.rect.y + self.cam_y
        world = self.game.world
        row0 = int(math.floor(wy / hh))
        best, best_d = None, 9.0
        for r in (row0 - 1, row0):
            if not 0 <= r < world.height:
                continue
            off = (r & 1) * hw
            c0 = int(math.floor((wx - off) / tw))
            for c in (c0 - 1, c0, c0 + 1):
                cx = c * tw + off + hw
                cy = r * hh + hh
                d = abs(wx - cx) / hw + abs(wy - cy) / hh
                if d < best_d:
                    best_d, best = d, (c % world.width, r)
        return best

    def tile_screen_center(self, x, y):
        """Screen centre of the first on-screen copy of a tile (or None if off-view)."""
        ww, _ = self.world_size()
        wx, wy = self.tile_world_center(x, y)
        sx = (wx - self.cam_x) % ww
        sy = wy - self.cam_y
        if sx > self.rect.width + self.tw or sy < -self.tw or sy > self.rect.height + self.tw:
            return None
        return self.rect.x + sx, self.rect.y + sy

    def tile_on_screen(self, x, y):
        """Top-left of a tile's bounding box on screen (or None)."""
        c = self.tile_screen_center(x, y)
        if c is None:
            return None
        return c[0] - self.tw / 2, c[1] - self.tw / 4

    def is_on_screen(self, x, y, margin=2):
        ww, _ = self.world_size()
        wx, wy = self.tile_world_center(x, y)
        sx = (wx - self.cam_x) % ww
        sy = wy - self.cam_y
        m = margin * self.tw / 2
        return m <= sx <= self.rect.width - m and m <= sy <= self.rect.height - m

    # -- caches --------------------------------------------------------------
    def invalidate(self):
        self.minimap_dirty = True
        self._coast = None

    def refresh_dirty(self):
        if self.game.dirty_tiles:
            self.game.dirty_tiles.clear()
            self.minimap_dirty = True
            self._coast = None

    def _fog_sprite(self, tw, alpha):
        key = (tw, alpha)
        if key not in self._fog:
            s = pygame.Surface((tw, tw // 2), pygame.SRCALPHA)
            pygame.draw.polygon(s, (0, 0, 0, alpha), diamond(tw / 2, tw / 4, tw, -0.5))
            self._fog[key] = s
        return self._fog[key]

    def _coasts(self):
        if self._coast is None:
            world = self.game.world
            coast = {}
            for t in world.all_tiles():
                if t.is_ocean:
                    dirs = []
                    for d in ("NE", "SE", "SW", "NW"):
                        p = world.step(t.x, t.y, d)
                        if p and world.tiles[p[0]][p[1]].is_land:
                            dirs.append(d)
                    if dirs:
                        coast[(t.x, t.y)] = dirs
            self._coast = coast
        return self._coast

    def _visible_tiles(self):
        """(tile_x, tile_y, screen_cx, screen_cy) for every tile in view, back to front."""
        tw = self.tw
        hw, hh = tw / 2, tw / 4
        world = self.game.world
        out = []
        r0 = max(0, int(self.cam_y // hh) - 2)
        r1 = min(world.height - 1, int((self.cam_y + self.rect.height) // hh) + 2)
        for r in range(r0, r1 + 1):
            off = (r & 1) * hw
            c0 = int(math.floor((self.cam_x - off) / tw)) - 1
            c1 = int(math.floor((self.cam_x + self.rect.width - off) / tw)) + 1
            sy = self.rect.y + r * hh + hh - self.cam_y
            for c in range(c0, c1 + 1):
                sx = self.rect.x + c * tw + off + hw - self.cam_x
                out.append((c % world.width, r, sx, sy))
        return out

    # -- drawing ---------------------------------------------------------------
    def draw(self, surf, pid, selected=None, hover=None, path=None, ticks=0):
        self.refresh_dirty()
        game = self.game
        world = game.world
        tw = self.tw
        hw, hh = tw / 2, tw / 4
        rect = self.rect
        surf.set_clip(rect)
        surf.fill((4, 6, 10), rect)
        player = game.players[pid]
        explored, visible = player.explored, player.visible
        W = world.width
        tiles = self._visible_tiles()
        coasts = self._coasts()
        fog = self._fog_sprite(tw, 120)
        black = self._fog_sprite(tw, 255)
        bp = game.base_pos

        # 1. terrain sprites (with improvements), coastline surf, roads
        for tx, ty, cx, cy in tiles:
            if not explored[ty * W + tx]:
                continue
            t = world.tiles[tx][ty]
            surf.blit(tile_sprite(world, t, tw), (cx - hw, cy - hh))
        for tx, ty, cx, cy in tiles:
            if not explored[ty * W + tx]:
                continue
            t = world.tiles[tx][ty]
            dirs = coasts.get((tx, ty))
            if dirs:
                for d in dirs:
                    a, b = edge_points(cx, cy, tw, d, inset=2)
                    pygame.draw.line(surf, (150, 200, 210), a, b, max(1, tw // 32))
            draw_roads(surf, world, t, cx, cy, tw, bp)

        # 2. bases (under the fog, so remembered bases show dimmed)
        for tx, ty, cx, cy in tiles:
            bid = bp.get((tx, ty))
            if bid is not None and explored[ty * W + tx]:
                draw_base(surf, game, game.bases[bid], cx, cy, tw)

        # 3. fog of war, 4. territory borders
        for tx, ty, cx, cy in tiles:
            idx = ty * W + tx
            if not explored[idx]:
                surf.blit(black, (cx - hw, cy - hh))
            elif not visible[idx]:
                surf.blit(fog, (cx - hw, cy - hh))
        for tx, ty, cx, cy in tiles:
            if not explored[ty * W + tx]:
                continue
            t = world.tiles[tx][ty]
            if t.owner is None:
                continue
            col = game.players[t.owner].color
            for d in ("NE", "SE", "SW", "NW"):
                p = world.step(tx, ty, d)
                if p is None or world.tiles[p[0]][p[1]].owner != t.owner:
                    a, b = edge_points(cx, cy, tw, d, inset=max(2, tw // 24))
                    pygame.draw.line(surf, col, a, b, max(2, tw // 28))

        # 5. selection marker, then units
        sel_id = selected.id if selected else None
        if selected and selected.id in game.units:
            c = self.tile_screen_center(selected.x, selected.y)
            if c:
                pulse = 0.5 + 0.5 * math.sin(ticks / 160)
                colr = theme.mix((80, 220, 200), (255, 255, 255), pulse)
                pygame.draw.polygon(surf, colr, diamond(c[0], c[1], tw, 1), max(2, tw // 24))
        for tx, ty, cx, cy in tiles:
            idx = ty * W + tx
            ids = game.unit_pos.get((tx, ty))
            if not ids or not visible[idx]:
                continue
            units = [game.units[i] for i in ids]
            if sel_id in ids:
                top = game.units[sel_id]
            else:
                free = [u for u in units if not u.carried_by] or units
                top = max(free, key=lambda u: (u.type.capacity > 0, u.type.defense + u.type.attack))
            is_sel = top.id == sel_id
            if (tx, ty) in bp:
                # Units in a base stand at its front edge so they stay visible and clickable.
                draw_unit(surf, game, top, cx + hw * 0.45, cy + hh * 0.35, tw, len(units), is_sel, small=not is_sel)
            else:
                draw_unit(surf, game, top, cx, cy, tw, len(units), is_sel)

        # 6. goto path preview, hover outline
        if path and selected:
            from game.pathfinding import turns_for_path
            for i, (px, py) in enumerate(path):
                c = self.tile_screen_center(px, py)
                if c is None:
                    continue
                if i == len(path) - 1:
                    n = turns_for_path(game, selected, path)
                    pygame.draw.polygon(surf, (255, 255, 255), diamond(c[0], c[1], tw, 3), 2)
                    theme.text(surf, str(n), c, max(16, tw // 3), (255, 255, 255), bold=True, center=True)
                else:
                    pygame.draw.ellipse(surf, (255, 255, 255), (c[0] - tw / 16, c[1] - tw / 32, tw / 8, tw / 16))
        if hover:
            c = self.tile_screen_center(*hover)
            if c:
                pygame.draw.polygon(surf, (235, 245, 240), diamond(c[0], c[1], tw, 1), 1)
        surf.set_clip(None)

    # -- minimap ---------------------------------------------------------------
    def draw_minimap(self, surf, rect, pid):
        game = self.game
        world = game.world
        # One half-column is s pixels wide and one row s/2 tall, matching the map's proportions.
        s = min(rect.width / (world.width * 2 + 1), rect.height / (world.height / 2 + 1))
        mw, mh = int((world.width * 2 + 1) * s), int((world.height / 2 + 1) * s)
        if self.minimap_dirty or self.minimap is None or self.minimap.get_size() != (mw, mh):
            mm = pygame.Surface((mw, mh))
            mm.fill((4, 6, 10))
            p = game.players[pid]
            W = world.width
            for t in world.all_tiles():
                idx = t.y * W + t.x
                if not p.explored[idx]:
                    continue
                if t.is_ocean:
                    col = theme.mix(DEEP, SHELF, 0.6 if t.is_shelf else 0.1)
                elif t.fungus:
                    col = FUNGUS_COLOR
                else:
                    col = terrain_color(t)
                if t.owner is not None:
                    col = theme.mix(col, game.players[t.owner].color, 0.45)
                if (t.x, t.y) in game.base_pos:
                    col = (255, 255, 255)
                if not p.visible[idx]:
                    col = theme.shade(col, -40)
                x0 = int((2 * t.x + (t.y & 1)) * s)
                y0 = int(t.y * s / 2)
                mm.fill(col, (x0, y0, max(1, int(2 * s + 0.99)), max(1, int(s / 2 + 0.99))))
            self.minimap = mm
            self.minimap_dirty = False
        dest = self.minimap.get_rect(center=rect.center)
        surf.blit(self.minimap, dest)
        tw = self.tw
        vx = self.cam_x / tw * 2 * s
        vy = self.cam_y / (tw / 4) * s / 2
        vw = self.rect.width / tw * 2 * s
        vh = self.rect.height / (tw / 4) * s / 2
        surf.set_clip(dest)
        for off in (0, -self.minimap.get_width(), self.minimap.get_width()):
            pygame.draw.rect(surf, (255, 255, 255), (dest.x + vx + off, dest.y + vy, vw, vh), 1)
        surf.set_clip(None)
        return dest, s

    def minimap_click(self, pos, dest, scale):
        if not dest.collidepoint(pos):
            return False
        ty = int((pos[1] - dest.y) / (scale / 2))
        ty = max(0, min(self.game.world.height - 1, ty))
        tx = int(((pos[0] - dest.x) / scale - (ty & 1)) / 2) % self.game.world.width
        self.center_on(tx, ty)
        return True
