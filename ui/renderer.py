"""Map drawing: cached terrain layers, units, bases, borders, fog of war and the minimap."""
import math
import random

import pygame

from game.world import ARID, MOIST, RAINY, FLAT, ROLLING, ROCKY
from . import theme

ZOOMS = [16, 24, 32, 48, 64]

LAND_COLORS = {ARID: (170, 146, 98), MOIST: (122, 142, 74), RAINY: (74, 128, 66)}
ROCK_COLOR = (128, 118, 106)
FUNGUS_COLOR = (178, 64, 112)
DEEP = (16, 36, 88)
SHELF = (36, 78, 138)


def terrain_color(t):
    if t.is_ocean:
        f = (t.elevation + 3000) / 3000
        return theme.mix(DEEP, SHELF, max(0.0, min(1.0, f)) ** 1.5)
    c = LAND_COLORS[t.rainfall]
    if t.rockiness == ROCKY:
        c = theme.mix(c, ROCK_COLOR, 0.6)
    elif t.rockiness == ROLLING:
        c = theme.mix(c, ROCK_COLOR, 0.2)
    return theme.shade(c, t.elevation / 3500 * 22 - 6)


def draw_tile(surf, world, t, px, py, z, base_positions=()):
    """Draw one terrain tile (no units/bases) at pixel (px, py) with size z."""
    rng = random.Random(t.x * 7919 + t.y * 104729)
    col = terrain_color(t)
    pygame.draw.rect(surf, col, (px, py, z, z))
    # texture speckles
    if z >= 16:
        for _ in range(3 if z < 32 else 6):
            sx = px + rng.randrange(z)
            sy = py + rng.randrange(z)
            pygame.draw.rect(surf, theme.shade(col, rng.choice((-14, 12))), (sx, sy, max(1, z // 16), max(1, z // 16)))
    if t.is_land and t.rockiness == ROCKY and z >= 16:
        for _ in range(2):
            cx = px + rng.randrange(z // 5, z - z // 5)
            cy = py + rng.randrange(z // 3, z - z // 6)
            s = z // 5
            pygame.draw.polygon(surf, theme.shade(ROCK_COLOR, -30), [(cx - s, cy + s // 2), (cx, cy - s), (cx + s, cy + s // 2)])
            pygame.draw.polygon(surf, theme.shade(ROCK_COLOR, 25), [(cx - s // 3, cy - s // 2), (cx, cy - s), (cx + s // 4, cy - s // 2)])
    elif t.is_land and t.rockiness == ROLLING and z >= 24:
        for i in range(2):
            cy = py + z // 3 + i * z // 3
            pygame.draw.arc(surf, theme.shade(col, -22), (px + z // 6, cy - z // 8, z * 2 // 3, z // 4), 0.2, math.pi - 0.2, 1)
    imp = t.improvements
    if "farm" in imp:
        c = (214, 196, 110)
        step = max(3, z // 5)
        for i in range(step // 2, z, step):
            pygame.draw.line(surf, c, (px + 2, py + i), (px + z - 3, py + i), max(1, z // 20))
    if "forest" in imp:
        for i in range(3):
            cx = px + [z // 4, 3 * z // 4, z // 2][i]
            cy = py + [z // 3, z // 3, 2 * z // 3][i]
            s = max(3, z // 6)
            pygame.draw.polygon(surf, (28, 80, 38), [(cx - s, cy + s), (cx, cy - s), (cx + s, cy + s)])
            pygame.draw.line(surf, (70, 50, 30), (cx, cy + s), (cx, cy + s + s // 2), max(1, z // 24))
    if t.fungus:
        fc = FUNGUS_COLOR if t.is_land else (140, 60, 120)
        for _ in range(4 if z < 32 else 7):
            cx = px + rng.randrange(z)
            cy = py + rng.randrange(z)
            r = rng.randrange(max(2, z // 10), max(3, z // 4))
            pygame.draw.circle(surf, theme.shade(fc, rng.randrange(-20, 20)), (cx, cy), r)
        if z >= 32:
            for _ in range(3):
                cx = px + rng.randrange(z)
                cy = py + rng.randrange(z)
                pygame.draw.circle(surf, (230, 130, 170), (cx, cy), max(1, z // 20))
    if "mine" in imp:
        s = max(4, z // 4)
        cx, cy = px + z // 2, py + z // 2 + s // 3
        pygame.draw.polygon(surf, (60, 55, 50), [(cx - s, cy + s // 2), (cx, cy - s // 2 - 2), (cx + s, cy + s // 2)])
        pygame.draw.rect(surf, (20, 18, 16), (cx - s // 3, cy, 2 * s // 3, s // 2))
    if "solar" in imp:
        s = max(4, z // 3)
        r = pygame.Rect(px + z - s - 2, py + 2, s, s * 2 // 3)
        pygame.draw.rect(surf, (40, 70, 150), r)
        pygame.draw.rect(surf, (240, 210, 90), r, 1)
        pygame.draw.line(surf, (240, 210, 90), (r.centerx, r.top), (r.centerx, r.bottom), 1)
    if "road" in imp or (t.x, t.y) in base_positions:
        cx, cy = px + z // 2, py + z // 2
        linked = False
        for nx, ny in world.neighbors(t.x, t.y):
            n = world.tiles[nx][ny]
            if "road" in n.improvements or (nx, ny) in base_positions:
                dx = world.signed_dx(t.x, nx)
                dy = ny - t.y
                pygame.draw.line(surf, (120, 92, 60), (cx, cy), (cx + dx * z // 2, cy + dy * z // 2), max(2, z // 10))
                linked = True
        if not linked:
            pygame.draw.circle(surf, (120, 92, 60), (cx, cy), max(2, z // 8))
    if t.special:
        s = max(3, z // 7)
        cx, cy = px + s + 2, py + z - s - 2
        if t.special == "nutrient":
            pygame.draw.circle(surf, (60, 200, 70), (cx, cy), s)
            pygame.draw.circle(surf, (230, 255, 220), (cx, cy), s, 1)
        elif t.special == "mineral":
            pygame.draw.polygon(surf, (150, 160, 220), [(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)])
            pygame.draw.polygon(surf, (240, 240, 255), [(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], 1)
        else:
            pygame.draw.circle(surf, (250, 220, 60), (cx, cy), s)
            pygame.draw.circle(surf, (255, 255, 200), (cx, cy), s, 1)
    if t.supply_pod:
        s = max(4, z // 4)
        r = pygame.Rect(px + z // 2 - s // 2, py + z // 2 - s // 2, s, s)
        pygame.draw.rect(surf, (200, 230, 240), r)
        pygame.draw.rect(surf, (40, 120, 160), r, max(1, z // 24))
        pygame.draw.line(surf, (40, 120, 160), r.midtop, r.midbottom, 1)


class MapView:
    def __init__(self, game):
        self.game = game
        self.zoom_index = 2
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.layers = {}
        self.fog_tiles = {}
        self.minimap = None
        self.minimap_dirty = True
        self.rect = pygame.Rect(0, 0, 100, 100)

    @property
    def z(self):
        return ZOOMS[self.zoom_index]

    # -- camera --------------------------------------------------------
    def center_on(self, x, y):
        z = self.z
        self.cam_x = (x + 0.5) * z - self.rect.width / 2
        self.cam_y = (y + 0.5) * z - self.rect.height / 2
        self.clamp()

    def clamp(self):
        z = self.z
        mw = self.game.world.width * z
        mh = self.game.world.height * z
        self.cam_x %= mw
        lo = -self.rect.height * 0.3
        hi = mh - self.rect.height * 0.7
        if hi < lo:
            self.cam_y = (mh - self.rect.height) / 2
        else:
            self.cam_y = max(lo, min(hi, self.cam_y))

    def zoom(self, delta, anchor=None):
        new = max(0, min(len(ZOOMS) - 1, self.zoom_index + delta))
        if new == self.zoom_index:
            return
        if anchor is None:
            anchor = self.rect.center
        ax, ay = anchor[0] - self.rect.x, anchor[1] - self.rect.y
        old = self.z
        wx, wy = (self.cam_x + ax) / old, (self.cam_y + ay) / old
        self.zoom_index = new
        self.cam_x = wx * self.z - ax
        self.cam_y = wy * self.z - ay
        self.clamp()

    def pan(self, dx, dy):
        self.cam_x -= dx
        self.cam_y -= dy
        self.clamp()

    def screen_to_tile(self, pos):
        if not self.rect.collidepoint(pos):
            return None
        z = self.z
        wx = pos[0] - self.rect.x + self.cam_x
        wy = pos[1] - self.rect.y + self.cam_y
        tx = int(wx // z) % self.game.world.width
        ty = int(wy // z)
        if not 0 <= ty < self.game.world.height:
            return None
        return tx, ty

    def tile_on_screen(self, x, y):
        """Screen position of a tile's top-left (first wrapped copy), or None if off-view."""
        z = self.z
        mw = self.game.world.width * z
        px = (x * z - self.cam_x) % mw
        py = y * z - self.cam_y
        if px > self.rect.width or py < -z or py > self.rect.height:
            return None
        return self.rect.x + px, self.rect.y + py

    def is_on_screen(self, x, y, margin=2):
        z = self.z
        mw = self.game.world.width * z
        px = (x * z - self.cam_x) % mw
        py = y * z - self.cam_y
        return margin * z <= px <= self.rect.width - margin * z and margin * z <= py <= self.rect.height - margin * z

    # -- terrain cache ---------------------------------------------------
    def invalidate(self):
        self.layers = {}
        self.minimap_dirty = True

    def _layer(self):
        z = self.z
        if z not in self.layers:
            world = self.game.world
            surf = pygame.Surface((world.width * z, world.height * z))
            bp = self.game.base_pos
            for t in world.all_tiles():
                draw_tile(surf, world, t, t.x * z, t.y * z, z, bp)
            self.layers[z] = surf
        return self.layers[z]

    def refresh_dirty(self):
        game = self.game
        if not game.dirty_tiles:
            return
        world = game.world
        tiles = set()
        for (x, y) in game.dirty_tiles:
            tiles.add((x, y))
            tiles.update(world.neighbors(x, y))
        game.dirty_tiles.clear()
        bp = game.base_pos
        for z, surf in self.layers.items():
            for x, y in tiles:
                draw_tile(surf, world, world.tiles[x][y], x * z, y * z, z, bp)
        self.minimap_dirty = True

    def _fog_tile(self):
        z = self.z
        if z not in self.fog_tiles:
            s = pygame.Surface((z, z), pygame.SRCALPHA)
            s.fill((0, 0, 0, 120))
            self.fog_tiles[z] = s
        return self.fog_tiles[z]

    # -- drawing ------------------------------------------------------------
    def draw(self, surf, pid, selected=None, hover=None, path=None, ticks=0):
        self.refresh_dirty()
        game = self.game
        world = game.world
        z = self.z
        rect = self.rect
        surf.set_clip(rect)
        surf.fill((0, 0, 0), rect)
        layer = self._layer()
        mw = world.width * z

        # Terrain, tiled horizontally for the wrap-around.
        start = -(self.cam_x % mw)
        x = start
        while x < rect.width:
            surf.blit(layer, (rect.x + x, rect.y - self.cam_y))
            x += mw

        player = game.players[pid]
        explored = player.explored
        visible = player.visible
        W = world.width
        fog = self._fog_tile()
        first_tx = int(self.cam_x // z)
        first_ty = max(0, int(self.cam_y // z))
        off_x = rect.x - (self.cam_x - first_tx * z)
        off_y = rect.y - (self.cam_y - first_ty * z)
        cols = rect.width // z + 2
        rows = rect.height // z + 2
        players = game.players

        # Pass 1: fog and borders
        for cy in range(rows):
            ty = first_ty + cy
            if ty >= world.height:
                break
            py = off_y + cy * z
            for cx in range(cols):
                tx = (first_tx + cx) % W
                px = off_x + cx * z
                idx = ty * W + tx
                if not explored[idx]:
                    pygame.draw.rect(surf, (0, 0, 0), (px, py, z, z))
                    continue
                t = world.tiles[tx][ty]
                if t.owner is not None:
                    col = players[t.owner].color
                    right = world.tiles[(tx + 1) % W][ty]
                    if right.owner != t.owner:
                        pygame.draw.line(surf, col, (px + z - 2, py), (px + z - 2, py + z - 1), 2)
                    left = world.tiles[(tx - 1) % W][ty]
                    if left.owner != t.owner:
                        pygame.draw.line(surf, col, (px + 1, py), (px + 1, py + z - 1), 2)
                    if ty > 0 and world.tiles[tx][ty - 1].owner != t.owner:
                        pygame.draw.line(surf, col, (px, py + 1), (px + z - 1, py + 1), 2)
                    if ty < world.height - 1 and world.tiles[tx][ty + 1].owner != t.owner:
                        pygame.draw.line(surf, col, (px, py + z - 2), (px + z - 1, py + z - 2), 2)
                if not visible[idx]:
                    surf.blit(fog, (px, py))

        # Pass 2: bases and units
        sel_id = selected.id if selected else None
        for cy in range(rows):
            ty = first_ty + cy
            if ty >= world.height:
                break
            py = off_y + cy * z
            for cx in range(cols):
                tx = (first_tx + cx) % W
                px = off_x + cx * z
                idx = ty * W + tx
                if not explored[idx]:
                    continue
                bid = game.base_pos.get((tx, ty))
                if bid is not None:
                    self._draw_base(surf, game.bases[bid], px, py, z)
                ids = game.unit_pos.get((tx, ty))
                if ids and (visible[idx]):
                    units = [game.units[i] for i in ids]
                    top = None
                    if sel_id in ids:
                        top = game.units[sel_id]
                    else:
                        free = [u for u in units if not u.carried_by] or units
                        top = max(free, key=lambda u: (u.type.capacity > 0, u.type.defense + u.type.attack))
                    blink = top.id == sel_id and (ticks // 300) % 2 == 0
                    self._draw_unit(surf, top, px, py, z, len(units), bid is not None, blink)

        # Goto path preview
        if path and selected:
            from game.pathfinding import turns_for_path
            for i, (px_, py_) in enumerate(path):
                pos = self.tile_on_screen(px_, py_)
                if pos is None:
                    continue
                c = (pos[0] + z // 2, pos[1] + z // 2)
                if i == len(path) - 1:
                    n = turns_for_path(game, selected, path)
                    pygame.draw.circle(surf, (255, 255, 255), c, max(6, z // 4), 2)
                    theme.text(surf, str(n), c, max(14, z // 2), (255, 255, 255), bold=True, center=True)
                else:
                    pygame.draw.circle(surf, (255, 255, 255), c, max(2, z // 10))

        if hover:
            pos = self.tile_on_screen(*hover)
            if pos:
                pygame.draw.rect(surf, (255, 255, 255), (pos[0], pos[1], z, z), 1)
        surf.set_clip(None)

    def _draw_base(self, surf, base, px, py, z):
        col = self.game.players[base.owner].color
        m = max(2, z // 8)
        r = pygame.Rect(px + m, py + m, z - 2 * m, z - 2 * m)
        pygame.draw.rect(surf, theme.shade(col, -60), r, border_radius=max(2, z // 6))
        inner = r.inflate(-max(2, z // 8), -max(2, z // 8))
        pygame.draw.rect(surf, col, inner, border_radius=max(2, z // 8))
        # domes
        if z >= 24:
            for i, dx in enumerate((-z // 5, z // 6)):
                pygame.draw.circle(surf, theme.shade(col, 60), (r.centerx + dx, r.centery + z // 10), max(2, z // (6 + i)))
        pygame.draw.rect(surf, (15, 15, 15), r, 1, border_radius=max(2, z // 6))
        size = max(12, int(z * 0.55))
        lum = sum(col) / 3
        tc = (10, 10, 10) if lum > 150 else (255, 255, 255)
        theme.text(surf, base.pop, (r.x + max(3, z // 8), r.y + 1), size, tc, bold=True)
        if z >= 24:
            label = theme.font(max(14, z // 2)).render(base.name, True, (255, 255, 255))
            lr = label.get_rect(midtop=(px + z // 2, py + z - 1))
            bg = lr.inflate(6, 0)
            s = pygame.Surface(bg.size, pygame.SRCALPHA)
            s.fill((0, 0, 0, 150))
            surf.blit(s, bg)
            pygame.draw.line(surf, col, bg.bottomleft, bg.bottomright, 2)
            surf.blit(label, lr)

    def _draw_unit(self, surf, u, px, py, z, count, in_base, blink):
        col = self.game.players[u.owner].color
        cx, cy = px + z // 2, py + z // 2
        if in_base:
            cx, cy = px + z * 2 // 3, py + z // 3
        r = max(5, int(z * (0.32 if not in_base else 0.26)))
        if u.type.native:
            for i in range(3):
                pygame.draw.circle(surf, (230, 110, 170), (cx + int(math.cos(i * 2.1) * r / 2), cy + int(math.sin(i * 2.1) * r / 2)), r // 2 + 1)
            pygame.draw.circle(surf, (90, 20, 60), (cx, cy), r, 2)
        else:
            if u.type.domain == "sea":
                pts = [(cx - r, cy - r // 2), (cx + r, cy - r // 2), (cx + r // 2, cy + r), (cx - r // 2, cy + r)]
                pygame.draw.polygon(surf, col, pts)
                pygame.draw.polygon(surf, (10, 10, 10), pts, 1)
            elif u.fortified or u.orders == "fortify":
                rr = pygame.Rect(cx - r, cy - r, 2 * r, 2 * r)
                pygame.draw.rect(surf, col, rr)
                pygame.draw.rect(surf, (10, 10, 10), rr, 2)
            else:
                pygame.draw.circle(surf, col, (cx, cy), r)
                pygame.draw.circle(surf, (10, 10, 10), (cx, cy), r, 1)
            lum = sum(col) / 3
            tc = (10, 10, 10) if lum > 150 else (255, 255, 255)
            theme.text(surf, u.type.symbol, (cx, cy + 1), max(12, int(r * 1.6)), tc, bold=True, center=True)
        if z >= 24:
            # health bar
            hb = pygame.Rect(cx - r, cy - r - 4, 2 * r, 3)
            theme.bar(surf, hb, u.hp / 10, (80, 220, 80) if u.hp > 6 else (230, 200, 60) if u.hp > 3 else (230, 70, 60))
        if count > 1 and z >= 24:
            theme.text(surf, count, (px + z - 2, py + z - 14), 16, (255, 255, 255), bold=True, right=True)
        if u.terraform and z >= 24:
            theme.text(surf, u.terraform[1], (px + 2, py + 2), 14, (255, 240, 150), bold=True)
        if blink:
            pygame.draw.rect(surf, (255, 255, 255), (px + 1, py + 1, z - 2, z - 2), 2)

    # -- minimap -------------------------------------------------------------
    def draw_minimap(self, surf, rect, pid):
        game = self.game
        world = game.world
        scale = max(1, min(rect.width // world.width, rect.height // world.height))
        if self.minimap_dirty or self.minimap is None or self.minimap.get_width() != world.width * scale:
            mm = pygame.Surface((world.width * scale, world.height * scale))
            p = game.players[pid]
            W = world.width
            for t in world.all_tiles():
                idx = t.y * W + t.x
                if not p.explored[idx]:
                    col = (0, 0, 0)
                else:
                    if t.is_ocean:
                        col = (30, 60, 120)
                    elif t.fungus:
                        col = (150, 60, 100)
                    else:
                        col = LAND_COLORS[t.rainfall]
                    if t.owner is not None:
                        col = theme.mix(col, game.players[t.owner].color, 0.45)
                    if (t.x, t.y) in game.base_pos:
                        col = (255, 255, 255)
                    if not p.visible[idx]:
                        col = theme.shade(col, -40)
                mm.fill(col, (t.x * scale, t.y * scale, scale, scale))
            self.minimap = mm
            self.minimap_dirty = False
        dest = self.minimap.get_rect(center=rect.center)
        surf.blit(self.minimap, dest)
        # viewport rectangle
        z = self.z
        vx = self.cam_x / z * scale
        vy = self.cam_y / z * scale
        vw = self.rect.width / z * scale
        vh = self.rect.height / z * scale
        surf.set_clip(dest)
        for off in (0, -self.minimap.get_width()):
            pygame.draw.rect(surf, (255, 255, 255), (dest.x + vx + off, dest.y + vy, vw, vh), 1)
        surf.set_clip(None)
        return dest, scale

    def minimap_click(self, pos, dest, scale):
        if not dest.collidepoint(pos):
            return False
        tx = (pos[0] - dest.x) // scale
        ty = (pos[1] - dest.y) // scale
        self.center_on(tx, ty)
        return True
