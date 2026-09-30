"""The planet map: tiles, terrain and procedural generation.

The map is a cylinder: it wraps east-west but not north-south.
"""
import math
import random

ARID, MOIST, RAINY = 0, 1, 2
FLAT, ROLLING, ROCKY = 0, 1, 2

RAINFALL_NAMES = ("Arid", "Moist", "Rainy")
ROCKINESS_NAMES = ("Flat", "Rolling", "Rocky")

NEIGHBOR_DIRS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]


class Tile:
    __slots__ = ("x", "y", "elevation", "rainfall", "rockiness", "fungus", "special",
                 "improvements", "supply_pod", "owner", "continent")

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.elevation = 0       # metres; below 0 is ocean
        self.rainfall = MOIST
        self.rockiness = FLAT
        self.fungus = False
        self.special = None      # None / "nutrient" / "mineral" / "energy"
        self.improvements = set()  # farm, mine, solar, road, forest
        self.supply_pod = False
        self.owner = None        # territory owner (player id)
        self.continent = 0       # connected land/sea body id

    @property
    def is_ocean(self):
        return self.elevation < 0

    @property
    def is_land(self):
        return self.elevation >= 0

    @property
    def is_shelf(self):
        return -1000 <= self.elevation < 0

    def terrain_name(self):
        if self.is_ocean:
            name = "Ocean Shelf" if self.is_shelf else "Deep Ocean"
        else:
            name = f"{RAINFALL_NAMES[self.rainfall]} {ROCKINESS_NAMES[self.rockiness]}"
        if self.fungus:
            name += ", Xenofungus"
        if "forest" in self.improvements:
            name += ", Forest"
        return name

    def rough(self):
        """Rough terrain costs a full move to enter (except on roads)."""
        return self.is_land and (self.rockiness == ROCKY or self.fungus or "forest" in self.improvements)


class World:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.tiles = [[Tile(x, y) for y in range(height)] for x in range(width)]

    # -- geometry ---------------------------------------------------------
    def wrap_x(self, x):
        return x % self.width

    def in_bounds(self, x, y):
        return 0 <= y < self.height

    def tile(self, x, y):
        if not 0 <= y < self.height:
            return None
        return self.tiles[x % self.width][y]

    def dx(self, x1, x2):
        d = abs(x1 - x2) % self.width
        return min(d, self.width - d)

    def distance(self, x1, y1, x2, y2):
        """Chebyshev distance (number of king moves), wrapping east-west."""
        return max(self.dx(x1, x2), abs(y1 - y2))

    def signed_dx(self, x1, x2):
        """Shortest signed delta from x1 to x2 on the cylinder."""
        d = (x2 - x1) % self.width
        if d > self.width // 2:
            d -= self.width
        return d

    def neighbors(self, x, y):
        for dx, dy in NEIGHBOR_DIRS:
            ny = y + dy
            if 0 <= ny < self.height:
                yield (x + dx) % self.width, ny

    def radius(self, x, y, r):
        for dy in range(-r, r + 1):
            ny = y + dy
            if not 0 <= ny < self.height:
                continue
            for dx in range(-r, r + 1):
                yield (x + dx) % self.width, ny

    def base_radius(self, x, y):
        """The 21-tile 'fat cross' a base can work."""
        for dy in range(-2, 3):
            ny = y + dy
            if not 0 <= ny < self.height:
                continue
            for dx in range(-2, 3):
                if abs(dx) == 2 and abs(dy) == 2:
                    continue
                yield (x + dx) % self.width, ny

    def all_tiles(self):
        for col in self.tiles:
            yield from col

    # -- generation -------------------------------------------------------
    def label_continents(self):
        cid = 0
        for t in self.all_tiles():
            t.continent = 0
        for t in self.all_tiles():
            if t.continent:
                continue
            cid += 1
            land = t.is_land
            stack = [t]
            t.continent = cid
            while stack:
                c = stack.pop()
                for nx, ny in self.neighbors(c.x, c.y):
                    n = self.tiles[nx][ny]
                    if not n.continent and n.is_land == land:
                        n.continent = cid
                        stack.append(n)

    def continent_sizes(self):
        sizes = {}
        for t in self.all_tiles():
            sizes[t.continent] = sizes.get(t.continent, 0) + 1
        return sizes


def _value_noise(width, height, rng, cells_x, cells_y):
    """Bilinear value noise that wraps horizontally."""
    grid = [[rng.random() for _ in range(cells_y + 2)] for _ in range(cells_x)]
    out = [[0.0] * height for _ in range(width)]
    for x in range(width):
        gx = x / width * cells_x
        x0 = int(gx)
        fx = gx - x0
        fx = fx * fx * (3 - 2 * fx)
        x1 = (x0 + 1) % cells_x
        x0 %= cells_x
        for y in range(height):
            gy = y / height * cells_y
            y0 = int(gy)
            fy = gy - y0
            fy = fy * fy * (3 - 2 * fy)
            a = grid[x0][y0] * (1 - fx) + grid[x1][y0] * fx
            b = grid[x0][y0 + 1] * (1 - fx) + grid[x1][y0 + 1] * fx
            out[x][y] = a * (1 - fy) + b * fy
    return out


def _fractal(width, height, rng, base_cells, octaves=4):
    total = [[0.0] * height for _ in range(width)]
    amp = 1.0
    norm = 0.0
    cells = base_cells
    for _ in range(octaves):
        layer = _value_noise(width, height, rng, cells, max(2, int(cells * height / width)))
        for x in range(width):
            col, lcol = total[x], layer[x]
            for y in range(height):
                col[y] += lcol[y] * amp
        norm += amp
        amp *= 0.5
        cells *= 2
    for x in range(width):
        for y in range(height):
            total[x][y] /= norm
    return total


def _rank_normalize(values):
    """Map a flat list of floats to their percentile rank 0..1."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    n = max(1, len(values) - 1)
    for rank, i in enumerate(order):
        out[i] = rank / n
    return out


def generate_world(width, height, seed=None, land_fraction=0.42):
    rng = random.Random(seed)
    world = World(width, height)

    elev = _fractal(width, height, rng, 5)
    # Push the poles down so the map is mostly ocean/ice near the edges.
    for x in range(width):
        for y in range(height):
            lat = abs((y + 0.5) / height - 0.5) * 2  # 0 at equator, 1 at poles
            if lat > 0.8:
                elev[x][y] -= (lat - 0.8) * 1.5
    flat = [elev[x][y] for x in range(width) for y in range(height)]
    ranks = _rank_normalize(flat)
    sea = 1.0 - land_fraction

    rain = _fractal(width, height, rng, 6, 3)
    rough = _fractal(width, height, rng, 8, 3)
    fung = _fractal(width, height, rng, 8, 3)

    i = 0
    for x in range(width):
        for y in range(height):
            r = ranks[i]
            i += 1
            t = world.tiles[x][y]
            if r < sea:
                t.elevation = int(-3000 + 3000 * (r / sea))
            else:
                t.elevation = int(3500 * (r - sea) / (1 - sea))

    # Shelf: ocean next to land is shallow.
    for t in world.all_tiles():
        if t.is_ocean:
            if any(world.tiles[nx][ny].is_land for nx, ny in world.neighbors(t.x, t.y)):
                t.elevation = max(t.elevation, -rng.randint(100, 900))
            elif t.elevation > -1000:
                t.elevation = -1000 - rng.randint(0, 800)

    for t in world.all_tiles():
        if t.is_land:
            lat = abs((t.y + 0.5) / height - 0.5) * 2
            wet = rain[t.x][t.y] + (0.25 if lat < 0.3 else 0.0) - (0.15 if lat > 0.7 else 0.0)
            coast = any(world.tiles[nx][ny].is_ocean for nx, ny in world.neighbors(t.x, t.y))
            if coast:
                wet += 0.08
            t.rainfall = ARID if wet < 0.45 else (MOIST if wet < 0.62 else RAINY)
            rk = rough[t.x][t.y] + t.elevation / 3500 * 0.5
            t.rockiness = FLAT if rk < 0.55 else (ROLLING if rk < 0.8 else ROCKY)

    # Xenofungus - the top ~14% of the fungus field.
    fvals = sorted(fung[x][y] for x in range(width) for y in range(height))
    fthresh = fvals[int(len(fvals) * 0.86)]
    for t in world.all_tiles():
        if fung[t.x][t.y] >= fthresh and (t.is_land or rng.random() < 0.5):
            t.fungus = True

    for t in world.all_tiles():
        if t.is_land and not t.fungus:
            roll = rng.random()
            if roll < 0.045:
                t.special = rng.choice(("nutrient", "mineral", "energy"))
            elif roll < 0.075:
                t.supply_pod = True
        elif t.is_ocean and t.is_shelf and rng.random() < 0.03:
            t.special = rng.choice(("nutrient", "energy"))

    world.label_continents()
    return world


def find_start_positions(world, count, rng):
    """Pick well spread, fertile land start positions on big continents."""
    sizes = world.continent_sizes()
    candidates = []
    for t in world.all_tiles():
        if not t.is_land or t.fungus or sizes.get(t.continent, 0) < 25:
            continue
        if t.y < 3 or t.y >= world.height - 3:
            continue
        score = 0.0
        for nx, ny in world.base_radius(t.x, t.y):
            n = world.tiles[nx][ny]
            if n.is_land and not n.fungus:
                score += 1 + n.rainfall * 0.6 + (0.5 if n.rockiness == ROLLING else 0)
            elif n.is_ocean:
                score += 0.6
            if n.special:
                score += 1.5
        candidates.append((score, t))
    if not candidates:
        candidates = [(1, t) for t in world.all_tiles() if t.is_land]
    candidates.sort(key=lambda c: -c[0])
    top = [t for _, t in candidates[: max(count * 30, len(candidates) // 3)]]

    best, best_spread = None, -1
    for _attempt in range(40):
        chosen = [rng.choice(top)]
        while len(chosen) < count:
            # Farthest-point sampling among the fertile candidates.
            pick = max(rng.sample(top, min(len(top), 60)),
                       key=lambda t: min(world.distance(t.x, t.y, c.x, c.y) for c in chosen))
            chosen.append(pick)
        spread = min((world.distance(a.x, a.y, b.x, b.y) for i, a in enumerate(chosen)
                      for b in chosen[i + 1:]), default=99)
        if spread > best_spread:
            best, best_spread = chosen, spread
    for s in best:
        for nx, ny in world.radius(s.x, s.y, 2):
            world.tiles[nx][ny].fungus = False
            world.tiles[nx][ny].supply_pod = False
    return [(t.x, t.y) for t in best]
