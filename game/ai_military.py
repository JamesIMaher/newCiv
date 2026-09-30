"""AI war planning and coordinated operations.

An AI faction that wants a war first *plans* it: it picks a rival, builds up a strike force, and
gathers it at a staging base near the chosen target. Only when the force is ready does it declare
war and attack together. Targets across the sea are reached by loading the force onto transports,
sailing to a landing beach beside the target, and going ashore.
"""
from . import diplomacy
from .entities import MOVE_POINTS
from .pathfinding import find_path


def is_offensive(u):
    t = u.type
    return (t.domain == "land" and not t.colony and not t.former and not t.native
            and u.type_id != "scout" and t.attack > t.defense)


def strength_of(game, pid):
    return sum(u.type.attack + u.type.defense for u in game.units.values()
               if u.owner == pid and u.type.military and not u.type.native)


def _defenders(game, base):
    return [u for u in game.units_at(base.x, base.y) if u.owner == base.owner and u.type.military]


# ---------------------------------------------------------------------------
# Strategic level: who to fight, and when to declare
# ---------------------------------------------------------------------------
def plan_wars(game, p):
    st = p.ai_state
    f = p.faction
    rng = game.rng
    plan = st.get("plan")
    if plan:
        tgt = game.players[plan["target"]]
        rel = p.relations.get(plan["target"])
        if not tgt.alive or rel == "pact" or rel is None:
            plan = None
        elif rel == "peace":
            op = st.get("op")
            ready = op and op.get("ready")
            waited = game.turn - plan["since"]
            if diplomacy.attitude(game, p.id, plan["target"]) > 30 or waited > 60:
                plan = None           # tempers cooled, or the moment passed
            elif ready or waited > 35:
                game.declare_war(p.id, plan["target"])
                plan = None
    enemies = [o for o, r in p.relations.items() if r == "war" and game.players[o].alive]
    if not plan and not enemies and game.turn > 30:
        lead = diplomacy.leader(game)
        mine = strength_of(game, p.id)
        best, best_score = None, 0.0
        my_bases = game.player_bases(p.id)
        for o_id, rel in p.relations.items():
            o = game.players[o_id]
            if rel != "peace" or not o.alive:
                continue
            theirs = max(1, strength_of(game, o_id))
            near = min((game.world.distance(a.x, a.y, b.x, b.y) for a in my_bases
                        for b in game.player_bases(o_id)), default=99)
            score = (f.aggression * 1.2 - diplomacy.attitude(game, p.id, o_id) / 60
                     + min(1.5, mine / theirs - 1) + (0.6 if near < 12 else -0.4 if near > 25 else 0))
            if lead and lead[0] == o_id and lead[2] >= 0.5:
                score += 1.5 * lead[2]     # stop the runaway leader
            if score > best_score:
                best, best_score = o_id, score
        if best is not None and rng.random() < 0.03 * best_score:
            plan = {"target": best, "since": game.turn}
            game.notify(best, f"Intelligence reports that the {p.name} is massing forces.")
    st["plan"] = plan
    # AI-to-AI wars can end by mutual agreement.
    for o_id in enemies:
        o = game.players[o_id]
        if not o.is_human and rng.random() < 0.1 \
                and diplomacy.will_accept_peace(game, p.id, o_id)[0] \
                and diplomacy.will_accept_peace(game, o_id, p.id)[0]:
            game.make_peace(p.id, o_id)


def war_targets(game, p):
    targets = [o for o, r in p.relations.items() if r == "war" and game.players[o].alive]
    plan = p.ai_state.get("plan")
    if plan and plan["target"] not in targets:
        targets.append(plan["target"])
    return targets


def attackers_wanted(game, p):
    op = p.ai_state.get("op")
    if not war_targets(game, p):
        return 0
    return (op or {}).get("need", 4) + 1


# ---------------------------------------------------------------------------
# Operational level: gather, (embark, sail, land), attack
# ---------------------------------------------------------------------------
def _pick_target(game, p, owners):
    world = game.world
    my_bases = game.player_bases(p.id)
    if not my_bases:
        return None
    best, best_s = None, 1e9
    for b in game.bases.values():
        if b.owner not in owners or not game.is_explored(p.id, b.x, b.y):
            continue
        d = min(world.distance(b.x, b.y, m.x, m.y) for m in my_bases)
        s = d + 3 * len(_defenders(game, b)) - b.pop * 0.5
        if s < best_s:
            best, best_s = b, s
    return best


def _staging_base(game, p, target, naval):
    bases = game.player_bases(p.id)
    if naval:
        bases = [b for b in bases if game.is_coastal(b)]
    if not bases:
        return None
    return min(bases, key=lambda b: game.world.distance(b.x, b.y, target.x, target.y))


def _same_landmass(game, a, b):
    w = game.world
    return w.tiles[a.x][a.y].continent == w.tiles[b.x][b.y].continent


def run_operation(game, p):
    """Moves the strike force. Returns the set of unit ids it controlled this turn."""
    from .ai import _go
    st = p.ai_state
    owners = war_targets(game, p)
    if not owners:
        st.pop("op", None)
        return set()
    op = st.get("op")
    if op:
        tb = game.bases.get(op["target"])
        sb = game.bases.get(op["stage"])
        if tb is None or tb.owner not in owners or sb is None or sb.owner != p.id:
            op = None
    if not op:
        tb = _pick_target(game, p, owners)
        if tb is None:
            st.pop("op", None)
            return set()
        naval = False
        sb = _staging_base(game, p, tb, False)
        if sb and not _same_landmass(game, sb, tb):
            naval = True
            sb = _staging_base(game, p, tb, True)
        if sb is None:
            st.pop("op", None)
            return set()
        op = {"target": tb.id, "stage": sb.id, "naval": naval, "phase": "gather", "transport": None,
              "landing": None, "started": game.turn, "ready": False}
        st["op"] = op
    tb, sb = game.bases[op["target"]], game.bases[op["stage"]]
    op["need"] = min(8, max(3, 2 * len(_defenders(game, tb)) + 1))
    at_war = p.relations.get(tb.owner) == "war"
    strike = [u for u in game.player_units(p.id) if is_offensive(u)]
    controlled = {u.id for u in strike}
    world = game.world

    if op["phase"] == "gather":
        gathered = 0
        for u in strike:
            if u.carried_by:
                continue
            if world.distance(u.x, u.y, sb.x, sb.y) <= 1:
                gathered += 1
                if (u.x, u.y) != (sb.x, sb.y) and not op["naval"]:
                    game.fortify(u)
            elif u.moves_left > 0:
                _go(game, u, sb.x, sb.y)
        op["ready"] = gathered >= op["need"]
        overdue = game.turn - op["started"] > 30 and gathered >= 2
        if at_war and (op["ready"] or overdue):
            op["phase"] = "embark" if op["naval"] else "attack"
            game.notify(tb.owner, f"A {p.name} strike force is on the move!")

    if op["phase"] == "embark":
        tr = game.units.get(op["transport"]) if op["transport"] else None
        if tr is None:
            idle = [u for u in game.player_units(p.id) if u.type.capacity and not u.cargo]
            tr = min(idle, key=lambda u: world.distance(u.x, u.y, sb.x, sb.y)) if idle else None
            op["transport"] = tr.id if tr else None
        if tr is None:
            op["need_transport"] = sb.id
            for u in strike:
                if not u.carried_by and world.distance(u.x, u.y, sb.x, sb.y) > 0 and u.moves_left > 0:
                    _go(game, u, sb.x, sb.y)
            return controlled
        op.pop("need_transport", None)
        controlled.add(tr.id)
        if (tr.x, tr.y) != (sb.x, sb.y):
            _go(game, tr, sb.x, sb.y)
            return controlled
        for u in strike:
            if not u.carried_by and (u.x, u.y) == (sb.x, sb.y):
                game.board(u, tr)
            elif not u.carried_by and u.moves_left > 0:
                _go(game, u, sb.x, sb.y)
        waiting = [u for u in strike if not u.carried_by and world.distance(u.x, u.y, sb.x, sb.y) <= 3]
        if tr.cargo and (len(tr.cargo) >= tr.type.capacity or not waiting):
            op["landing"] = _landing_tile(game, tr, tb)
            if op["landing"] is None:
                op["naval"] = False
                op["phase"] = "attack"
            else:
                op["phase"] = "sail"

    if op["phase"] == "sail":
        tr = game.units.get(op["transport"])
        if tr is None or not tr.cargo:
            op["phase"] = "attack"
        else:
            controlled.add(tr.id)
            lx, ly = op["landing"]
            if (tr.x, tr.y) != (lx, ly):
                if not _go(game, tr, lx, ly) and not tr.path:
                    op["landing"] = _landing_tile(game, tr, tb)
                    if op["landing"] is None:
                        op["phase"] = "attack"
            if tr.id in game.units and (tr.x, tr.y) == tuple(op["landing"] or (None, None)):
                for cid in list(tr.cargo):
                    c = game.units.get(cid)
                    if c is None:
                        continue
                    shore = [(x, y) for x, y in world.neighbors(tr.x, tr.y)
                             if world.tiles[x][y].is_land and not game.hostile_at(c, x, y)[0]
                             and game.base_at(x, y) is None]
                    if shore:
                        c.moves_left = max(c.moves_left, MOVE_POINTS)
                        x, y = min(shore, key=lambda s: world.distance(s[0], s[1], tb.x, tb.y))
                        game.move_unit(c, x, y)
                if not tr.cargo:
                    op["phase"] = "attack"
                    tr.orders = None
                    op["transport"] = None

    if op["phase"] == "attack" and at_war:
        # A siege: once enough of the force surrounds the base, it assaults in waves, strongest first.
        # Each failed attack still wears the defenders down.
        adjacent = [u for u in strike if not u.carried_by and world.distance(u.x, u.y, tb.x, tb.y) == 1]
        assault = len(adjacent) >= max(2, op["need"] - 1)
        for u in sorted(strike, key=lambda u: -u.type.attack * u.hp):
            if u.carried_by or u.moves_left <= 0 or u.id not in game.units:
                continue
            d = world.distance(u.x, u.y, tb.x, tb.y)
            if d == 1:
                if tb.id not in game.bases or tb.owner == p.id:
                    break
                odds = game.combat_odds(u, tb.x, tb.y) if game.units_at(tb.x, tb.y) else 1.0
                if odds > 0.4 or (assault and odds > 0.1):
                    game.move_unit(u, tb.x, tb.y)
                else:
                    game.fortify(u)
                continue
            path = find_path(game, u, tb.x, tb.y)
            if path and len(path) > 1:
                # Strike anything blocking the way first.
                nx, ny = path[0]
                others, _ = game.hostile_at(u, nx, ny)
                if others and p.at_war(others[0].owner) and game.combat_odds(u, nx, ny) > 0.45:
                    game.move_unit(u, nx, ny)
                    continue
                _go(game, u, *path[-2])
            elif path is None and not op["naval"]:
                op["naval"] = True
                op["phase"] = "embark"
                naval_sb = _staging_base(game, p, tb, True)
                if naval_sb:
                    op["stage"] = naval_sb.id
                break
    return controlled


def _landing_tile(game, transport, target):
    """Ocean tile next to land near the target that the transport can reach."""
    world = game.world
    cands = []
    for x, y in world.radius(target.x, target.y, 4):
        t = world.tiles[x][y]
        if not t.is_ocean or game.hostile_at(transport, x, y)[0]:
            continue
        shore = [n for n in world.neighbors(x, y) if world.tiles[n[0]][n[1]].is_land
                 and world.tiles[n[0]][n[1]].continent == world.tiles[target.x][target.y].continent]
        if shore:
            d = min(world.distance(sx, sy, target.x, target.y) for sx, sy in shore)
            cands.append((d, world.distance(x, y, transport.x, transport.y), x, y))
    for _, _, x, y in sorted(cands)[:6]:
        if (x, y) == (transport.x, transport.y) or find_path(game, transport, x, y, max_nodes=4000):
            return (x, y)
    return None
