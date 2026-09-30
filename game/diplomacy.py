"""Diplomacy: attitudes with memory, treaties (peace / war / pact), trades, and offers to the human.

Attitude is how one faction feels about another, from -100 (hostile) to +100 (friendly). It is
moved by events that are also remembered, so the player can see *why* a faction feels the way it
does. AI decisions (war, peace, pacts, trades) all read from it.
"""
from .data import TECHS
from .entities import NATIVE_ID
from .society import ideology_opinion

ATTITUDE_WORDS = [(50, "Friendly", (120, 220, 120)), (15, "Cordial", (170, 220, 140)),
                  (-15, "Neutral", (200, 200, 190)), (-50, "Wary", (230, 180, 90)),
                  (-999, "Hostile", (235, 100, 80))]


def attitude(game, a, b):
    return game.players[a].attitude.get(b, 0.0)


def attitude_word(value):
    for threshold, word, color in ATTITUDE_WORDS:
        if value >= threshold:
            return word, color
    return "Hostile", (235, 100, 80)


def adjust(game, a, b, amount, reason=None):
    """Faction a's opinion of b changes; reason is remembered."""
    p = game.players[a]
    if p.is_native or b == NATIVE_ID or a == b:
        return
    p.attitude[b] = max(-100.0, min(100.0, p.attitude.get(b, 0.0) + amount))
    if reason:
        p.memory.append((game.turn, b, reason, amount))
        del p.memory[:-40]


def memories_about(game, a, b, limit=4):
    """What a remembers about b, most significant recent first."""
    mem = [m for m in game.players[a].memory if m[1] == b]
    mem.sort(key=lambda m: (-abs(m[3]) * (0.97 ** (game.turn - m[0]))))
    return mem[:limit]


# ---------------------------------------------------------------------------
# Victory awareness
# ---------------------------------------------------------------------------
def victory_threats(game):
    """[(pid, kind, progress 0..1)] for every faction making real progress towards a win."""
    out = []
    alive = [p for p in game.players if p.alive and not p.is_native]
    total_bases = max(1, len(game.bases))
    for p in alive:
        # Transcendence: the tech gets you halfway, the Ascension Engine the rest.
        prog = len(p.techs) / len(TECHS) * 0.4
        if "transcendence" in p.techs:
            best = 0.0
            for b in game.player_bases(p.id):
                if b.production == ("project", "ascension_engine"):
                    best = max(best, b.minerals / game.item_cost(b.production))
            prog = 0.6 + 0.4 * best
        out.append((p.id, "Transcendence", prog))
        share = sum(1 for b in game.bases.values() if b.owner == p.id) / total_bases
        if len(alive) > 2:
            out.append((p.id, "Conquest", max(0.0, (share - 0.2) / 0.6)))
    return [t for t in out if t[2] >= 0.35]


def leader(game):
    threats = victory_threats(game)
    if not threats:
        return None
    return max(threats, key=lambda t: t[2])


# ---------------------------------------------------------------------------
# Per-round update
# ---------------------------------------------------------------------------
def update(game):
    players = [p for p in game.players if p.alive and not p.is_native]
    lead = leader(game)
    bases_by = {p.id: game.player_bases(p.id) for p in players}
    for p in players:
        for o_id in list(p.relations):
            o = game.players[o_id]
            if not o.alive:
                continue
            v = p.attitude.get(o_id, 0.0)
            # Grudges and gratitude fade slowly.
            v -= max(-0.5, min(0.5, v * 0.02))
            rel = p.relations[o_id]
            if rel == "pact":
                v += 0.4
            # Ideology: factions warm to societies built like their own, and resent their opposites.
            op = ideology_opinion(p, o)
            if op and (-40 < v < 40):
                v += 0.35 * op
            # Common enemies bring factions together.
            for third, r in p.relations.items():
                if third != o_id and r == "war" and o.relations.get(third) == "war":
                    v += 0.6
                    break
            # Bases crowding each other's borders breed resentment (up to a point)...
            close = sum(1 for a in bases_by[p.id] for b in bases_by[o_id]
                        if game.world.distance(a.x, a.y, b.x, b.y) <= 5)
            if close and v > -35:
                v -= min(0.6, close * 0.15)
            # ...while a quiet, uncrowded peace slowly builds trust.
            elif not close and rel in ("peace", "pact") and v < 25:
                v += 0.25
            # A faction racing to victory makes everyone else nervous.
            if lead and lead[0] == o_id and lead[2] >= 0.5 and v > -60:
                v -= 0.4 + lead[2]
            p.attitude[o_id] = max(-100.0, min(100.0, v))
        if p.relations and game.turn % 5 == 0:
            for o_id, r in p.relations.items():
                if r == "pact":
                    _share_maps(game.players[p.id], game.players[o_id])


def _share_maps(a, b):
    merged = bytes(x | y for x, y in zip(a.explored, b.explored))
    a.explored = bytearray(merged)
    b.explored = bytearray(merged)


# ---------------------------------------------------------------------------
# Treaties
# ---------------------------------------------------------------------------
def on_war_declared(game, a, b, broke_pact):
    """a declared war on b."""
    adjust(game, b, a, -60 if broke_pact else -35,
           "broke our pact and attacked us" if broke_pact else "declared war on us")
    for p in game.players:
        if p.is_native or not p.alive or p.id in (a, b):
            continue
        if p.relations.get(b) == "pact":
            adjust(game, p.id, a, -25, f"attacked our ally, the {game.players[b].name}")
            if not p.is_human and p.relations.get(a) != "war":
                game.notify(None, f"The {p.name} honours its pact with the {game.players[b].name}.")
                game.declare_war(p.id, a)
            elif p.is_human:
                game.notify(p.id, f"Your pact ally, the {game.players[b].name}, is at war with the "
                                  f"{game.players[a].name}. They expect your help.")
        elif p.relations.get(a) == "pact" and not p.is_human and p.relations.get(b) != "war" \
                and attitude(game, p.id, b) < 10:
            game.notify(None, f"The {p.name} joins its ally the {game.players[a].name} in the war.")
            game.declare_war(p.id, b)
        elif b in p.relations and a in p.relations:
            adjust(game, p.id, a, -5, f"started a war with the {game.players[b].name}")


def on_join_war(game, joiner, enemy):
    """Allies of joiner who were already fighting enemy are grateful."""
    for p in game.players:
        if p.relations.get(joiner) == "pact" and p.relations.get(enemy) == "war":
            adjust(game, p.id, joiner, 15, f"joined us in the war against the {game.players[enemy].name}")


def form_pact(game, a, b):
    pa, pb = game.players[a], game.players[b]
    pa.relations[b] = "pact"
    pb.relations[a] = "pact"
    adjust(game, a, b, 10, "signed a pact with us")
    adjust(game, b, a, 10, "signed a pact with us")
    _share_maps(pa, pb)
    game.notify(None, f"The {pa.name} and the {pb.name} have formed a pact.")


def cancel_pact(game, a, b):
    pa, pb = game.players[a], game.players[b]
    pa.relations[b] = "peace"
    pb.relations[a] = "peace"
    adjust(game, b, a, -20, "abandoned our pact")
    game.notify(None, f"The {pa.name} has ended its pact with the {pb.name}.")


# ---------------------------------------------------------------------------
# AI decisions
# ---------------------------------------------------------------------------
def _is_threat(game, pid):
    lead = leader(game)
    return lead is not None and lead[0] == pid and lead[2] >= 0.5


def will_accept_peace(game, ai_pid, other):
    from .ai import military_strength
    p = game.players[ai_pid]
    started = p.war_turns.get(other, game.turn)
    if game.turn - started < 5:
        return False, "It is too soon. The wounds are fresh."
    if _is_threat(game, other):
        return False, "You are too dangerous to be left in peace."
    att = attitude(game, ai_pid, other)
    mine = military_strength(game, ai_pid)
    theirs = military_strength(game, other)
    aggression = p.faction.aggression if p.faction else 0.5
    score = (theirs / max(1, mine)) - 0.9 + (att + 30) / 100 - aggression * 0.4 + (game.turn - started) / 60
    if score > 0:
        return True, ""
    return False, "Not while we are winning."


def will_accept_pact(game, ai_pid, other):
    p = game.players[ai_pid]
    if p.relations.get(other) != "peace":
        return False, "We must be at peace first."
    att = attitude(game, ai_pid, other)
    shared = any(r == "war" and game.players[other].relations.get(t) == "war" for t, r in p.relations.items())
    if _is_threat(game, other):
        return False, "We will not strengthen you further."
    need = 35 - (20 if shared else 0)
    if att >= need:
        return True, ""
    return False, "We do not trust you enough for that."


def tradeable_techs(game, giver, receiver):
    g, r = game.players[giver], game.players[receiver]
    return sorted((t for t in g.techs if t not in r.techs and all(q in r.techs for q in TECHS[t].prereqs)),
                  key=lambda t: -game.tech_cost(receiver, t))


def tech_price(game, seller, buyer, tech):
    """Credits the AI seller wants, or (None, reason) if it refuses."""
    att = attitude(game, seller, buyer)
    if game.players[seller].relations.get(buyer) == "war":
        return None, "We do not trade with enemies."
    if _is_threat(game, buyer):
        return None, "You are close enough to victory already."
    if att < -30:
        return None, "We have nothing to discuss."
    price = int(game.tech_cost(buyer, tech) * (1.7 - att / 100))
    return max(10, price), ""


def will_swap(game, ai_pid, other, ai_gives, ai_gets):
    if game.players[ai_pid].relations.get(other) == "war":
        return False, "We do not trade with enemies."
    if _is_threat(game, other):
        return False, "You are close enough to victory already."
    att = attitude(game, ai_pid, other)
    if att < -15:
        return False, "We don't trust you."
    give_v = game.tech_cost(other, ai_gives)
    get_v = game.tech_cost(ai_pid, ai_gets)
    if get_v >= give_v * (0.95 - att / 250):
        return True, ""
    return False, "That is not a fair trade."


def swap_techs(game, a, b, a_gives, b_gives):
    game.grant_tech(b, a_gives, source=f"Traded with the {game.players[a].name}")
    game.grant_tech(a, b_gives, source=f"Traded with the {game.players[b].name}")
    adjust(game, a, b, 5, "traded technology with us")
    adjust(game, b, a, 5, "traded technology with us")


def sell_tech(game, seller, buyer, tech, price):
    game.players[buyer].credits -= price
    game.players[seller].credits += price
    game.grant_tech(buyer, tech, source=f"Bought from the {game.players[seller].name}")
    adjust(game, seller, buyer, 3, "bought technology from us")


def gift(game, giver, receiver, amount):
    game.players[giver].credits -= amount
    game.players[receiver].credits += amount
    adjust(game, receiver, giver, min(25, amount / 6), f"gave us {amount} credits")


# ---------------------------------------------------------------------------
# Offers from the AI to the human player (and AI-to-AI deals)
# ---------------------------------------------------------------------------
def ai_diplomacy(game, p):
    """Called during an AI's turn: trades and pacts with other AIs, offers to the human."""
    rng = game.rng
    for o_id, rel in list(p.relations.items()):
        o = game.players[o_id]
        if not o.alive:
            continue
        att = attitude(game, p.id, o_id)
        if o.is_human:
            if any(pr["from"] == p.id for pr in game.proposals):
                continue
            if rel == "war" and will_accept_peace(game, p.id, o_id)[0] and rng.random() < 0.15:
                game.proposals.append({"from": p.id, "kind": "peace"})
            elif rel == "peace" and will_accept_pact(game, p.id, o_id)[0] and att >= 45 and rng.random() < 0.05:
                game.proposals.append({"from": p.id, "kind": "pact"})
            elif rel != "war" and att > 5 and rng.random() < 0.06:
                mine = tradeable_techs(game, p.id, o_id)
                theirs = tradeable_techs(game, o_id, p.id)
                if mine and theirs:
                    get = theirs[0]
                    give = min(mine, key=lambda t: abs(game.tech_cost(o_id, t) - game.tech_cost(p.id, get)))
                    if will_swap(game, p.id, o_id, give, get)[0]:
                        game.proposals.append({"from": p.id, "kind": "swap", "give": give, "get": get})
            continue
        # AI <-> AI
        if rel != "war" and att > 10 and rng.random() < 0.08:
            mine = tradeable_techs(game, p.id, o_id)
            theirs = tradeable_techs(game, o_id, p.id)
            if mine and theirs:
                give, get = mine[-1], theirs[0]
                if will_swap(game, p.id, o_id, give, get)[0] and will_swap(game, o_id, p.id, get, give)[0]:
                    swap_techs(game, p.id, o_id, give, get)
        if rel == "peace" and rng.random() < 0.05 and will_accept_pact(game, p.id, o_id)[0] \
                and will_accept_pact(game, o_id, p.id)[0]:
            form_pact(game, p.id, o_id)


def resolve_proposal(game, proposal, accept):
    """The human answers an AI offer."""
    ai_id = proposal["from"]
    human = game.human_id
    kind = proposal["kind"]
    if proposal in game.proposals:
        game.proposals.remove(proposal)
    if not accept:
        adjust(game, ai_id, human, -3, "rejected our proposal")
        return
    if kind == "peace":
        game.make_peace(ai_id, human)
    elif kind == "pact":
        form_pact(game, ai_id, human)
    elif kind == "swap":
        if proposal["give"] not in game.players[human].techs and proposal["get"] in game.players[human].techs:
            swap_techs(game, ai_id, human, proposal["give"], proposal["get"])


def describe_proposal(game, proposal):
    p = game.players[proposal["from"]]
    leader_name = p.faction.leader
    kind = proposal["kind"]
    if kind == "peace":
        return f"{leader_name} of the {p.name} offers to end the war between us."
    if kind == "pact":
        return (f"{leader_name} of the {p.name} proposes a pact: we share our maps and stand together "
                f"if either of us is attacked.")
    give, get = TECHS[proposal["give"]].name, TECHS[proposal["get"]].name
    return f"{leader_name} of the {p.name} offers to trade their {give} for our {get}."
