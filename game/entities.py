"""Mutable game objects: players (factions in play), bases and units."""
from .data import FACTIONS, UNITS, NATIVE_COLOR

MOVE_POINTS = 3      # movement points per "move"; roads cost 1, open terrain 3
MAX_HP = 10
MORALE_NAMES = ["Green", "Disciplined", "Hardened", "Veteran", "Commando", "Elite"]
NATIVE_ID = 0


class Player:
    def __init__(self, pid, faction_id, is_human, width, height):
        self.id = pid
        self.faction_id = faction_id
        self.is_human = is_human
        self.alive = True
        self.credits = 60
        self.research_progress = 0
        self.current_tech = None
        self.techs = set()
        # Energy allocation in tenths: economy / psych / labs.
        self.alloc = [4, 1, 5]
        self.explored = bytearray(width * height)
        self.visible = bytearray(width * height)
        self.relations = {}     # pid -> "peace" / "war"
        self.war_turns = {}     # pid -> turn war was declared
        self.hq_base = None
        self.base_name_index = 0
        self.ai_state = {}

    @property
    def faction(self):
        return FACTIONS.get(self.faction_id)

    @property
    def name(self):
        return self.faction.name if self.faction else "Planet"

    @property
    def color(self):
        return self.faction.color if self.faction else NATIVE_COLOR

    @property
    def is_native(self):
        return self.id == NATIVE_ID

    def bonus(self, key, default=0):
        if not self.faction:
            return default
        return self.faction.bonuses.get(key, default)

    def at_war(self, other_id):
        if other_id == NATIVE_ID or self.id == NATIVE_ID:
            return True
        return self.relations.get(other_id) == "war"

    def has_contact(self, other_id):
        return other_id in self.relations


class Base:
    def __init__(self, bid, name, owner, x, y, turn):
        self.id = bid
        self.name = name
        self.owner = owner
        self.x = x
        self.y = y
        self.pop = 1
        self.nutrients = 0
        self.minerals = 0
        self.production = ("unit", "scout")
        self.facilities = set()
        self.focus = "balanced"   # balanced / growth / production / energy
        self.founded = turn
        self.worked = []          # (x, y) tiles worked by citizens
        self.specialists = 0
        self.rioting = False
        self.last_report = {}     # cached yields for display
        self.queue = []           # production items after the current one


class Unit:
    def __init__(self, uid, type_id, owner, x, y, home=None):
        self.id = uid
        self.type_id = type_id
        self.owner = owner
        self.x = x
        self.y = y
        self.home = home
        self.hp = MAX_HP
        self.morale = 1
        self.moves_left = self.type.moves * MOVE_POINTS
        self.orders = None        # None / fortify / sentry / goto / explore / auto / terraform
        self.fortified = False
        self.path = []
        self.goal = None
        self.ai_goal = None       # AI/automation target tile
        self.terraform = None     # (kind, turns_left)
        self.carried_by = None
        self.cargo = []
        self.age = 0

    @property
    def type(self):
        return UNITS[self.type_id]

    @property
    def name(self):
        return self.type.name

    @property
    def morale_name(self):
        return MORALE_NAMES[max(0, min(len(MORALE_NAMES) - 1, self.morale))]
