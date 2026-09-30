"""Computer opponents, native life behaviour, and automation for human units.

The AI is intentionally straightforward: expand, develop, defend, and attack when it
feels strong. It uses the same public rules API as the human player.
"""
from . import ai_military, diplomacy
from .data import UNITS, FACILITIES, PROJECTS, TECHS
from .entities import MOVE_POINTS, NATIVE_ID
from .pathfinding import find_path, reachable
from .world import FLAT, ROLLING, ROCKY


# ----------------------------------------------------------------------
# Research and production choices
# ----------------------------------------------------------------------
CATEGORY_WEIGHT = {
    "discover": lambda f: 0.6 + f.science,
    "build": lambda f: 1.0 + f.expansion * 0.3,
    "conquer": lambda f: 0.5 + f.aggression,
    "explore": lambda f: 0.9,
}


def choose_research(game, p):
    options = game.available_techs(p.id)
    if not options:
        return None
    f = p.faction

    def value(t):
        w = CATEGORY_WEIGHT[t.category](f) if f else 1.0
        # Prefer cheap (early era) techs, but the faction's taste bends it.
        return w / (1 + t.era) + game.rng.random() * 0.3

    return max(options, key=value).id


def best_unit(game, pid, role, sea=False):
    units = [u for u in game.buildable_units(pid) if (u.domain == "sea") == sea
             and not u.colony and not u.former and not u.capacity]
    if not units:
        return None
    if role == "defend":
        return max(units, key=lambda u: (u.defense, -u.cost)).id
    return max(units, key=lambda u: (u.attack * (1 + 0.3 * (u.moves - 1)), -u.cost)).id


def military_strength(game, pid):
    return sum(u.type.attack + u.type.defense for u in game.units.values()
               if u.owner == pid and u.type.military)


def at_war_with_anyone(game, p):
    return any(r == "war" and game.players[o].alive for o, r in p.relations.items())


def defenders_at(game, base):
    return [u for u in game.units_at(base.x, base.y)
            if u.owner == base.owner and u.type.military and not u.carried_by]


def choose_production(game, base):
    p = game.players[base.owner]
    f = p.faction
    opts = game.production_options(base)
    opt_set = set(opts)
    rep = base.last_report or game.base_report(base)
    bases = game.player_bases(p.id)
    units = game.player_units(p.id)
    war = at_war_with_anyone(game, p)

    defenders = len(defenders_at(game, base))
    early = game.turn <= 12 and not war  # rush expansion during planetfall; worms appear later
    if (defenders == 0 and not early) or (war and defenders < 2 and base.pop >= 3):
        uid = best_unit(game, p.id, "defend")
        if uid:
            base.production = ("unit", uid)
            return

    pods = sum(1 for u in units if u.type.colony) + sum(
        1 for b in bases if b.production == ("unit", "colony_pod") and b.id != base.id)
    want_bases = 5 + int((f.expansion if f else 0.5) * 10)
    if ((base.pop >= 2 or early) and pods < 2 and len(bases) < want_bases and not p.ai_state.get("no_sites")
            and not (p.is_human and pods >= (2 if early else 1))):
        base.production = ("unit", "colony_pod")
        return

    formers = sum(1 for u in units if u.type.former) + sum(
        1 for b in bases if b.production == ("unit", "former") and b.id != base.id)
    if formers < max(1, int(len(bases) * 0.8)) and base.pop >= 2:
        base.production = ("unit", "former")
        return

    op = p.ai_state.get("op") or {}
    if op.get("need_transport") == base.id and game.is_coastal(base) and ("unit", "transport") in opt_set:
        base.production = ("unit", "transport")
        return
    wanted = ai_military.attackers_wanted(game, p)
    have = sum(1 for u in units if ai_military.is_offensive(u))
    if wanted and have < wanted and rep["minerals_net"] >= 2 and \
            game.rng.random() < 0.5 + (f.aggression if f else 0.5) * 0.4:
        uid = best_unit(game, p.id, "attack")
        if uid:
            base.production = ("unit", uid)
            return

    # Facilities, scored by usefulness.
    best, best_score = None, 0.0
    sci = f.science if f else 0.5
    for kind, iid in opts:
        if kind == "facility":
            fac = FACILITIES[iid]
            s = 0.0
            if fac.tile_bonus:
                s += 3
            if fac.drones < 0 and rep["drones"] > 0:
                s += 4 + rep["drones"] * 2
            if fac.psych_pct and rep["drones"] > 0:
                s += 1
            if fac.labs_pct:
                s += rep["labs"] * fac.labs_pct / 100 * (1 + sci) + 0.5
            if fac.econ_pct:
                s += rep["econ"] * fac.econ_pct / 100 + 0.5
            if fac.minerals_pct:
                s += rep["minerals"] * fac.minerals_pct / 100
                if fac.drones > 0:
                    s -= 2
            if fac.pop_cap and fac.pop_cap > rep["pop_cap"] and base.pop >= rep["pop_cap"] - 1:
                s += 6
            if fac.defense_pct:
                s += 3 if war else 0.5
            s -= fac.upkeep * 1.2
            s = s * 10 / max(10, fac.cost) * 3
            if s > best_score:
                best, best_score = (kind, iid), s
        elif kind == "project":
            s = 2.5 + rep["minerals_net"] * 0.2
            if iid == "ascension_engine":
                s = 50
            if s > best_score and game.rng.random() < 0.6:
                best, best_score = (kind, iid), s
    if best:
        base.production = best
        return
    if len([u for u in units if u.type.military]) < len(bases) * 2:
        uid = best_unit(game, p.id, "attack" if war else "defend")
        if uid:
            base.production = ("unit", uid)
            return
    if ("unit", "former") in opt_set and formers < len(bases) * 1.5:
        base.production = ("unit", "former")
        return
    base.production = ("special", "stockpile")


# ----------------------------------------------------------------------
# Turn driver
# ----------------------------------------------------------------------
def take_turn(game, p):
    if p.current_tech is None:
        p.current_tech = choose_research(game, p)
    bases = game.player_bases(p.id)
    rioting = any(b.rioting for b in bases)
    sci = p.faction.science if p.faction else 0.5
    psych = min(4, p.alloc[1] + 1) if rioting else max(0, p.alloc[1] - 1)
    labs = min(10 - psych, int(4 + sci * 3))
    p.alloc = [10 - psych - labs, psych, labs]

    ai_military.plan_wars(game, p)
    diplomacy.ai_diplomacy(game, p)

    for b in bases:
        if b.production not in game.production_options(b):
            choose_production(game, b)
        # Emergency: undefended base at war - buy a defender.
        if not defenders_at(game, b) and at_war_with_anyone(game, p) and b.production[0] == "unit" \
                and UNITS[b.production[1]].military and game.buy_cost(b) <= p.credits:
            game.buy_production(b)
    reserve = 60 + 10 * len(bases)
    for b in sorted(bases, key=lambda b: game.buy_cost(b)):
        c = game.buy_cost(b)
        if b.production[0] == "project" and c > (p.credits - reserve) // 2:
            continue
        if 0 < c <= p.credits - reserve:
            game.buy_production(b)

    controlled = ai_military.run_operation(game, p)
    order = sorted(game.player_units(p.id), key=lambda u: (not u.type.colony, u.id))
    for u in order:
        if u.id in game.units and u.id not in controlled:
            act_unit(game, u)


def run_automation(game, p):
    """Move the human's automated units (goto, explore, automated formers)."""
    for u in sorted(game.player_units(p.id), key=lambda u: u.id):
        if u.id not in game.units or u.moves_left <= 0:
            continue
        if u.orders == "goto":
            game.follow_path(u)
        elif u.orders == "explore":
            if not act_explore(game, u):
                u.orders = None
                game.notify(p.id, f"{u.name} has nothing left to explore.", (u.x, u.y))
        elif u.orders == "auto" and u.type.former:
            act_former(game, u)


def act_unit(game, u):
    t = u.type
    if u.carried_by:
        return
    if t.colony:
        act_colony(game, u)
    elif t.former:
        act_former(game, u)
    elif t.domain == "sea":
        act_sea(game, u)
    elif t.military:
        act_military(game, u)


def _go(game, u, x, y):
    """Move toward (x, y). Returns True if the unit is (now) there."""
    if (u.x, u.y) == (x % game.world.width, y):
        return True
    if u.goal != (x % game.world.width, y) or not u.path:
        path = find_path(game, u, x, y)
        if path is None:
            u.goal, u.path = None, []
            return False
        u.goal, u.path = (x % game.world.width, y), path
    saved = u.orders
    u.orders = "goto"
    game.follow_path(u)
    if u.id in game.units:
        u.orders = saved if saved != "goto" else None
        return (u.x, u.y) == (x % game.world.width, y)
    return False


# ----------------------------------------------------------------------
# Colony pods
# ----------------------------------------------------------------------
def site_score(game, pid, x, y):
    world = game.world
    s = 0.0
    coastal = False
    for nx, ny in world.base_radius(x, y):
        t = world.tiles[nx][ny]
        if t.owner is not None and t.owner != pid:
            s -= 0.5
            continue
        if t.is_ocean:
            s += 1.0 if t.is_shelf else 0.6
            if world.distance(nx, ny, x, y) == 1:
                coastal = True
        elif t.fungus:
            s += 0.2
        else:
            s += 0.6 + t.rainfall * 0.5 + (0.4 if t.rockiness == ROLLING else 0) + (0.2 if t.rockiness == ROCKY else 0)
        if t.special:
            s += 1.5
        for b in game.bases.values():
            if world.distance(b.x, b.y, nx, ny) <= 2:
                s -= 0.4
                break
    if coastal:
        s += 2
    return s


def act_colony(game, u):
    p = game.players[u.owner]
    if not game.player_bases(p.id):
        ok, _ = game.can_found_base(u)
        if ok:
            game.found_base(u)
            return
    goal = u.ai_goal
    if goal and not _valid_site(game, u.owner, *goal):
        goal = None
    if not goal:
        reach = reachable(game, u, MOVE_POINTS * 12)
        best, best_s = None, -1e9
        for (x, y), cost in reach.items():
            if not _valid_site(game, u.owner, x, y):
                continue
            s = site_score(game, u.owner, x, y) - cost / MOVE_POINTS * 0.9
            if s > best_s:
                best, best_s = (x, y), s
        if best is None or best_s < 4:
            p.ai_state["no_sites"] = True
            ok, _ = game.can_found_base(u)
            if ok:
                game.found_base(u)
            else:
                u.orders = "sentry" if not p.is_human else None
            return
        goal = best
        u.ai_goal = goal
    if _go(game, u, *goal):
        if u.id in game.units and game.can_found_base(u)[0]:
            game.found_base(u)
    elif u.id in game.units and not u.path:
        u.ai_goal = None


def _valid_site(game, pid, x, y):
    t = game.world.tiles[x][y]
    if not t.is_land or t.fungus:
        return False
    if t.owner is not None and t.owner != pid:
        return False
    if y < 3 or y >= game.world.height - 3:
        return False
    for b in game.bases.values():
        if game.world.distance(b.x, b.y, x, y) < 3:
            return False
    return True


# ----------------------------------------------------------------------
# Formers
# ----------------------------------------------------------------------
def desired_improvement(game, pid, t):
    if (t.x, t.y) in game.base_pos or t.is_ocean:
        return None
    imp = t.improvements
    if t.fungus:
        return "remove_fungus" if game.has_tech(pid, "centauri_ecology") else None
    if "forest" in imp:
        return None
    if t.rockiness == ROCKY:
        return None if "mine" in imp else "mine"
    if t.rainfall >= 1:
        if "farm" not in imp:
            return "farm"
        if "solar" not in imp and "mine" not in imp:
            return "solar"
        return None
    if t.rockiness == ROLLING:
        return None if "mine" in imp else "mine"
    if game.has_tech(pid, "centauri_ecology"):
        return "forest"
    return None if "solar" in imp else "solar"


def act_former(game, u):
    if u.terraform:
        return
    pid = u.owner
    here = game.world.tiles[u.x][u.y]
    job_here = desired_improvement(game, pid, here)
    if job_here and (here.owner == pid) and _former_tile_free(game, u, here.x, here.y):
        if game.start_terraform(u, job_here):
            return
    targets = []
    claimed = {o.ai_goal for o in game.player_units(pid) if o.type.former and o.id != u.id}
    for b in game.player_bases(pid):
        worked = set(b.worked)
        for x, y in game.world.base_radius(b.x, b.y):
            t = game.world.tiles[x][y]
            if t.owner != pid or (x, y) in claimed:
                continue
            job = desired_improvement(game, pid, t)
            if not job or not _former_tile_free(game, u, x, y):
                continue
            d = game.world.distance(u.x, u.y, x, y)
            score = d - (3 if (x, y) in worked else 0)
            targets.append((score, x, y))
    if not targets:
        # Nothing to do - build roads between bases, else wait in the nearest base.
        if "road" not in here.improvements and here.owner == pid and here.is_land and \
                any(game.world.distance(b.x, b.y, u.x, u.y) <= 3 for b in game.player_bases(pid)):
            game.start_terraform(u, "road")
        return
    targets.sort()
    for _, x, y in targets[:4]:
        u.ai_goal = (x, y)
        if _go(game, u, x, y):
            if u.id in game.units and u.moves_left >= 0:
                job = desired_improvement(game, pid, game.world.tiles[x][y])
                if job:
                    game.start_terraform(u, job)
            return
        if u.id not in game.units or u.path:
            return
    u.ai_goal = None


def _former_tile_free(game, u, x, y):
    return not any(o.id != u.id and o.type.former and o.terraform for o in game.units_at(x, y))


# ----------------------------------------------------------------------
# Military
# ----------------------------------------------------------------------
def act_explore(game, u):
    """Move toward the nearest unexplored area or supply pod. Returns False if nothing is left."""
    pid = u.owner
    reach = reachable(game, u, MOVE_POINTS * 15)
    best, best_s = None, 1e9
    world = game.world
    for (x, y), cost in reach.items():
        if (x, y) == (u.x, u.y):
            continue
        t = world.tiles[x][y]
        s = None
        if t.supply_pod and game.is_explored(pid, x, y):
            s = cost - 12
        else:
            unexplored = sum(1 for nx, ny in world.radius(x, y, 1) if not game.is_explored(pid, nx, ny))
            if unexplored:
                s = cost - unexplored * 0.5
        if s is not None and s < best_s:
            best, best_s = (x, y), s
    if best is None:
        return False
    _go(game, u, *best)
    return True


def act_military(game, u):
    p = game.players[u.owner]
    world = game.world
    base_here = game.base_at(u.x, u.y)
    war = at_war_with_anyone(game, p)
    if base_here and base_here.owner == p.id:
        need = 1 + (1 if war or base_here.pop >= 5 else 0)
        defs = sorted(defenders_at(game, base_here), key=lambda d: (-d.type.defense, d.id))
        if u in defs[:need]:
            if u.orders != "fortify":
                game.fortify(u)
            return

    # Opportunistic attacks on adjacent enemies.
    if game.can_attack(u):
        for nx, ny in world.neighbors(u.x, u.y):
            others, eb = game.hostile_at(u, nx, ny)
            enemies = [o for o in others if p.at_war(o.owner)]
            if enemies and world.tiles[nx][ny].is_land:
                if game.combat_odds(u, nx, ny) > 0.6:
                    game.move_unit(u, nx, ny)
                    return
            elif eb and not others and p.at_war(eb.owner):
                game.move_unit(u, nx, ny)
                return

    # Undefended home bases take priority.
    bases = game.player_bases(p.id)
    heading = {o.ai_goal for o in game.player_units(p.id) if o.id != u.id}
    empty = [b for b in bases if not defenders_at(game, b) and (b.x, b.y) not in heading]
    if empty:
        b = min(empty, key=lambda b: world.distance(b.x, b.y, u.x, u.y))
        if world.distance(b.x, b.y, u.x, u.y) <= 12:
            u.ai_goal = (b.x, b.y)
            if _go(game, u, b.x, b.y) and u.id in game.units:
                game.fortify(u)
            return

    # Offensive: march on the nearest enemy base.
    if war and game.can_attack(u) and u.type.attack >= u.type.defense:
        targets = [b for b in game.bases.values() if p.at_war(b.owner) and b.owner != p.id
                   and game.is_explored(p.id, b.x, b.y)]
        if targets:
            b = min(targets, key=lambda b: world.distance(b.x, b.y, u.x, u.y))
            if world.distance(b.x, b.y, u.x, u.y) <= 20:
                u.ai_goal = (b.x, b.y)
                if world.distance(b.x, b.y, u.x, u.y) == 1:
                    if not game.units_at(b.x, b.y) or game.combat_odds(u, b.x, b.y) > 0.4:
                        game.move_unit(u, b.x, b.y)
                    else:
                        game.fortify(u)
                    return
                path = find_path(game, u, b.x, b.y)
                if path and len(path) > 1:
                    stop = path[-2]
                    _go(game, u, *stop)
                    return

    # Hunt nearby native life.
    if game.can_attack(u):
        for x, y in world.radius(u.x, u.y, 3):
            worms = [o for o in game.units_at(x, y) if o.owner == NATIVE_ID]
            if worms and world.tiles[x][y].is_land:
                if world.distance(x, y, u.x, u.y) == 1:
                    if game.combat_odds(u, x, y) > 0.55:
                        game.move_unit(u, x, y)
                        return
                else:
                    path = find_path(game, u, x, y)
                    if path and len(path) > 1:
                        _go(game, u, *path[-2])
                        return

    # Scouts explore early on.
    if u.type_id == "scout" or (game.turn < 30 and u.type.moves > 1):
        if act_explore(game, u):
            return

    # Otherwise reinforce the weakest base.
    if bases:
        b = min(bases, key=lambda b: (len(defenders_at(game, b)) - b.pop / 4,
                                     world.distance(b.x, b.y, u.x, u.y)))
        u.ai_goal = (b.x, b.y)
        if _go(game, u, b.x, b.y) and u.id in game.units:
            game.fortify(u)
    else:
        game.fortify(u)


def act_sea(game, u):
    if u.type.capacity:
        base = game.base_at(u.x, u.y)
        if base:
            u.orders = "sentry"
        return
    if not act_explore(game, u):
        bases = [b for b in game.player_bases(u.owner) if game.is_coastal(b)]
        if bases:
            b = min(bases, key=lambda b: game.world.distance(b.x, b.y, u.x, u.y))
            _go(game, u, b.x, b.y)


# ----------------------------------------------------------------------
# Native life
# ----------------------------------------------------------------------
def native_turn(game):
    world = game.world
    rng = game.rng
    for u in list(game.player_units(NATIVE_ID)):
        if u.id not in game.units:
            continue
        target = None
        if rng.random() < 0.75:
            best_d = 99
            for x, y in world.radius(u.x, u.y, 4):
                t = world.tiles[x][y]
                if not t.is_land:
                    continue
                prey = [o for o in game.units_at(x, y) if o.owner != NATIVE_ID]
                b = game.base_at(x, y)
                if b and game.turn < 20 and not prey:
                    continue
                if prey or b:
                    d = world.distance(x, y, u.x, u.y)
                    if d < best_d:
                        best_d, target = d, (x, y)
        if target:
            for _ in range(3):
                if u.id not in game.units or u.moves_left <= 0:
                    break
                if world.distance(u.x, u.y, *target) == 1:
                    game.move_unit(u, *target)
                    break
                path = find_path(game, u, *target, max_nodes=400)
                if not path:
                    break
                if game.move_unit(u, *path[0]) != "moved":
                    break
        else:
            opts = [(x, y) for x, y in world.neighbors(u.x, u.y)
                    if world.tiles[x][y].is_land and not game.units_at(x, y) and not game.base_at(x, y)]
            if opts:
                fung = [o for o in opts if world.tiles[o[0]][o[1]].fungus]
                game.move_unit(u, *rng.choice(fung or opts))
