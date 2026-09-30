"""A slowly rotating, lit planet for the title screen (and the window icon).

The surface texture is generated from the same terrain generator as the game. Each frame the
visible hemisphere is projected orthographically with pure pygame operations: the texture is
warped vertically and horizontally in bands (for the sphere's curvature), then every row is
squeezed to the width of the disc at that latitude, and a lighting overlay is added on top.
"""
import math
import random

import pygame

from game.world import generate_world
from . import theme
from .renderer import terrain_color, FUNGUS_COLOR

BANDS = 28


def _texture(seed, w=512, h=256):
    world = generate_world(96, 48, seed, land_fraction=0.4)
    small = pygame.Surface((world.width, world.height))
    for t in world.all_tiles():
        if t.is_ocean:
            col = theme.mix((10, 36, 72), (30, 96, 124), max(0.0, min(1.0, (t.elevation + 3000) / 3000)) ** 1.5)
        elif t.fungus:
            col = FUNGUS_COLOR
        else:
            col = terrain_color(t)
        lat = abs(t.y / world.height - 0.5) * 2
        if lat > 0.86:
            col = theme.mix(col, (228, 236, 240), min(1.0, (lat - 0.86) * 7))
        small.set_at((t.x, t.y), col)
    tex = pygame.transform.smoothscale(small, (w, h))
    # A few wispy cloud bands.
    # Wispy clouds, drawn small and scaled up so their edges are soft.
    cw, ch = w // 8, h // 8
    clouds = pygame.Surface((cw, ch), pygame.SRCALPHA)
    rng = random.Random(seed)
    for _ in range(40):
        x, y = rng.uniform(0, cw), rng.uniform(ch * 0.1, ch * 0.9)
        rx, ry = rng.uniform(2, 8), rng.uniform(0.6, 1.4)
        layer = pygame.Surface((cw, ch), pygame.SRCALPHA)
        pygame.draw.ellipse(layer, (255, 255, 255, rng.randint(50, 110)), (x - rx, y - ry, 2 * rx, 2 * ry))
        clouds.blit(layer, (0, 0))
    tex.blit(pygame.transform.smoothscale(clouds, (w, h)), (0, 0))
    # Double it horizontally so any 180-degree window can be cut without wrapping.
    out = pygame.Surface((w * 2, h))
    out.blit(tex, (0, 0))
    out.blit(tex, (w, 0))
    return out


class Globe:
    def __init__(self, diameter, seed=2101):
        self.d = int(diameter)
        self.tex = _texture(seed)
        self.tw = self.tex.get_width() // 2
        self.th = self.tex.get_height()
        self.overlay = self._lighting()
        self.frame = pygame.Surface((self.d, self.d), pygame.SRCALPHA)

    def _lighting(self):
        d = self.d
        r = d / 2
        pad = 24
        s = pygame.Surface((d + 2 * pad, d + 2 * pad), pygame.SRCALPHA)
        c = (d + 2 * pad) / 2

        def blend_circle(target, color, center, radius):
            layer = pygame.Surface(target.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(layer, color, center, radius)
            target.blit(layer, (0, 0))

        # atmosphere glow: a teal haze that fades outwards
        for i in range(pad, 0, -1):
            layer = pygame.Surface(s.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(layer, (80, 200, 190, int(60 * (1 - i / pad) ** 2)), (c, c), r + i, 2)
            s.blit(layer, (0, 0))
        disc = pygame.Surface((d, d), pygame.SRCALPHA)
        # the night side, darkening towards the lower right
        for i in range(22):
            f = i / 22
            blend_circle(disc, (0, 0, 10, 14), (r + r * 0.9 * f, r + r * 0.7 * f), r * (1.05 - f * 0.35))
        # specular glint on the day side
        for i in range(10):
            blend_circle(disc, (255, 250, 230, 6), (r * 0.62, r * 0.55), r * (0.45 - i * 0.04))
        mask = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (r, r), r)
        disc.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        s.blit(disc, (pad, pad))
        return s

    def render(self, angle):
        """angle in [0, 1): fraction of a full rotation."""
        d, r = self.d, self.d / 2
        tw, th = self.tw, self.th
        start = int(angle * tw) % tw
        window = self.tex.subsurface((start, 0, tw // 2, th))   # 180 degrees of longitude
        # Vertical warp: disc row y corresponds to latitude asin(y).
        vert = pygame.Surface((tw // 2, d))
        for i in range(BANDS):
            y0, y1 = -1 + 2 * i / BANDS, -1 + 2 * (i + 1) / BANDS
            t0 = (math.asin(y0) / math.pi + 0.5) * th
            t1 = (math.asin(y1) / math.pi + 0.5) * th
            src = window.subsurface((0, int(t0), tw // 2, max(1, int(math.ceil(t1)) - int(t0))))
            dy0, dy1 = int((y0 + 1) * r), int(math.ceil((y1 + 1) * r))
            vert.blit(pygame.transform.smoothscale(src, (tw // 2, max(1, dy1 - dy0))), (0, dy0))
        # Horizontal warp: disc column x corresponds to longitude asin(x).
        warped = pygame.Surface((d, d))
        for i in range(BANDS):
            x0, x1 = -1 + 2 * i / BANDS, -1 + 2 * (i + 1) / BANDS
            s0 = (math.asin(x0) / math.pi + 0.5) * (tw // 2)
            s1 = (math.asin(x1) / math.pi + 0.5) * (tw // 2)
            src = vert.subsurface((int(s0), 0, max(1, min(tw // 2 - int(s0), int(math.ceil(s1)) - int(s0))), d))
            dx0, dx1 = int((x0 + 1) * r), int(math.ceil((x1 + 1) * r))
            warped.blit(pygame.transform.smoothscale(src, (max(1, dx1 - dx0), d)), (dx0, 0))
        # Squeeze each row to the disc.
        self.frame.fill((0, 0, 0, 0))
        for y in range(d):
            yy = (y + 0.5 - r) / r
            half = math.sqrt(max(0.0, 1 - yy * yy)) * r
            wdt = int(half * 2)
            if wdt <= 0:
                continue
            row = pygame.transform.scale(warped.subsurface((0, y, d, 1)), (wdt, 1))
            self.frame.blit(row, (int(r - half), y))
        return self.frame

    def draw(self, surf, center, angle):
        frame = self.render(angle)
        cx, cy = center
        o = self.overlay
        surf.blit(frame, (cx - self.d / 2, cy - self.d / 2))
        surf.blit(o, (cx - o.get_width() / 2, cy - o.get_height() / 2))


def make_icon(size=32):
    g = Globe(size - 4, seed=7)
    icon = pygame.Surface((size, size), pygame.SRCALPHA)
    frame = g.render(0.2)
    icon.blit(frame, (2, 2))
    pygame.draw.circle(icon, (110, 220, 200), (size / 2, size / 2), size / 2 - 1, 1)
    return icon
