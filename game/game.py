"""The rules engine. Pure Python - no pygame - so it can be tested and simulated headless."""
import random

from . import ai
from .data import TECHS, UNITS, FACILITIES, PROJECTS, TERRAFORMS, FACTIONS, FACTION_LIST, ERAS
from .entities import Player, Base, Unit, MOVE_POINTS, MAX_HP, NATIVE_ID
from .pathfinding import find_path
from .victory import check_victory
from .world import generate_world, find_start_positions, ROCKY, ROLLING, FLAT

START_YEAR = 2101
BASE_POP_CAP = 7
CONTENT_BASE = 4
FREE_SUPPORT = 2
# Planetfall: for the first turns, landing supplies from orbit boost every base so the opening moves fast.
LANDING_TURNS = 40
LANDING_MINERALS = 1
LANDING_NUTRIENTS = 1
SIGHT_UNIT = 2
SIGHT_BASE = 3

MAP_SIZES = {"small": (48, 32), "standard": (64, 40), "large": (84, 52)}


class Game:
    def __init__(self, human_faction="concord", num_ai=3, map_size="standard", seed=None, all_ai=False):
        self.seed = seed if seed is not None else random.randrange(1 << 30)
        self.rng = random.Random(self.seed)
        w, h = MAP_SIZES[map_size]
        self.world = generate_world(w, h, self.rng.randrange(1 << 30))
        self.turn = 1
        self.players = []
        self.units = {}
        self.bases = {}
        self.unit_pos = {}       # (x, y) -> [unit ids]
        self.base_pos = {}       # (x, y) -> base id
        self.next_id = 1
        self.log = []            # (turn, pid or None, text, pos)
        self.projects_built = {}  # project id -> base id
        self.winner = None       # (pid, victory type)
        self.dirty_tiles = set()  # tiles whose appearance changed (for the renderer)
        self.human_id = None

        self.players.append(Player(NATIVE_ID, None, False, w, h))
        others = [f.id for f in FACTION_LIST if f.id != human_faction]
        self.rng.shuffle(others)
        faction_ids = [human_faction] + others[:num_ai]
        starts = find_start_positions(self.world, len(faction_ids), self.rng)
        for i, fid in enumerate(faction_ids):
            p = Player(i + 1, fid, (i == 0 and not all_ai), w, h)
            self.players.append(p)
            if p.is_human:
                self.human_id = p.id
            sx, sy = starts[i]
            for utype in ("colony_pod", "colony_pod", "former", "scout", "scout"):
                self._create_unit(utype, p.id, sx, sy)
        if self.human_id is None:
            self.human_id = 1
        for p, (sx, sy) in zip(self.players[1:], starts):
            self.reveal(p.id, sx, sy, 4)  # orbital survey from the landing craft
            self.update_visibility(p.id)
        self.notify(None, f"Mission Year {self.year}: Planetfall. Your colonists have landed.")

    # ------------------------------------------------------------------
    # Basic accessors
    # ------------------------------------------------------------------
    @property
    def year(self):
        return START_YEAR + self.turn - 1

    @property
    def human(self):
        return self.players[self.human_id]

    def player(self, pid):
        return self.players[pid]

    def notify(self, pid, text, pos=None):
        self.log.append((self.turn, pid, text, pos))
        if len(self.log) > 400:
            del self.log[:100]

    def units_at(self, x, y):
        return [self.units[i] for i in self.unit_pos.get((x % self.world.width, y), ())]

    def base_at(self, x, y):
        bid = self.base_pos.get((x % self.world.width, y))
        return self.bases.get(bid) if bid is not None else None

    def player_units(self, pid):
        return [u for u in self.units.values() if u.owner == pid]

    def player_bases(self, pid):
        return [b for b in self.bases.values() if b.owner == pid]

    def _new_id(self):
        self.next_id += 1
        return self.next_id

    def _place(self, unit):
        self.unit_pos.setdefault((unit.x, unit.y), []).append(unit.id)

    def _unplace(self, unit):
        lst = self.unit_pos.get((unit.x, unit.y))
        if lst and unit.id in lst:
            lst.remove(unit.id)
            if not lst:
                del self.unit_pos[(unit.x, unit.y)]

    def _create_unit(self, type_id, owner, x, y, home=None):
        u = Unit(self._new_id(), type_id, owner, x % self.world.width, y, home)
        if UNITS[type_id].domain == "sea":
            u.moves_left += self.players[owner].bonus("sea_moves") * MOVE_POINTS
        self.units[u.id] = u
        self._place(u)
        return u

    def full_moves(self, unit):
        m = unit.type.moves * MOVE_POINTS
        if unit.type.domain == "sea":
            m += self.players[unit.owner].bonus("sea_moves") * MOVE_POINTS
        return m

    def kill_unit(self, unit):
        if unit.id not in self.units:
            return
        for cid in list(unit.cargo):
            c = self.units.get(cid)
            if c:
                c.carried_by = None
                self.kill_unit(c)
        if unit.carried_by and unit.carried_by in self.units:
            t = self.units[unit.carried_by]
            if unit.id in t.cargo:
                t.cargo.remove(unit.id)
        self._unplace(unit)
        del self.units[unit.id]

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------
    def has_tech(self, pid, tech):
        return tech is None or tech in self.players[pid].techs

    def available_techs(self, pid):
        p = self.players[pid]
        return [t for t in TECHS.values() if t.id not in p.techs and all(r in p.techs for r in t.prereqs)]

    def tech_cost(self, pid, tech_id=None):
        p = self.players[pid]
        n = len(p.techs)
        cost = 12 + 11 * (n ** 1.35)
        if tech_id:
            knowers = sum(1 for q in self.players
                          if q.alive and q.id != pid and not q.is_native and p.has_contact(q.id) and tech_id in q.techs)
            cost *= 1 - min(0.3, 0.1 * knowers)
        return int(cost)

    def buildable_units(self, pid):
        out = []
        for u in UNITS.values():
            if u.native or not self.has_tech(pid, u.prereq):
                continue
            if u.obsolete_by and self.has_tech(pid, UNITS[u.obsolete_by].prereq):
                continue
            out.append(u)
        return out

    def is_coastal(self, base):
        return any(self.world.tiles[nx][ny].is_ocean for nx, ny in self.world.neighbors(base.x, base.y))

    def production_options(self, base):
        """All (kind, id) items this base can build right now."""
        opts = []
        for u in self.buildable_units(base.owner):
            if u.domain == "sea" and not self.is_coastal(base):
                continue
            opts.append(("unit", u.id))
        for f in FACILITIES.values():
            if f.id not in base.facilities and self.has_tech(base.owner, f.prereq):
                opts.append(("facility", f.id))
        for pr in PROJECTS.values():
            if pr.id not in self.projects_built and self.has_tech(base.owner, pr.prereq):
                opts.append(("project", pr.id))
        opts.append(("special", "stockpile"))
        return opts

    @staticmethod
    def item_name(item):
        kind, iid = item
        if kind == "unit":
            return UNITS[iid].name
        if kind == "facility":
            return FACILITIES[iid].name
        if kind == "project":
            return PROJECTS[iid].name
        return "Stockpile Energy"

    @staticmethod
    def item_cost(item):
        kind, iid = item
        if kind == "unit":
            return UNITS[iid].cost
        if kind == "facility":
            return FACILITIES[iid].cost
        if kind == "project":
            return PROJECTS[iid].cost
        return 0

    def project_owner(self, project_id):
        bid = self.projects_built.get(project_id)
        if bid is None or bid not in self.bases:
            return None
        return self.bases[bid].owner

    def has_project(self, pid, project_id):
        return self.project_owner(project_id) == pid

    def era(self, pid):
        techs = self.players[pid].techs
        e = 0
        for t in techs:
            e = max(e, TECHS[t].era)
        return ERAS[e]

    # ------------------------------------------------------------------
    # Tile yields and base economy
    # ------------------------------------------------------------------
    def tile_yield(self, tile, pid, base_tile=False):
        p = self.players[pid]
        imp = tile.improvements
        if tile.fungus:
            n = m = e = 0
            if self.has_tech(pid, "ecological_engineering"):
                e += 1
            if self.has_tech(pid, "centauri_psi"):
                n += 1
            if self.has_tech(pid, "planetary_mind"):
                m += 1
                e += 1
            fb = p.bonus("fungus_bonus")
            n += fb
            e += fb
        elif tile.is_ocean:
            n, m, e = 1 + p.bonus("ocean_nutrient"), 0, 2 if tile.is_shelf else 1
        elif "forest" in imp:
            n, m, e = 1, 2, 0
            if self.has_tech(pid, "environmental_economics"):
                e += 1
        else:
            n = 0 if tile.rockiness == ROCKY else tile.rainfall
            m = 0 if tile.rockiness == FLAT else 1
            e = 0
            if "farm" in imp:
                n += 1
                if self.has_project(pid, "weather_array"):
                    n += 1
            if "mine" in imp:
                m += 2 if tile.rockiness == ROCKY else 1
            if "solar" in imp:
                e += 1 + max(0, tile.elevation // 1000)
        if tile.special == "nutrient":
            n += 2
        elif tile.special == "mineral":
            m += 2
        elif tile.special == "energy":
            e += 2
        if base_tile:
            n, m, e = max(n, 1) + (1 if tile.is_land and tile.rainfall > 0 and not tile.fungus else 0), max(m, 1), max(e, 2)
            e += p.bonus("base_energy")
        else:
            # Planetary restrictions until the relevant technologies are known.
            if not self.has_tech(pid, "gene_splicing"):
                n = min(n, 2)
            if not self.has_tech(pid, "ecological_engineering"):
                m = min(m, 2)
            if not self.has_tech(pid, "environmental_economics"):
                e = min(e, 2)
        return n, m, e

    def pop_cap(self, base):
        cap = BASE_POP_CAP + self.players[base.owner].bonus("pop_cap")
        for fid in base.facilities:
            f = FACILITIES[fid]
            if f.pop_cap:
                cap = max(cap, f.pop_cap + self.players[base.owner].bonus("pop_cap"))
        return cap

    def growth_threshold(self, base):
        # Cheap early growth, steeper for big bases: 10, 18, 26, 36, 46 ... 186 at size 14.
        return 4 + 6 * base.pop + base.pop * base.pop // 2

    def workable_tiles(self, base):
        taken = set()
        for other in self.bases.values():
            if other.id != base.id and self.world.distance(other.x, other.y, base.x, base.y) <= 4:
                taken.update(other.worked)
        out = []
        for x, y in self.world.base_radius(base.x, base.y):
            if (x, y) == (base.x, base.y) or (x, y) in taken:
                continue
            t = self.world.tiles[x][y]
            if t.owner is not None and t.owner != base.owner:
                continue
            if any(u.owner != base.owner for u in self.units_at(x, y)):
                continue
            out.append(t)
        return out

    def assign_workers(self, base):
        weights = {"balanced": (2.0, 1.6, 1.3), "growth": (3.5, 1.2, 1.0),
                   "production": (1.6, 3.0, 1.0), "energy": (1.6, 1.2, 3.0)}[base.focus]
        wn, wm, we = weights
        tiles = self.workable_tiles(base)
        scored = [(t, self.tile_yield(t, base.owner)) for t in tiles]
        food = self.tile_yield(self.world.tiles[base.x][base.y], base.owner, True)[0]
        food += FACILITIES["recycling_tanks"].tile_bonus if "recycling_tanks" in base.facilities else 0
        worked = []
        for i in range(base.pop):
            if not scored:
                break
            need = 2 * (i + 1) - food
            fw = wn * (2.0 if need > 0 else 1.0)
            best = max(scored, key=lambda s: s[1][0] * fw + s[1][1] * wm + s[1][2] * we)
            bn, bm, be = best[1]
            if bn + bm + be == 0:
                break
            scored.remove(best)
            worked.append((best[0].x, best[0].y))
            food += bn
        base.worked = worked
        base.specialists = base.pop - len(worked)

    def base_report(self, base):
        """Compute all per-turn yields for a base (without applying them)."""
        p = self.players[base.owner]
        world = self.world
        bt = world.tiles[base.x][base.y]
        n, m, e = self.tile_yield(bt, base.owner, True)
        bonus = sum(FACILITIES[f].tile_bonus for f in base.facilities)
        n, m, e = n + bonus, m + bonus, e + bonus
        for x, y in base.worked:
            tn, tm, te = self.tile_yield(world.tiles[x][y], base.owner)
            n += tn
            m += tm
            e += te
        e += base.specialists * 2
        landing = self.turn <= LANDING_TURNS
        if landing:
            n += LANDING_NUTRIENTS
            m += LANDING_MINERALS

        supported = [u for u in self.units.values() if u.home == base.id]
        free = FREE_SUPPORT + (1 if p.bonus("police") else 0)
        support = max(0, len(supported) - free)
        m_net = max(0, m - support)
        m_pct = sum(FACILITIES[f].minerals_pct for f in base.facilities)
        m_net = m_net * (100 + m_pct) // 100

        # Inefficiency: energy lost with distance from headquarters.
        hq = self.bases.get(p.hq_base)
        dist = world.distance(base.x, base.y, hq.x, hq.y) if hq else 20
        loss = int(e * min(0.5, dist / 36))
        e_net = e - loss
        a_econ, a_psych, _a_labs = p.alloc
        econ = e_net * a_econ // 10
        psych = e_net * a_psych // 10
        labs = e_net - econ - psych

        econ_pct = sum(FACILITIES[f].econ_pct for f in base.facilities) + p.bonus("econ_pct")
        if self.has_project(p.id, "planetary_exchange"):
            econ_pct += 25
        labs_pct = sum(FACILITIES[f].labs_pct for f in base.facilities) + p.bonus("labs_pct")
        if self.has_project(p.id, "cyber_sanctum"):
            labs_pct += 25
        psych_pct = sum(FACILITIES[f].psych_pct for f in base.facilities)
        econ = econ * (100 + econ_pct) // 100
        labs = labs * (100 + labs_pct) // 100
        psych = psych * (100 + psych_pct) // 100

        # Drones (unhappy citizens).
        num_bases = sum(1 for b in self.bases.values() if b.owner == p.id)
        content = CONTENT_BASE + p.bonus("content") - max(0, (num_bases - 8) // 4)
        drones = max(0, base.pop - max(0, content))
        drones += sum(FACILITIES[f].drones for f in base.facilities)
        if self.has_project(p.id, "genome_archive"):
            drones -= 1
        police_units = sum(1 for u in self.units_at(base.x, base.y) if u.owner == p.id and u.type.military)
        drones -= min(police_units, 1 + p.bonus("police"))
        drones -= psych // 2
        drones = max(0, min(base.pop, drones))
        rioting = drones * 2 > base.pop and drones > 0 and base.pop > 1

        upkeep = sum(FACILITIES[f].upkeep for f in base.facilities)
        food_use = base.pop * 2
        report = {
            "nutrients": n, "nutrient_surplus": n - food_use, "minerals": m, "support": support,
            "minerals_net": 0 if rioting else m_net, "energy": e, "inefficiency": loss,
            "econ": 0 if rioting else econ, "psych": psych, "labs": 0 if rioting else labs,
            "upkeep": upkeep, "drones": drones, "rioting": rioting,
            "growth_threshold": self.growth_threshold(base), "pop_cap": self.pop_cap(base), "landing": landing,
        }
        base.last_report = report
        base.rioting = rioting
        return report

    def turns_to_complete(self, base, item=None):
        item = item or base.production
        rep = base.last_report or self.base_report(base)
        cost = self.item_cost(item)
        have = base.minerals if item == base.production else 0
        rate = rep["minerals_net"]
        if cost <= have:
            return 1
        if rate <= 0:
            return 999
        return -(-(cost - have) // rate)

    def buy_cost(self, base):
        item = base.production
        if item[0] == "special":
            return 0
        remaining = max(0, self.item_cost(item) - base.minerals)
        price = 2 * remaining + remaining * remaining // 20
        if base.minerals == 0:
            price *= 2
        if item[0] == "project":
            price *= 2
        return price

    def buy_production(self, base):
        p = self.players[base.owner]
        cost = self.buy_cost(base)
        if cost <= 0 or p.credits < cost:
            return False
        p.credits -= cost
        base.minerals = self.item_cost(base.production)
        self.notify(p.id, f"{base.name}: purchased {self.item_name(base.production)} for {cost} credits.",
                    (base.x, base.y))
        return True

    def set_production(self, base, item):
        if base.production[0] != item[0] and base.production[0] != "special" and item[0] != "special":
            # Switching category (e.g. unit -> facility) loses half the stock, as in the classics.
            base.minerals //= 2
        base.production = item

    # ------------------------------------------------------------------
    # Territory and visibility
    # ------------------------------------------------------------------
    def update_territory(self):
        world = self.world
        best = {}
        for b in sorted(self.bases.values(), key=lambda b: b.founded):
            r = 3 + (1 if b.pop >= 5 else 0)
            for x, y in world.radius(b.x, b.y, r):
                d = world.distance(x, y, b.x, b.y)
                if world.tiles[x][y].is_ocean and d > 2:
                    continue
                cur = best.get((x, y))
                if cur is None or d < cur[0]:
                    best[(x, y)] = (d, b.owner)
        for t in world.all_tiles():
            new = best.get((t.x, t.y), (0, None))[1]
            if new != t.owner:
                t.owner = new
                self.dirty_tiles.add((t.x, t.y))

    def update_visibility(self, pid):
        p = self.players[pid]
        w = self.world.width
        p.visible = bytearray(len(p.visible))
        seen = []
        for u in self.units.values():
            if u.owner == pid:
                seen.append((u.x, u.y, SIGHT_UNIT + (1 if self.world.tiles[u.x][u.y].elevation > 2000 else 0)))
        for b in self.bases.values():
            if b.owner == pid:
                seen.append((b.x, b.y, SIGHT_BASE))
        for sx, sy, r in seen:
            for x, y in self.world.radius(sx, sy, r):
                idx = y * w + x
                p.visible[idx] = 1
                p.explored[idx] = 1
        self._check_contacts(pid)

    def reveal(self, pid, cx, cy, r):
        p = self.players[pid]
        w = self.world.width
        for x, y in self.world.radius(cx, cy, r):
            p.explored[y * w + x] = 1

    def is_visible(self, pid, x, y):
        return self.players[pid].visible[y * self.world.width + (x % self.world.width)] == 1

    def is_explored(self, pid, x, y):
        return self.players[pid].explored[y * self.world.width + (x % self.world.width)] == 1

    def _check_contacts(self, pid):
        p = self.players[pid]
        if p.is_native:
            return
        w = self.world.width
        others = set()
        for (x, y), ids in self.unit_pos.items():
            if p.visible[y * w + x]:
                for i in ids:
                    o = self.units[i].owner
                    if o != pid and o != NATIVE_ID:
                        others.add(o)
        for (x, y), bid in self.base_pos.items():
            if p.visible[y * w + x]:
                o = self.bases[bid].owner
                if o != pid:
                    others.add(o)
        for o in others:
            if not p.has_contact(o):
                self.make_contact(pid, o)

    def make_contact(self, a, b):
        pa, pb = self.players[a], self.players[b]
        pa.relations[b] = "peace"
        pb.relations[a] = "peace"
        self.notify(a, f"Contact established with the {pb.name}.")
        self.notify(b, f"Contact established with the {pa.name}.")

    def declare_war(self, a, b):
        pa, pb = self.players[a], self.players[b]
        if pa.relations.get(b) == "war":
            return
        pa.relations[b] = "war"
        pb.relations[a] = "war"
        pa.war_turns[b] = pb.war_turns[a] = self.turn
        self.notify(None, f"The {pa.name} has declared war on the {pb.name}!")

    def make_peace(self, a, b):
        pa, pb = self.players[a], self.players[b]
        pa.relations[b] = "peace"
        pb.relations[a] = "peace"
        pa.war_turns.pop(b, None)
        pb.war_turns.pop(a, None)
        self.notify(None, f"The {pa.name} and the {pb.name} have signed a peace treaty.")

    def propose_peace(self, a, b):
        """Player a asks player b for peace. AI decides; returns True if accepted."""
        pb = self.players[b]
        if pb.is_human:
            return False
        if ai.consider_peace(self, pb, a):
            self.make_peace(a, b)
            return True
        return False

    # ------------------------------------------------------------------
    # Movement
    # ------------------------------------------------------------------
    def move_cost(self, unit, fx, fy, tx, ty):
        if unit.type.domain == "sea":
            return MOVE_POINTS
        f = self.world.tiles[fx % self.world.width][fy]
        t = self.world.tiles[tx % self.world.width][ty]
        if unit.type.native and t.fungus:
            return 1
        f_road = "road" in f.improvements or (fx % self.world.width, fy) in self.base_pos
        t_road = "road" in t.improvements or (tx % self.world.width, ty) in self.base_pos
        if f_road and t_road:
            return 1
        if t.rough():
            return 2 * MOVE_POINTS
        return MOVE_POINTS

    def _can_stand(self, unit, x, y):
        """Terrain/domain check (ignores other units except transports)."""
        t = self.world.tile(x, y)
        if t is None:
            return False
        if unit.type.domain == "sea":
            b = self.base_at(x, y)
            return t.is_ocean or (b is not None and b.owner == unit.owner)
        if t.is_land:
            return True
        # Land unit onto ocean: needs a friendly transport with room.
        return self._transport_at(unit.owner, x, y) is not None

    def _transport_at(self, owner, x, y):
        for u in self.units_at(x, y):
            if u.owner == owner and u.type.capacity and len(u.cargo) < u.type.capacity:
                return u
        return None

    def path_passable(self, unit, x, y, is_goal):
        t = self.world.tile(x, y)
        if t is None:
            return False
        if unit.type.domain == "sea":
            b = self.base_at(x, y)
            if not (t.is_ocean or (b is not None and b.owner == unit.owner)):
                return False
        elif not t.is_land:
            return False
        others = [u for u in self.units_at(x, y) if u.owner != unit.owner]
        b = self.base_at(x, y)
        if others or (b is not None and b.owner != unit.owner):
            return is_goal
        return True

    def hostile_at(self, unit, x, y):
        """Units/base at (x, y) that belong to someone else."""
        others = [u for u in self.units_at(x, y) if u.owner != unit.owner]
        b = self.base_at(x, y)
        if b is not None and b.owner == unit.owner:
            b = None
        return others, b

    def can_attack(self, unit):
        return unit.type.attack > 0 and not unit.type.colony and not unit.type.former

    def move_unit(self, unit, x, y):
        """Try to move a unit one step. Returns a short result string:
        'moved', 'attack', 'captured', or 'blocked:<reason>'."""
        world = self.world
        x %= world.width
        if not world.in_bounds(x, y) or world.distance(unit.x, unit.y, x, y) != 1:
            return "blocked:not adjacent"
        if unit.moves_left <= 0:
            return "blocked:no moves left"
        if unit.terraform:
            unit.terraform = None
        others, enemy_base = self.hostile_at(unit, x, y)
        owner = self.players[unit.owner]

        if others or enemy_base:
            target_owner = others[0].owner if others else enemy_base.owner
            if not owner.at_war(target_owner):
                return f"blocked:at peace with the {self.players[target_owner].name}"
            if others:
                if not self.can_attack(unit):
                    return "blocked:this unit cannot attack"
                t = world.tiles[x][y]
                if unit.type.domain == "sea" and t.is_land:
                    return "blocked:naval units cannot attack land"
                if unit.type.domain == "land" and t.is_ocean:
                    return "blocked:cannot attack units at sea"
                if unit.carried_by:
                    return "blocked:unload before attacking"
                self.attack(unit, x, y)
                return "attack"
            # Undefended enemy base.
            if unit.type.native:
                self.attack(unit, x, y)
                return "attack"
            if not self.can_attack(unit) or unit.type.domain != "land":
                return "blocked:this unit cannot capture bases"
            self._relocate(unit, x, y)
            unit.moves_left = 0
            self.capture_base(enemy_base, unit.owner)
            return "captured"

        if not self._can_stand(unit, x, y):
            return "blocked:impassable terrain"
        cost = self.move_cost(unit, unit.x, unit.y, x, y)
        full = self.full_moves(unit)
        if unit.moves_left < cost and unit.moves_left < full:
            unit.moves_left = 0
            return "blocked:not enough moves for rough terrain"
        unit.moves_left = max(0, unit.moves_left - cost)
        unit.fortified = False
        if unit.orders in ("fortify", "sentry") and not unit.carried_by:
            unit.orders = None

        t = world.tiles[x][y]
        # Boarding / unloading.
        if unit.type.domain == "land" and t.is_ocean:
            transport = self._transport_at(unit.owner, x, y)
            self._disembark(unit)
            transport.cargo.append(unit.id)
            unit.carried_by = transport.id
            unit.orders = "sentry"
            unit.moves_left = 0
        else:
            self._disembark(unit)
        self._relocate(unit, x, y)
        if unit.type.capacity:
            for cid in unit.cargo:
                c = self.units[cid]
                self._relocate(c, x, y)
        if t.supply_pod and not unit.type.native:
            self._open_pod(unit, t)
        self.update_visibility(unit.owner)
        return "moved"

    def _disembark(self, unit):
        if unit.carried_by:
            tr = self.units.get(unit.carried_by)
            if tr and unit.id in tr.cargo:
                tr.cargo.remove(unit.id)
            unit.carried_by = None

    def _relocate(self, unit, x, y):
        self._unplace(unit)
        unit.x, unit.y = x % self.world.width, y
        self._place(unit)

    def _open_pod(self, unit, tile):
        tile.supply_pod = False
        self.dirty_tiles.add((tile.x, tile.y))
        p = self.players[unit.owner]
        rng = self.rng
        roll = rng.random()
        pos = (tile.x, tile.y)
        if roll < 0.35:
            amt = rng.randint(20, 60)
            p.credits += amt
            self.notify(p.id, f"Supply pod: {amt} energy credits recovered.", pos)
        elif roll < 0.45 and self.available_techs(p.id):
            tech = rng.choice(self.available_techs(p.id))
            self.grant_tech(p.id, tech.id, source="Supply pod data banks")
        elif roll < 0.6:
            utype = rng.choice(["former", "scout", "colony_pod"])
            self._create_unit(utype, p.id, tile.x, tile.y)
            self.notify(p.id, f"Supply pod: a stranded {UNITS[utype].name} joins your faction!", pos)
        elif roll < 0.75:
            self.reveal(p.id, tile.x, tile.y, 6)
            self.notify(p.id, "Supply pod: satellite maps reveal the surrounding area.", pos)
        elif roll < 0.88:
            bases = self.player_bases(p.id)
            if bases:
                b = min(bases, key=lambda b: self.world.distance(b.x, b.y, tile.x, tile.y))
                b.minerals += 25
                self.notify(p.id, f"Supply pod: 25 minerals shipped to {b.name}.", pos)
            else:
                p.credits += 25
                self.notify(p.id, "Supply pod: 25 energy credits recovered.", pos)
        else:
            spots = [(nx, ny) for nx, ny in self.world.neighbors(tile.x, tile.y)
                     if self.world.tiles[nx][ny].is_land and not self.unit_pos.get((nx, ny))
                     and (nx, ny) not in self.base_pos]
            if spots:
                sx, sy = rng.choice(spots)
                self._create_unit("xenoworm", NATIVE_ID, sx, sy)
                self.notify(p.id, "Supply pod: the pod was a nest! Xenoworms emerge!", pos)
            else:
                p.credits += 10
                self.notify(p.id, "Supply pod: 10 energy credits recovered.", pos)

    # ------------------------------------------------------------------
    # Combat
    # ------------------------------------------------------------------
    def _morale_mult(self, unit):
        return 1 + 0.125 * (unit.morale - 1)

    def strength(self, unit, attacking, opponent, x, y):
        p = self.players[unit.owner]
        psi = unit.type.native or opponent.type.native
        t = self.world.tiles[x][y]
        base = self.base_at(x, y)
        if psi:
            s = (unit.type.attack if attacking else unit.type.defense) if unit.type.native else 2.0
            pct = p.bonus("psi_pct")
            if self.has_project(p.id, "empath_council"):
                pct += 50
            s *= 1 + pct / 100
        elif attacking:
            s = unit.type.attack * (1 + p.bonus("attack_pct") / 100)
        else:
            s = max(unit.type.defense, 0.5)
            mult = 1.0
            if t.is_land and not base:
                if t.rockiness == ROCKY:
                    mult += 0.5
                elif t.rockiness == ROLLING or "forest" in t.improvements or t.fungus:
                    mult += 0.25
            if unit.fortified:
                mult += 0.25
            if base:
                mult += 0.25
                if "perimeter_defense" in base.facilities and not opponent.type.domain == "sea":
                    mult += 1.0
            mult += p.bonus("defense_pct") / 100
            s *= mult
        return s * self._morale_mult(unit)

    def best_defender(self, attacker, x, y):
        defenders = [u for u in self.units_at(x, y) if u.owner != attacker.owner and not u.carried_by]
        if not defenders:
            defenders = [u for u in self.units_at(x, y) if u.owner != attacker.owner]
        if not defenders:
            return None
        return max(defenders, key=lambda d: self.strength(d, False, attacker, x, y) * d.hp)

    def combat_odds(self, attacker, x, y):
        """Probability (0..1) that the attacker wins, estimated from the strengths."""
        d = self.best_defender(attacker, x, y)
        if d is None:
            return 1.0
        a_s = self.strength(attacker, True, d, x, y)
        d_s = self.strength(d, False, attacker, x, y)
        p = a_s / (a_s + d_s)
        # Quick analytic-ish estimate by simulation with a fixed seed.
        rng = random.Random(1234)
        wins = 0
        for _ in range(200):
            ah, dh = attacker.hp, d.hp
            while ah > 0 and dh > 0:
                if rng.random() < p:
                    dh -= 2
                else:
                    ah -= 2
            wins += dh <= 0
        return wins / 200

    def attack(self, attacker, x, y):
        defender = self.best_defender(attacker, x, y)
        base = self.base_at(x, y)
        attacker.moves_left = max(0, attacker.moves_left - MOVE_POINTS)
        attacker.fortified = False
        ap = self.players[attacker.owner]
        if defender is None:
            # Native life raiding an undefended base.
            if base:
                base.pop -= 1
                self.notify(base.owner, f"Xenoworms ravage {base.name}! Population lost.", (x, y))
                if base.pop <= 0:
                    self.destroy_base(base)
            return True
        dp = self.players[defender.owner]
        if not ap.is_native and not dp.is_native and not ap.at_war(dp.id):
            self.declare_war(ap.id, dp.id)
        a_s = self.strength(attacker, True, defender, x, y)
        d_s = self.strength(defender, False, attacker, x, y)
        p = a_s / (a_s + d_s)
        while attacker.hp > 0 and defender.hp > 0:
            if self.rng.random() < p:
                defender.hp -= 2
            else:
                attacker.hp -= 2
        pos = (x, y)
        if defender.hp <= 0:
            winner, loser = attacker, defender
            self.notify(ap.id, f"Your {attacker.name} destroyed a {dp.name} {defender.name}.", pos)
            self.notify(dp.id, f"Your {defender.name} was destroyed by a {ap.name} {attacker.name}.", pos)
            if defender.type.native and not ap.is_native:
                ap.credits += 10
            # Outside of bases, the whole stack falls with its defender.
            stack = [u for u in self.units_at(x, y) if u.owner == defender.owner]
            if base is None:
                for u in stack:
                    self.kill_unit(u)
                if len(stack) > 1:
                    self.notify(dp.id, f"{len(stack) - 1} other unit(s) in the stack were lost.", pos)
            else:
                self.kill_unit(defender)
        else:
            winner, loser = defender, attacker
            self.notify(ap.id, f"Your {attacker.name} was destroyed attacking a {dp.name} {defender.name}.", pos)
            self.notify(dp.id, f"Your {defender.name} repelled a {ap.name} {attacker.name}.", pos)
            self.kill_unit(attacker)
        if winner.morale < 5 and self.rng.random() < 0.5:
            winner.morale += 1
        return winner is attacker

    # ------------------------------------------------------------------
    # Bases
    # ------------------------------------------------------------------
    def can_found_base(self, unit):
        if not unit.type.colony:
            return False, "Only colony pods can found bases."
        if unit.carried_by:
            return False, "Unload the colony pod first."
        t = self.world.tiles[unit.x][unit.y]
        if not t.is_land:
            return False, "Bases must be founded on land."
        for b in self.bases.values():
            if self.world.distance(b.x, b.y, unit.x, unit.y) < 3:
                return False, "Too close to another base."
        if t.owner is not None and t.owner != unit.owner:
            return False, "This land is claimed by another faction."
        return True, ""

    def next_base_name(self, pid):
        p = self.players[pid]
        names = p.faction.base_names
        i = p.base_name_index
        p.base_name_index += 1
        if i < len(names):
            return names[i]
        return f"{names[i % len(names)]} {i // len(names) + 1}"

    def found_base(self, unit):
        ok, _ = self.can_found_base(unit)
        if not ok:
            return None
        pid = unit.owner
        x, y = unit.x, unit.y
        b = Base(self._new_id(), self.next_base_name(pid), pid, x, y, self.turn)
        t = self.world.tiles[x][y]
        t.fungus = False
        t.improvements.discard("forest")
        t.improvements.add("road")
        self.dirty_tiles.add((x, y))
        self.bases[b.id] = b
        self.base_pos[(x, y)] = b.id
        p = self.players[pid]
        if p.hq_base not in self.bases:
            p.hq_base = b.id
        self.kill_unit(unit)
        self.update_territory()
        ai.choose_production(self, b)
        self.assign_workers(b)
        self.base_report(b)
        self.update_visibility(pid)
        self.notify(pid, f"{b.name} founded.", (x, y))
        return b

    def destroy_base(self, base):
        self.notify(None, f"{base.name} has been destroyed!", (base.x, base.y))
        del self.bases[base.id]
        del self.base_pos[(base.x, base.y)]
        for u in self.units.values():
            if u.home == base.id:
                u.home = None
        for pr, bid in list(self.projects_built.items()):
            if bid == base.id:
                self.projects_built[pr] = None
        p = self.players[base.owner]
        if p.hq_base == base.id:
            rest = self.player_bases(p.id)
            p.hq_base = min(rest, key=lambda b: b.founded).id if rest else None
        self.dirty_tiles.add((base.x, base.y))
        self.update_territory()

    def capture_base(self, base, new_owner):
        old = base.owner
        op, np_ = self.players[old], self.players[new_owner]
        base.pop -= 1
        if base.pop <= 0:
            self.destroy_base(base)
            self.notify(new_owner, "The base was razed in the fighting.")
            return
        base.owner = new_owner
        base.minerals = 0
        base.queue = []
        base.facilities = {f for f in base.facilities if self.rng.random() < 0.5}
        for u in self.units.values():
            if u.home == base.id:
                u.home = None
        if op.hq_base == base.id:
            rest = self.player_bases(old)
            op.hq_base = min(rest, key=lambda b: b.founded).id if rest else None
        if np_.hq_base not in self.bases:
            np_.hq_base = base.id
        ai.choose_production(self, base)
        self.notify(None, f"The {np_.name} captured {base.name} from the {op.name}!", (base.x, base.y))
        self.update_territory()
        self.assign_workers(base)
        self.update_visibility(new_owner)
        self.update_visibility(old)

    # ------------------------------------------------------------------
    # Unit orders
    # ------------------------------------------------------------------
    def terraform_options(self, unit):
        """Terraforming jobs the unit could start on its current tile."""
        if not unit.type.former or unit.carried_by:
            return []
        t = self.world.tiles[unit.x][unit.y]
        if not t.is_land:
            return []
        opts = []
        for tf in TERRAFORMS.values():
            if not self.has_tech(unit.owner, tf.prereq):
                continue
            if self._terraform_valid(t, tf.id):
                opts.append(tf)
        return opts

    def _terraform_valid(self, t, kind):
        imp = t.improvements
        if kind == "remove_fungus":
            return t.fungus
        if kind == "road":
            return "road" not in imp
        if t.fungus or (t.x, t.y) in self.base_pos:
            return False
        if kind == "farm":
            return "farm" not in imp and t.rockiness != ROCKY
        if kind == "mine":
            return "mine" not in imp and t.rockiness != FLAT
        if kind == "solar":
            return "solar" not in imp
        if kind == "forest":
            return "forest" not in imp
        return False

    def start_terraform(self, unit, kind):
        if kind not in [tf.id for tf in self.terraform_options(unit)]:
            return False
        t = self.world.tiles[unit.x][unit.y]
        turns = TERRAFORMS[kind].turns
        if kind == "mine" and t.rockiness == ROCKY:
            turns += 2
        if kind == "road" and t.rough():
            turns *= 2
        unit.terraform = (kind, turns)
        unit.orders = "terraform" if unit.orders != "auto" else "auto"
        unit.moves_left = 0
        return True

    def _complete_terraform(self, unit, kind):
        t = self.world.tiles[unit.x][unit.y]
        imp = t.improvements
        if kind == "remove_fungus":
            t.fungus = False
        elif kind == "road":
            imp.add("road")
        elif kind == "farm":
            imp.discard("mine")
            imp.discard("forest")
            imp.add("farm")
        elif kind == "mine":
            imp.discard("farm")
            imp.discard("solar")
            imp.discard("forest")
            imp.add("mine")
        elif kind == "solar":
            imp.discard("mine")
            imp.discard("forest")
            imp.add("solar")
        elif kind == "forest":
            for k in ("farm", "mine", "solar"):
                imp.discard(k)
            imp.add("forest")
        self.dirty_tiles.add((t.x, t.y))

    def fortify(self, unit):
        unit.orders = "fortify"
        unit.moves_left = 0

    def sentry(self, unit):
        unit.orders = "sentry"

    def set_goto(self, unit, x, y):
        path = find_path(self, unit, x, y)
        if path is None:
            return False
        unit.orders = "goto"
        unit.goal = (x % self.world.width, y)
        unit.path = path
        return True

    def follow_path(self, unit):
        """Advance a unit along its goto path. Returns when it runs out of moves or arrives."""
        steps = 0
        while unit.id in self.units and unit.path and unit.moves_left > 0 and steps < 30:
            steps += 1
            nx, ny = unit.path[0]
            others, eb = self.hostile_at(unit, nx, ny)
            if (others or eb) and len(unit.path) > 1:
                # Something is in the way - re-plan.
                path = find_path(self, unit, *unit.goal)
                if not path or path[0] == (nx, ny):
                    unit.orders, unit.path = None, []
                    return
                unit.path = path
                continue
            before = unit.moves_left
            res = self.move_unit(unit, nx, ny)
            if res in ("moved", "captured"):
                unit.path.pop(0)
            elif res == "attack":
                unit.path = []
            else:
                if unit.moves_left == 0 and before > 0 and "rough" in res:
                    return  # try again next turn
                unit.path = []
                break
        if unit.id in self.units and not unit.path and unit.orders == "goto":
            unit.orders = None
            unit.goal = None

    def units_needing_orders(self, pid):
        out = []
        for u in self.units.values():
            if u.owner != pid or u.moves_left <= 0 or u.carried_by:
                continue
            if u.orders in ("fortify", "sentry", "terraform", "auto", "explore", "goto"):
                continue
            out.append(u)
        out.sort(key=lambda u: u.id)
        return out

    # ------------------------------------------------------------------
    # Research
    # ------------------------------------------------------------------
    def grant_tech(self, pid, tech_id, source=None):
        p = self.players[pid]
        if tech_id in p.techs:
            return
        p.techs.add(tech_id)
        name = TECHS[tech_id].name
        self.notify(pid, f"{source + ': ' if source else ''}Discovered {name}!")
        if p.current_tech == tech_id:
            p.current_tech = None
        if tech_id == "transcendence":
            self.notify(None, f"The {p.name} has mastered Transcendence and may now build the Ascension Engine!")

    def set_research(self, pid, tech_id):
        self.players[pid].current_tech = tech_id

    def _research(self, p, labs):
        if p.current_tech is None or p.current_tech in p.techs:
            p.current_tech = ai.choose_research(self, p)
        if p.current_tech is None:
            return
        p.research_progress += labs
        cost = self.tech_cost(p.id, p.current_tech)
        if p.research_progress >= cost:
            p.research_progress -= cost
            done = p.current_tech
            self.grant_tech(p.id, done)
            p.current_tech = None
            if not p.is_human:
                p.current_tech = ai.choose_research(self, p)

    # ------------------------------------------------------------------
    # Turn processing
    # ------------------------------------------------------------------
    def end_turn(self):
        """The human has finished their turn: run the AIs and process the round."""
        if self.winner:
            return
        for p in self.players:
            if p.alive and not p.is_native and not p.is_human:
                ai.take_turn(self, p)
        ai.native_turn(self)
        self._end_of_round()
        if not self.winner:
            ai.run_automation(self, self.human)

    def _end_of_round(self):
        for p in self.players:
            if p.is_native or not p.alive:
                continue
            self._process_player(p)
        self._process_units()
        self._spawn_natives()
        self.update_territory()
        for p in self.players:
            if not p.is_native and p.alive:
                self.update_visibility(p.id)
        self._check_eliminations()
        self.turn += 1
        result = check_victory(self)
        if result and not self.winner:
            self.winner = result
            self.notify(None, f"{self.players[result[0]].name} achieves a {result[1]} victory!")

    def _process_player(self, p):
        total_econ = total_labs = total_upkeep = 0
        bases = sorted(self.player_bases(p.id), key=lambda b: b.id)
        for b in bases:
            self.assign_workers(b)
            rep = self.base_report(b)
            total_econ += rep["econ"]
            total_labs += rep["labs"]
            total_upkeep += rep["upkeep"]
            if rep["rioting"]:
                self.notify(p.id, f"Drone riots in {b.name}! Production halted.", (b.x, b.y))
            # Growth
            b.nutrients += rep["nutrient_surplus"]
            if b.nutrients >= rep["growth_threshold"]:
                if b.pop < rep["pop_cap"]:
                    b.pop += 1
                    b.nutrients = 0
                    self.notify(p.id, f"{b.name} grows to size {b.pop}.", (b.x, b.y))
                else:
                    b.nutrients = rep["growth_threshold"]
            elif b.nutrients < 0:
                if b.pop > 1:
                    b.pop -= 1
                    self.notify(p.id, f"Starvation in {b.name}! Population falls to {b.pop}.", (b.x, b.y))
                b.nutrients = 0
            # Production
            if b.production == ("special", "stockpile"):
                total_econ += rep["minerals_net"]
            else:
                b.minerals += rep["minerals_net"]
                self._check_production(b)
        p.credits += total_econ - total_upkeep
        while p.credits < 0:
            candidates = [(b, f) for b in bases for f in b.facilities if FACILITIES[f].upkeep > 0]
            if not candidates:
                p.credits = 0
                break
            b, f = max(candidates, key=lambda bf: FACILITIES[bf[1]].upkeep)
            b.facilities.discard(f)
            p.credits += FACILITIES[f].cost // 2
            self.notify(p.id, f"Energy shortfall! {FACILITIES[f].name} in {b.name} sold off.", (b.x, b.y))
        self._research(p, total_labs)

    def _check_production(self, b):
        item = b.production
        cost = self.item_cost(item)
        if b.minerals < cost:
            return
        kind, iid = item
        p = self.players[b.owner]
        pos = (b.x, b.y)
        if kind == "unit":
            ut = UNITS[iid]
            if ut.colony and b.pop <= 1:
                if b.minerals == cost:
                    self.notify(p.id, f"{b.name} must reach size 2 to complete a Colony Pod.", pos)
                return
            if ut.colony:
                b.pop -= 1
            self._create_unit(iid, p.id, b.x, b.y, home=b.id)
            self.notify(p.id, f"{b.name} completes {ut.name}.", pos)
        elif kind == "facility":
            b.facilities.add(iid)
            self.notify(p.id, f"{b.name} completes {FACILITIES[iid].name}.", pos)
        elif kind == "project":
            if iid in self.projects_built:
                self.notify(p.id, f"{PROJECTS[iid].name} was already completed elsewhere.", pos)
                b.production = ("special", "stockpile")
                ai.choose_production(self, b)
                return
            self.projects_built[iid] = b.id
            self.notify(None, f"The {p.name} completes the secret project {PROJECTS[iid].name} in {b.name}!", pos)
            if iid == "orbital_survey":
                p.explored = bytearray(b"\x01" * len(p.explored))
            if iid == "ascension_engine" and not self.winner:
                self.winner = (p.id, "Transcendence")
        b.minerals -= cost
        # Next item: queue first, otherwise keep building units, pick a facility for anything else.
        if b.queue:
            b.production = b.queue.pop(0)
        elif kind == "unit" and not p.is_human:
            ai.choose_production(self, b)
        elif kind != "unit":
            ai.choose_production(self, b)
            if p.is_human:
                self.notify(p.id, f"{b.name} is now building {self.item_name(b.production)}.", pos)
        if b.production not in self.production_options(b):
            ai.choose_production(self, b)

    def _process_units(self):
        for u in list(self.units.values()):
            if u.id not in self.units:
                continue
            owner = self.players[u.owner]
            full = self.full_moves(u)
            # Terraforming progress
            if u.terraform:
                kind, left = u.terraform
                left -= 2 if self.has_project(u.owner, "engineering_corps") else 1
                if left <= 0:
                    self._complete_terraform(u, kind)
                    u.terraform = None
                    if u.orders == "terraform":
                        u.orders = None
                    if owner.is_human and u.orders != "auto":
                        self.notify(u.owner, f"Former completes {TERRAFORMS[kind].name}.", (u.x, u.y))
                else:
                    u.terraform = (kind, left)
            # Healing
            if u.hp < MAX_HP and u.moves_left >= full:
                in_base = self.base_at(u.x, u.y) is not None
                u.hp = min(MAX_HP, u.hp + (3 if in_base else 1))
            if u.orders == "fortify":
                u.fortified = True
            u.moves_left = full if not u.terraform else 0
            u.age += 1
            if u.type.native and u.age > 40 and self.rng.random() < 0.1:
                self.kill_unit(u)

    def _spawn_natives(self):
        if self.turn < 6:
            return
        worms = sum(1 for u in self.units.values() if u.type.native)
        land = sum(1 for t in self.world.all_tiles() if t.is_land)
        cap = land // 150 + self.turn // 40
        if worms >= cap:
            return
        fungus = [t for t in self.world.all_tiles() if t.fungus and t.is_land]
        rng = self.rng
        for _ in range(2):
            if not fungus or rng.random() > 0.35:
                continue
            t = rng.choice(fungus)
            crowded = False
            for x, y in self.world.radius(t.x, t.y, 2):
                if self.unit_pos.get((x, y)) or (x, y) in self.base_pos:
                    crowded = True
                    break
            if not crowded:
                self._create_unit("xenoworm", NATIVE_ID, t.x, t.y)

    def _check_eliminations(self):
        for p in self.players:
            if p.is_native or not p.alive:
                continue
            if not any(b.owner == p.id for b in self.bases.values()) and \
                    not any(u.owner == p.id and u.type.colony for u in self.units.values()):
                if self.turn > 1:
                    p.alive = False
                    for u in list(self.units.values()):
                        if u.owner == p.id:
                            self.kill_unit(u)
                    self.notify(None, f"The {p.name} has been eliminated!")
                    if p.is_human and not self.winner:
                        survivors = [q for q in self.players if q.alive and not q.is_native]
                        self.winner = (survivors[0].id if survivors else NATIVE_ID, "Conquest")

    # ------------------------------------------------------------------
    # Scores
    # ------------------------------------------------------------------
    def score(self, pid):
        p = self.players[pid]
        pop = sum(b.pop for b in self.bases.values() if b.owner == pid)
        projects = sum(1 for pr in self.projects_built if self.project_owner(pr) == pid)
        return pop * 2 + len(p.techs) * 3 + projects * 10 + p.credits // 50
