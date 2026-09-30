"""Social engineering: how a faction governs itself.

A faction picks one model in each of four categories. Each model shifts a set of social
factors (economy, efficiency, growth, ...) up or down; the rules engine reads the totals.
Factions also have an ideology they favour and one they oppose, which colours how they feel
about others (and will drive the cultural victory later).
"""
from dataclasses import dataclass, field

from .data import TECHS

# Social factors and what one point of each does (shown to the player).
FACTORS = {
    "economy": ("Economy", "+10% energy credits per point."),
    "efficiency": ("Efficiency", "Less energy lost to distance from headquarters (25% per point)."),
    "support": ("Support", "Each base supports one more unit free of charge per point."),
    "content": ("Content", "One more naturally content citizen per base per point."),
    "morale": ("Morale", "+10% attack and defense strength per point."),
    "police": ("Police", "Each base can use one more military unit as police per point."),
    "growth": ("Growth", "Bases need 10% fewer nutrients to grow per point."),
    "planet": ("Planet", "+15% psi strength against native life per point; the planet tolerates you better."),
    "industry": ("Industry", "+10% mineral production per point."),
    "research": ("Research", "+10% research per point."),
    "influence": ("Influence", "Cultural pull on other factions' citizens (used by the coming cultural victory)."),
}

CATEGORIES = [("politics", "Politics"), ("economics", "Economics"), ("values", "Values"), ("future", "Future Society")]


@dataclass(frozen=True)
class Model:
    id: str
    name: str
    category: str
    prereq: str = None
    effects: dict = field(default_factory=dict)
    text: str = ""
    quote: tuple = None


MODEL_LIST = [
    # Politics
    Model("frontier", "Frontier", "politics", None, {},
          "The improvised rule of the landing: whoever is competent takes charge. No strengths, no weaknesses."),
    Model("police_state", "Police State", "politics", "doctrine_mobility",
          {"police": 2, "support": 2, "efficiency": -2, "influence": -1},
          "Order through surveillance and force. Armies are cheap to keep and riots are easy to put down, but "
          "the bureaucracy is corrupt and wasteful.",
          ("\"Freedom is a luxury for colonies that have already survived.\"", "Marshal Viktor Crane")),
    Model("democratic", "Democratic", "politics", "ethical_calculus",
          {"efficiency": 2, "growth": 2, "support": -2, "influence": 1},
          "Government by elected councils. Honest, efficient administration and thriving families, but voters "
          "resent paying for large armies.",
          ("\"The colony is not a ship any more. Nobody has to follow the captain.\"", "Chair Imani Okafor")),
    Model("fundamentalist", "Fundamentalist", "politics", "social_psych",
          {"morale": 1, "content": 1, "research": -2, "influence": 1},
          "One faith, one purpose. Soldiers fight with conviction and citizens accept hardship, but awkward "
          "questions are discouraged.",
          ("\"Doubt is a door, and the dark things of this world are waiting on the other side.\"",
           "Prophet Ezra Hale")),
    # Economics
    Model("simple", "Simple", "economics", None, {},
          "Barter, rationing and handshake deals. No strengths, no weaknesses."),
    Model("free_market", "Free Market", "economics", "industrial_economics",
          {"economy": 2, "planet": -2, "police": -2},
          "Let the markets decide. Energy flows, but industry strips the land and nobody wants soldiers "
          "patrolling the shopping arcades.",
          ("\"Every credit is a vote, and the market is always in session.\"", "CEO Lucia Marchetti")),
    Model("planned", "Planned", "economics", "industrial_automation",
          {"growth": 2, "industry": 1, "efficiency": -2},
          "Central planners set quotas for every base. Populations and factories grow, at the price of "
          "paperwork and waste.",
          ("\"The five-year plan has become a fifty-year plan. It is still on schedule.\"", "Foundry Log")),
    Model("green", "Green", "economics", "environmental_economics",
          {"efficiency": 2, "planet": 2, "growth": -2},
          "Live within the planet's limits. Clean, efficient and at peace with the native life, but growth "
          "is deliberately slow.",
          ("\"We are guests here. Guests do not rearrange the furniture.\"", "Warden Sela Moraine")),
    # Values
    Model("survival", "Survival", "values", None, {},
          "Stay alive. The only value that mattered during planetfall. No strengths, no weaknesses."),
    Model("power", "Power", "values", "doctrine_initiative",
          {"morale": 2, "support": 2, "industry": -2, "influence": -1},
          "Strength above all. The military is honoured and well supplied, and the civilian economy pays "
          "for it.",
          ("\"History is written by the side with more rovers.\"", "Directorate Staff College")),
    Model("knowledge", "Knowledge", "values", "planetary_networks",
          {"research": 2, "efficiency": 1, "content": -1, "influence": 1},
          "Learning is the highest good. Laboratories flourish, and the citizens left out of the lecture halls "
          "grumble.",
          ("\"We crossed four light-years to ask better questions.\"", "Provost Aldric Venn")),
    Model("wealth", "Wealth", "values", "planetary_economics",
          {"economy": 1, "industry": 1, "morale": -2},
          "Prosperity for all, or at least for the investors. Business booms, and soldiers ask what exactly "
          "they are fighting for.",
          ("\"A rising tide lifts all hovercraft.\"", "Navigator Kaito Reyes")),
    # Future society
    Model("none", "None", "future", None, {},
          "The future has not arrived yet."),
    Model("cybernetic", "Cybernetic", "future", "digital_sentience",
          {"efficiency": 2, "planet": 2, "research": 2, "police": -3},
          "Human and machine minds governing together. Superbly efficient and wise, but no one can order the "
          "network to crack skulls.",
          ("\"The council has 40,000 members. Most of them are not human.\"", "Digital Sentience lab notes")),
    Model("eudaimonic", "Eudaimonic", "future", "homo_superior",
          {"growth": 2, "economy": 2, "content": 2, "morale": -2, "influence": 2},
          "A society organised around every citizen's flourishing. Happy, rich and growing, and very reluctant "
          "to go to war.",
          ("\"We solved scarcity. Now we are working on boredom.\"", "Chair Imani Okafor")),
    Model("thought_control", "Thought Control", "future", "planetary_mind",
          {"police": 2, "morale": 2, "content": 1, "support": -3, "influence": -2},
          "The planet's psi field, harnessed to shape minds. Utterly loyal citizens and fearless soldiers, but "
          "vast armies are hard to feed.",
          ("\"Everyone agrees with me now. It is very restful.\"", "Unknown")),
]

MODELS = {m.id: m for m in MODEL_LIST}
DEFAULTS = {"politics": "frontier", "economics": "simple", "values": "survival", "future": "none"}

# Each faction's ideology: the model it champions and the one it opposes.
IDEOLOGY = {
    "concord": ("democratic", "police_state"),
    "helix": ("knowledge", "fundamentalist"),
    "verdant": ("green", "free_market"),
    "iron": ("police_state", "democratic"),
    "meridian": ("free_market", "planned"),
    "luminous": ("fundamentalist", "knowledge"),
    "tidewater": ("wealth", "power"),
}


def available(game, pid, model_id):
    m = MODELS[model_id]
    return m.prereq is None or m.prereq in game.players[pid].techs


def factors(game_or_none, player):
    """Total social factors for a player: chosen models plus faction traits."""
    out = {k: 0 for k in FACTORS}
    for cat, mid in player.social.items():
        for k, v in MODELS[mid].effects.items():
            out[k] += v
    for k, v in (player.faction.bonuses.get("social", {}) if player.faction else {}).items():
        out[k] += v
    return out


def switch_cost(game, pid, changes):
    """Credits needed to reorganise society: the upheaval scales with the number of bases."""
    n = sum(1 for cat, mid in changes.items() if game.players[pid].social.get(cat) != mid)
    if n == 0:
        return 0
    bases = len(game.player_bases(pid))
    return n * (10 + 4 * bases)


def apply(game, pid, changes, free=False):
    p = game.players[pid]
    cost = 0 if free else switch_cost(game, pid, changes)
    if cost > p.credits:
        return False
    p.credits -= cost
    for cat, mid in changes.items():
        if available(game, pid, mid) and MODELS[mid].category == cat:
            p.social[cat] = mid
    names = ", ".join(MODELS[m].name for m in p.social.values() if m not in DEFAULTS.values())
    game.notify(None if not p.is_human else pid,
                f"The {p.name} reorganises its society: {names or 'back to basics'}.")
    return True


def ideology_opinion(observer, other):
    """How much observer's ideology approves (+) or disapproves (-) of other's society."""
    fav, opp = IDEOLOGY.get(observer.faction_id, (None, None))
    chosen = set(other.social.values())
    return (1 if fav in chosen else 0) - (1 if opp in chosen else 0)


# ---------------------------------------------------------------------------
# AI choice
# ---------------------------------------------------------------------------
def _weights(game, p):
    f = p.faction
    war = any(r == "war" for r in p.relations.values())
    riot = any(b.rioting for b in game.player_bases(p.id))
    w = {"economy": 1.0, "efficiency": 0.8, "support": 0.4, "content": 0.8, "morale": 0.4, "police": 0.3,
         "growth": 1.0, "planet": 0.3, "industry": 1.0, "research": 1.0, "influence": 0.3}
    if f:
        w["research"] += f.science
        w["morale"] += f.aggression
        w["support"] += f.aggression * 0.6
        w["growth"] += f.expansion * 0.5
    if war or p.ai_state.get("plan"):
        w["morale"] += 1.0
        w["support"] += 0.8
    if riot:
        w["content"] += 1.5
        w["police"] += 1.0
    if len(game.player_bases(p.id)) > 10:
        w["efficiency"] += 0.6
    return w


def ai_choose(game, p):
    """Pick the best available model per category (with a bias for the faction's own ideology)."""
    w = _weights(game, p)
    fav, opp = IDEOLOGY.get(p.faction_id, (None, None))
    best = {}
    for cat, _ in CATEGORIES:
        options = [m for m in MODEL_LIST if m.category == cat and available(game, p.id, m.id)]

        def score(m):
            s = sum(w[k] * v for k, v in m.effects.items())
            if m.id == fav:
                s += 2.0
            if m.id == opp:
                s -= 3.0
            if m.id == p.social.get(cat):
                s += 0.8  # inertia: changing costs money
            return s

        best[cat] = max(options, key=score).id
    changes = {c: m for c, m in best.items() if p.social.get(c) != m}
    if changes and switch_cost(game, p.id, changes) <= p.credits * 0.6:
        apply(game, p.id, changes)
