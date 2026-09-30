"""Static game definitions: technologies, units, facilities, secret projects and factions.

Everything in here is plain data so it is easy to rebalance or extend. The rules
engine (game.game) looks these tables up by id.
"""
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Technologies
# ---------------------------------------------------------------------------

ERAS = ["Landfall", "Colonization", "Expansion", "Planetary", "Transcendence"]


@dataclass(frozen=True)
class Tech:
    id: str
    name: str
    era: int
    category: str  # explore / discover / build / conquer
    prereqs: tuple = ()
    description: str = ""


TECH_LIST = [
    # Era 0 - Landfall
    Tech("biogenetics", "Biogenetics", 0, "discover", (), "Adapting Earth crops to alien soil."),
    Tech("industrial_base", "Industrial Base", 0, "build", (), "Basic fabrication from local ores."),
    Tech("information_networks", "Information Networks", 0, "discover", (), "Colony-wide data sharing."),
    Tech("social_psych", "Social Psych", 0, "build", (), "Keeping colonists sane far from home."),
    Tech("applied_physics", "Applied Physics", 0, "conquer", (), "Directed energy weapons."),
    Tech("centauri_ecology", "Xenoecology", 0, "explore", (), "Understanding the native biosphere."),
    # Era 1 - Colonization
    Tech("doctrine_mobility", "Doctrine: Mobility", 1, "conquer", ("applied_physics",), "Fast wheeled chassis."),
    Tech("ethical_calculus", "Ethical Calculus", 1, "build", ("social_psych", "biogenetics"), "Designing better communities."),
    Tech("industrial_economics", "Industrial Economics", 1, "build", ("industrial_base", "information_networks"), "Markets for a new world."),
    Tech("doctrine_flexibility", "Doctrine: Flexibility", 1, "explore", ("doctrine_mobility", "centauri_ecology"), "Hydrofoil sea craft."),
    Tech("high_energy_chem", "High Energy Chemistry", 1, "conquer", ("applied_physics", "industrial_base"), "Particle weapons."),
    Tech("gene_splicing", "Gene Splicing", 1, "discover", ("biogenetics", "centauri_ecology"), "Lifts the nutrient restriction on tiles."),
    Tech("planetary_networks", "Planetary Networks", 1, "discover", ("information_networks", "social_psych"), "A datalinked society."),
    # Era 2 - Expansion
    Tech("industrial_automation", "Industrial Automation", 2, "build", ("industrial_economics",), "Robotic industry."),
    Tech("environmental_economics", "Environmental Economics", 2, "build", ("industrial_economics", "centauri_ecology"), "Lifts the energy restriction on tiles."),
    Tech("ecological_engineering", "Ecological Engineering", 2, "explore", ("gene_splicing", "environmental_economics"), "Lifts the mineral restriction; fungus yields energy."),
    Tech("silksteel_alloys", "Silksteel Alloys", 2, "conquer", ("high_energy_chem", "industrial_automation"), "Plasma armor."),
    Tech("doctrine_initiative", "Doctrine: Initiative", 2, "conquer", ("doctrine_flexibility", "industrial_automation"), "Blue-water navy."),
    Tech("retroviral_engineering", "Retroviral Engineering", 2, "discover", ("gene_splicing", "ethical_calculus"), "Rewriting the human genome."),
    Tech("optical_computers", "Optical Computers", 2, "discover", ("planetary_networks", "high_energy_chem"), "Light-speed computing."),
    Tech("planetary_economics", "Planetary Economics", 2, "build", ("environmental_economics", "planetary_networks"), "A single planetary market."),
    # Era 3 - Planetary
    Tech("superconductor", "Superconductor", 3, "conquer", ("optical_computers", "silksteel_alloys"), "Guided missiles."),
    Tech("centauri_psi", "Xenopsychology", 3, "explore", ("ecological_engineering", "ethical_calculus"), "Communion with the native psi field; fungus yields nutrients."),
    Tech("fusion_power", "Fusion Power", 3, "build", ("superconductor", "industrial_automation"), "Clean, abundant energy."),
    Tech("digital_sentience", "Digital Sentience", 3, "discover", ("optical_computers", "retroviral_engineering"), "Thinking machines."),
    Tech("quantum_power", "Quantum Power", 3, "build", ("fusion_power",), "Quantum-scale industry."),
    Tech("climate_control", "Climate Control", 3, "explore", ("ecological_engineering", "fusion_power"), "Weather on demand."),
    # Era 4 - Transcendence
    Tech("graviton_theory", "Graviton Theory", 4, "conquer", ("quantum_power", "superconductor"), "Gravity manipulation."),
    Tech("matter_transmission", "Matter Transmission", 4, "discover", ("graviton_theory", "digital_sentience"), "Teleportation of matter."),
    Tech("homo_superior", "Homo Superior", 4, "discover", ("digital_sentience", "centauri_psi"), "The next step for humanity."),
    Tech("planetary_mind", "Planetary Consciousness", 4, "explore", ("homo_superior", "climate_control"), "The planet itself is awake. Fungus yields minerals."),
    Tech("transcendence", "Transcendence", 4, "discover", ("planetary_mind", "matter_transmission"), "Unlocks the Ascension Engine."),
]

TECHS = {t.id: t for t in TECH_LIST}


# ---------------------------------------------------------------------------
# Terraforming
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TerraformDef:
    id: str
    name: str
    key: str        # keyboard shortcut
    turns: int
    prereq: str = None


TERRAFORMS = {
    "farm": TerraformDef("farm", "Farm", "f", 4),
    "mine": TerraformDef("mine", "Mine", "m", 6),
    "solar": TerraformDef("solar", "Solar Collector", "s", 4),
    "road": TerraformDef("road", "Road", "r", 2),
    "forest": TerraformDef("forest", "Plant Forest", "n", 4, "centauri_ecology"),
    "remove_fungus": TerraformDef("remove_fungus", "Remove Fungus", "x", 6, "centauri_ecology"),
}


# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class UnitType:
    id: str
    name: str
    cost: int
    attack: int
    defense: int
    moves: int
    domain: str = "land"          # land / sea
    prereq: str = None
    symbol: str = "?"
    colony: bool = False
    former: bool = False
    capacity: int = 0             # transport capacity
    native: bool = False
    obsolete_by: str = None

    @property
    def military(self):
        return self.attack > 0 or (self.defense > 1 and not self.colony and not self.former)


UNIT_LIST = [
    UnitType("scout", "Scout Patrol", 10, 1, 1, 1, symbol="S", obsolete_by="laser_squad"),
    UnitType("colony_pod", "Colony Pod", 30, 0, 1, 1, symbol="C", colony=True),
    UnitType("former", "Former", 30, 0, 1, 1, symbol="F", former=True),
    UnitType("laser_squad", "Laser Squad", 20, 2, 1, 1, prereq="applied_physics", symbol="L", obsolete_by="impact_rover"),
    UnitType("synth_garrison", "Synthmetal Garrison", 20, 1, 2, 1, prereq="industrial_base", symbol="G", obsolete_by="plasma_garrison"),
    UnitType("speeder", "Laser Speeder", 30, 2, 1, 2, prereq="doctrine_mobility", symbol="R", obsolete_by="impact_rover"),
    UnitType("transport", "Transport Foil", 40, 0, 1, 4, domain="sea", prereq="doctrine_flexibility", symbol="T", capacity=4),
    UnitType("gun_foil", "Gun Foil", 30, 2, 1, 4, domain="sea", prereq="doctrine_flexibility", symbol="N", obsolete_by="cruiser"),
    UnitType("impact_rover", "Impact Rover", 40, 4, 1, 2, prereq="high_energy_chem", symbol="I", obsolete_by="missile_rover"),
    UnitType("plasma_garrison", "Plasma Garrison", 30, 1, 3, 1, prereq="silksteel_alloys", symbol="P", obsolete_by="fusion_garrison"),
    UnitType("cruiser", "Plasma Cruiser", 60, 4, 3, 5, domain="sea", prereq="doctrine_initiative", symbol="W"),
    UnitType("missile_rover", "Missile Rover", 60, 6, 2, 2, prereq="superconductor", symbol="M", obsolete_by="grav_tank"),
    UnitType("fusion_garrison", "Fusion Garrison", 50, 2, 6, 1, prereq="fusion_power", symbol="D"),
    UnitType("grav_tank", "Grav Tank", 100, 10, 5, 3, prereq="graviton_theory", symbol="X"),
    # Native life - never buildable.
    UnitType("xenoworm", "Xenoworm Boil", 999, 3, 2, 1, symbol="~", native=True, prereq="__never__"),
]

UNITS = {u.id: u for u in UNIT_LIST}


# ---------------------------------------------------------------------------
# Base facilities
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Facility:
    id: str
    name: str
    cost: int
    upkeep: int
    prereq: str = None
    description: str = ""
    # Effects - interpreted by the rules engine
    econ_pct: int = 0
    labs_pct: int = 0
    minerals_pct: int = 0
    psych_pct: int = 0
    drones: int = 0          # negative = removes drones
    defense_pct: int = 0
    pop_cap: int = 0         # raises population cap to this value
    tile_bonus: int = 0      # +N to each of nutrient/mineral/energy on base tile


FACILITY_LIST = [
    Facility("recycling_tanks", "Recycling Tanks", 30, 0, None, "+1 nutrient, mineral and energy at the base.", tile_bonus=1),
    Facility("perimeter_defense", "Perimeter Defense", 30, 0, None, "+100% defense for units in the base.", defense_pct=100),
    Facility("rec_commons", "Recreation Commons", 40, 1, "social_psych", "Two drones become content.", drones=-2),
    Facility("network_node", "Network Node", 50, 1, "information_networks", "+50% research.", labs_pct=50),
    Facility("childrens_creche", "Children's Creche", 50, 1, "ethical_calculus", "+50% psych, one drone becomes content.", psych_pct=50, drones=-1),
    Facility("energy_bank", "Energy Bank", 60, 1, "industrial_economics", "+50% economy.", econ_pct=50),
    Facility("hab_complex", "Hab Complex", 80, 2, "industrial_automation", "Raises the population limit from 7 to 14.", pop_cap=14),
    Facility("hologram_theatre", "Hologram Theatre", 60, 2, "planetary_networks", "+50% psych, two drones become content.", psych_pct=50, drones=-2),
    Facility("research_hospital", "Research Hospital", 100, 2, "gene_splicing", "+50% research.", labs_pct=50),
    Facility("tree_farm", "Tree Farm", 80, 2, "environmental_economics", "+50% economy.", econ_pct=50),
    Facility("genejack_factory", "Genejack Factory", 100, 2, "retroviral_engineering", "+50% minerals, but adds a drone.", minerals_pct=50, drones=1),
    Facility("fusion_lab", "Fusion Lab", 120, 3, "fusion_power", "+50% economy and research.", econ_pct=50, labs_pct=50),
    Facility("quantum_converter", "Quantum Converter", 120, 3, "quantum_power", "+50% minerals.", minerals_pct=50),
    Facility("hab_dome", "Habitation Dome", 160, 4, "homo_superior", "Removes the population limit.", pop_cap=99),
]

FACILITIES = {f.id: f for f in FACILITY_LIST}


# ---------------------------------------------------------------------------
# Secret projects (one per world)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Project:
    id: str
    name: str
    cost: int
    prereq: str
    description: str


PROJECT_LIST = [
    Project("engineering_corps", "Engineering Corps", 200, "industrial_automation", "Your formers terraform twice as fast."),
    Project("genome_archive", "Genome Archive", 250, "retroviral_engineering", "One drone becomes content in every base."),
    Project("orbital_survey", "Orbital Survey", 200, "optical_computers", "Reveals the entire planet."),
    Project("planetary_exchange", "Planetary Exchange", 300, "planetary_economics", "+25% economy in every base."),
    Project("empath_council", "Empath Council", 300, "centauri_psi", "+50% psi combat strength against native life."),
    Project("cyber_sanctum", "Cyber Sanctum", 400, "digital_sentience", "+25% research in every base."),
    Project("weather_array", "Weather Control Array", 400, "climate_control", "+1 nutrient on every farm."),
    Project("ascension_engine", "Ascension Engine", 1200, "transcendence", "Humanity transcends. Completing it wins the game."),
]

PROJECTS = {p.id: p for p in PROJECT_LIST}


# ---------------------------------------------------------------------------
# Factions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Faction:
    id: str
    name: str
    leader: str
    adjective: str
    color: tuple
    description: str
    bonuses: dict = field(default_factory=dict)
    # AI personality, 0..1
    aggression: float = 0.5
    expansion: float = 0.5
    science: float = 0.5
    base_names: tuple = ()


FACTION_LIST = [
    Faction(
        "concord", "Concordant Assembly", "Chair Imani Okafor", "Concordant", (70, 130, 230),
        "Democratic idealists. +1 content citizen in every base, +1 population limit.",
        {"content": 1, "pop_cap": 1},
        aggression=0.2, expansion=0.6, science=0.5,
        base_names=("Accord", "Harmony Point", "Assembly Hall", "Covenant Bay", "New Geneva", "Unity Rise",
                    "Charter Hill", "Ballot Springs", "Tribune", "Consensus", "Delegate's Rest", "Forum Ridge",
                    "Liberty Shelf", "Senate Mesa", "Votive", "Commonwealth"),
    ),
    Faction(
        "helix", "Helix Institute", "Provost Aldric Venn", "Helix", (235, 235, 245),
        "Researchers above all. +25% research, but -1 content citizen.",
        {"labs_pct": 25, "content": -1},
        aggression=0.3, expansion=0.5, science=0.9,
        base_names=("Axiom", "Theorem Station", "Lemma", "Proof Ridge", "Hypothesis", "Datum",
                    "Catalyst", "Quantum Reach", "Isotope", "Parallax", "Vector", "Tensor",
                    "Entropy", "Postulate", "Gradient", "Fermi's Rest"),
    ),
    Faction(
        "verdant", "Verdant Covenant", "Warden Sela Moraine", "Verdant", (70, 190, 90),
        "Guardians of the native ecology. +1 nutrient and energy on fungus, +50% psi strength, -10% economy.",
        {"fungus_bonus": 1, "psi_pct": 50, "econ_pct": -10},
        aggression=0.3, expansion=0.5, science=0.6,
        base_names=("Rootfast", "Mossgate", "Canopy", "Seedbank", "Greenhold", "Fernwater",
                    "Sporefall", "Thicket", "Bloomrest", "Mycelium", "Lichen Hollow", "Grovewatch",
                    "Tendril", "Wildspring", "Heartwood", "Pollen Reach"),
    ),
    Faction(
        "iron", "Iron Directorate", "Marshal Viktor Crane", "Directorate", (210, 60, 50),
        "Discipline and strength. +25% attack, units in bases police an extra drone, -10% research.",
        {"attack_pct": 25, "police": 1, "labs_pct": -10},
        aggression=0.85, expansion=0.6, science=0.3,
        base_names=("Bastion", "Command Post", "Ironhold", "Redoubt", "Rampart", "Garrison Hill",
                    "Anvil", "Citadel", "Vanguard", "Bulwark", "Palisade", "Stronghold",
                    "Muster Field", "Warden's Gate", "Foundry", "Barricade"),
    ),
    Faction(
        "meridian", "Meridian Consortium", "CEO Lucia Marchetti", "Meridian", (235, 200, 60),
        "Profit is progress. +1 energy at every base tile, +25% economy, -1 content citizen.",
        {"base_energy": 1, "econ_pct": 25, "content": -1},
        aggression=0.4, expansion=0.7, science=0.5,
        base_names=("Dividend", "Exchange", "Tradewind", "Ledger", "Venture", "Capital Rise",
                    "Mint", "Commerce Bay", "Futures", "Arbitrage", "Equity", "Bullion",
                    "Merchant's Row", "Portfolio", "Margin", "Bourse"),
    ),
    Faction(
        "luminous", "Luminous Order", "Prophet Ezra Hale", "Luminous", (170, 90, 210),
        "The faithful endure. +25% defense, +25% psi strength, -20% research.",
        {"defense_pct": 25, "psi_pct": 25, "labs_pct": -20},
        aggression=0.6, expansion=0.6, science=0.2,
        base_names=("Sanctuary", "Revelation", "Pilgrim's Rest", "Halo", "Devotion", "Lantern",
                    "Cathedral Rock", "Vigil", "Psalm", "Epiphany", "Grace", "Radiance",
                    "Chorus", "Hallowed Ground", "Beacon", "Testament"),
    ),
    Faction(
        "tidewater", "Tidewater Collective", "Navigator Kaito Reyes", "Tidewater", (60, 200, 200),
        "Children of the sea. +1 nutrient on ocean tiles, sea units +1 move.",
        {"ocean_nutrient": 1, "sea_moves": 1},
        aggression=0.4, expansion=0.6, science=0.5,
        base_names=("Driftport", "Coral Deep", "Tidehold", "Saltwind", "Harbor Light", "Brine",
                    "Kelpfield", "Lagoon", "Undertow", "Riptide", "Seafoam", "Anchorage",
                    "Moonwater", "Shoal", "Current", "Mariner's End"),
    ),
]

FACTIONS = {f.id: f for f in FACTION_LIST}

NATIVE_COLOR = (200, 80, 150)
