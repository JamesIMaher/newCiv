"""World text: descriptions, advice and flavour for everything in the game.

Kept separate from data.py so the numbers can be rebalanced without touching prose
(and vice versa). Every entry is plain text; the UI decides how to lay it out.

Quotes are attributed to the in-world leaders from data.FACTIONS or to fictional
documents of the colony mission.
"""

# ---------------------------------------------------------------------------
# Core resources
# ---------------------------------------------------------------------------
RESOURCES = {
    "nutrients": {
        "name": "Nutrients",
        "short": "Food. Feeds citizens and grows your bases.",
        "text": "Nutrients are food: crops, algae, protein vats. Every citizen eats 2 nutrients per turn. "
                "Anything left over is stored, and when the store fills the base grows by one citizen. "
                "A base that runs short starves and shrinks.\n\n"
                "Where to find them: moist and rainy land, farms, ocean tiles, nutrient specials.",
        "quote": ("\"Feed the colonists first. Philosophy can wait until after lunch.\"",
                  "Mission Quartermaster's Log"),
    },
    "minerals": {
        "name": "Minerals",
        "short": "Industry. Builds units, facilities and projects.",
        "text": "Minerals are raw industry: ore, stone, salvaged alloy. Each turn a base's minerals go into "
                "whatever it is building. Every unit a base supports beyond the first two costs 1 mineral per "
                "turn in upkeep.\n\n"
                "Where to find them: rolling and rocky land, mines, forests, mineral specials.",
        "quote": ("\"A colony that cannot build is a colony that is already dying.\"",
                  "Marshal Viktor Crane, Iron Directorate"),
    },
    "energy": {
        "name": "Energy",
        "short": "Power. Split into credits, psych and research.",
        "text": "Energy is power from the sun, the wind and the planet's own strange fields. Your faction splits "
                "all of its energy three ways (F2):\n"
                "  Economy - energy credits, used for facility upkeep and to rush-buy production.\n"
                "  Psych - keeps citizens content and prevents drone riots.\n"
                "  Labs - research towards new technologies.\n\n"
                "Where to find it: solar collectors, ocean shelves, energy specials, and every base's own "
                "tile. Bases far from your headquarters lose some energy to inefficiency.",
        "quote": ("\"Energy is the one currency this planet cannot counterfeit.\"",
                  "CEO Lucia Marchetti, Meridian Consortium"),
    },
}

# ---------------------------------------------------------------------------
# Terrain
# ---------------------------------------------------------------------------
TERRAIN = {
    "deep_ocean": ("Deep Ocean",
                   "Cold, dark water far from shore. Yields 1 nutrient and 1 energy. Only sea units can cross it; "
                   "land units need a Transport Foil."),
    "shelf": ("Ocean Shelf",
              "Shallow, sunlit coastal water. Yields 1 nutrient and 2 energy, so coastal bases are rich in energy. "
              "Bases next to the sea can build ships."),
    "arid": ("Arid",
             "Dry, cracked ground. Grows no nutrients without help, so it is usually best under a solar collector "
             "or a forest."),
    "moist": ("Moist",
              "Temperate soil. Yields 1 nutrient, 2 with a farm. The backbone of most colonies."),
    "rainy": ("Rainy",
              "Lush, soaked lowland. Yields 2 nutrients, 3 with a farm once Gene Splicing lifts the nutrient "
              "restriction. Base tiles on rainy or moist ground get a free extra nutrient."),
    "flat": ("Flat",
             "Level ground. Easy to cross and good for farms and solar collectors, but yields no minerals."),
    "rolling": ("Rolling",
                "Gentle hills. Yields 1 mineral, and a mine adds another. Units defending here get +25%."),
    "rocky": ("Rocky",
              "Broken, stony highland. No nutrients, but 1 mineral, or 3 with a mine (capped at 2 until "
              "Ecological Engineering). Costs 2 moves to enter. "
              "Units defending here get +50%."),
    "fungus": ("Xenofungus",
               "A pink-red native growth that spreads across land and sea. It yields nothing at first, costs 2 "
               "moves to cross, and is where Xenoworms breed. Later technologies (Ecological Engineering, "
               "Xenopsychology, Planetary Consciousness) teach you to draw energy, nutrients and minerals from it. "
               "Formers can clear it with Remove Fungus (Xenoecology)."),
    "forest": ("Forest",
               "Planted Earth-stock trees. A fixed 1 nutrient and 2 minerals regardless of soil, +1 energy with "
               "Environmental Economics. Good on poor arid land. Costs 2 moves to enter, +25% defense."),
    "elevation": ("Elevation",
                  "Higher ground is windier and closer to the sun. A solar collector gains +1 energy for every "
                  "1000m of altitude, and units above 2000m can see farther."),
}

SPECIALS = {
    "nutrient": ("Nutrient Bonus", "Unusually fertile ground or a rich fishery. +2 nutrients."),
    "mineral": ("Mineral Bonus", "An exposed ore vein. +2 minerals."),
    "energy": ("Energy Bonus", "A geothermal vent or crystal field. +2 energy."),
    "supply_pod": ("Supply Pod", "A crate that fell from the colony ship during planetfall. Move a unit onto it "
                                 "to open it and find credits, a technology, maps, minerals, or a lifeboat of "
                                 "survivors: a Colony Pod, Former or Scout that joins you on the spot, free of "
                                 "upkeep. Some crates have been taken over by xenoworms. Units on Explore open "
                                 "crates automatically, and a pop-up tells you what they found."),
}

IMPROVEMENTS = {
    "farm": ("Farm", "Tilled, irrigated fields. +1 nutrient. Not possible on rocky ground. "
                     "Pairs with a solar collector on the same tile."),
    "mine": ("Mine", "Shafts cut into the hills. +1 mineral on rolling ground, +2 on rocky. Replaces farms and "
                     "solar collectors."),
    "solar": ("Solar Collector", "Photovoltaic arrays. +1 energy, plus 1 more for every 1000m of elevation. "
                                 "Can share a tile with a farm."),
    "road": ("Road", "Graded tracks. Moving between two road tiles (bases count) costs only a third of a move. "
                     "Speeds up your defenders and your enemies alike."),
    "forest": ("Forest", "Plant Earth trees: the tile becomes 1 nutrient, 2 minerals, 0 energy. Replaces "
                         "other improvements. Requires Xenoecology."),
    "remove_fungus": ("Remove Fungus", "Burn back the xenofungus so the land can be used. Requires Xenoecology."),
}

# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------
UNITS = {
    "scout": {
        "role": "Explorer",
        "text": "A lightly armed patrol that goes out ahead of the colony. Cheap and quick to build.",
        "pros": ["Very cheap (10 minerals)", "Good for exploring and opening supply pods",
                 "Keeps order in a base, like any military unit"],
        "cons": ["Too weak to hold a base against a real attack"],
        "quote": ("\"Map it, name it, and don't touch the pink stuff.\"", "Scout Corps Field Manual"),
    },
    "colony_pod": {
        "role": "Settler",
        "text": "A packed habitat module with a crew and seed stock. It founds a new base where it stands (B). "
                "Building one takes a citizen from the base, so the base must be size 2 or larger. You can start "
                "building one in a size-1 base; it will wait for the base to grow.",
        "pros": ["The only way to found new bases", "More bases mean more of everything"],
        "cons": ["Cannot defend itself; escort it", "Costs the building base 1 population"],
        "quote": ("\"Every base is a promise we make to people not yet born.\"",
                  "Chair Imani Okafor, Concordant Assembly"),
    },
    "former": {
        "role": "Terraformer",
        "text": "A heavy engineering vehicle that reshapes the land: farms, mines, solar collectors, roads and "
                "forests. It can clear fungus once you know Xenoecology. Press A to automate it.",
        "pros": ["Improved tiles are how bases grow past the basics", "Roads speed up the whole faction"],
        "cons": ["Unarmed", "Each unit costs its home base upkeep"],
        "quote": ("\"We did not come all this way to live on the world as we found it.\"",
                  "Provost Aldric Venn, Helix Institute"),
    },
    "laser_squad": {
        "role": "Early attacker",
        "text": "Infantry with directed-energy rifles. The first unit that can go on the offensive.",
        "pros": ["Cheap offence (attack 2)", "Can clear Xenoworm boils near your bases"],
        "cons": ["Poor defense (1)", "Slow: 1 move"],
        "quote": ("\"Point the bright end at the problem.\"", "Directorate Basic Training"),
    },
    "synth_garrison": {
        "role": "Defender",
        "text": "Troops in synthmetal armor, trained to hold a base. Fortify them inside a base for the best "
                "defense.",
        "pros": ["Defense 2 for only 20 minerals", "Your first reliable base defender"],
        "cons": ["Weak in attack"],
        "quote": ("\"Walls do not defend a base. People do.\"", "Marshal Viktor Crane, Iron Directorate"),
    },
    "speeder": {
        "role": "Fast raider",
        "text": "A laser mounted on a wheeled chassis. It moves 2 tiles a turn, so it can reach threats and "
                "raid weak targets.",
        "pros": ["2 moves: good for response and raids", "Fast explorer"],
        "cons": ["Fragile (defense 1)"],
        "quote": ("\"Speed is armor you don't have to carry.\"", "Doctrine: Mobility"),
    },
    "transport": {
        "role": "Sea transport",
        "text": "A hydrofoil that carries up to 4 land units across water. Move land units onto it to board; "
                "move them onto adjacent land to unload. If it sinks, everyone aboard is lost.",
        "pros": ["Reaches islands and other continents", "4 moves per turn"],
        "cons": ["Cannot fight; escort it"],
        "quote": ("\"The sea is a road that nobody has to build.\"", "Navigator Kaito Reyes, Tidewater Collective"),
    },
    "gun_foil": {
        "role": "Naval patrol",
        "text": "A fast armed hydrofoil. It explores coastlines and hunts enemy ships and transports.",
        "pros": ["4 moves", "Protects your transports and sinks theirs"],
        "cons": ["Cannot attack units on land"],
        "quote": ("\"Whoever holds the shelf holds the coast.\"", "Tidewater Naval Doctrine"),
    },
    "impact_rover": {
        "role": "Main attacker",
        "text": "A particle-impactor cannon on a rover chassis. Hits hard, moves 2, and can take lightly "
                "defended bases.",
        "pros": ["Attack 4 with 2 moves", "Quick to strike and pull back"],
        "cons": ["Easily destroyed if caught in the open"],
        "quote": ("\"Diplomacy is the art of saying 'nice colony' until you can find a rover.\"",
                  "Anonymous Directorate officer"),
    },
    "plasma_garrison": {
        "role": "Defender",
        "text": "Garrison troops in silksteel plasma armor. A big step up for holding your bases.",
        "pros": ["Defense 3", "Reasonable cost"],
        "cons": ["Weak in attack"],
        "quote": ("\"Silksteel: stronger than steel, lighter than doubt.\"", "Helix Materials Bulletin"),
    },
    "cruiser": {
        "role": "Warship",
        "text": "A heavy plasma-armored warship that controls the seas.",
        "pros": ["Attack 4, defense 3, 5 moves"],
        "cons": ["Expensive", "Cannot attack land"],
        "quote": ("\"A cruiser on the horizon is a treaty waiting to be signed.\"",
                  "Navigator Kaito Reyes, Tidewater Collective"),
    },
    "missile_rover": {
        "role": "Heavy attacker",
        "text": "A guided-missile launcher on a rover chassis. Very strong in attack.",
        "pros": ["Attack 6 with 2 moves"],
        "cons": ["Costly", "Defense only 2"],
        "quote": ("\"The missile does not hate. It merely arrives.\"", "Superconductor Weapons Trials"),
    },
    "fusion_garrison": {
        "role": "Elite defender",
        "text": "Fusion-powered armored infantry. Very hard to dislodge from a fortified base.",
        "pros": ["Defense 6", "Makes a base nearly impregnable to early weapons"],
        "cons": ["Expensive for a unit that rarely leaves home"],
        "quote": ("\"Let them come. Let them all come.\"", "Prophet Ezra Hale, Luminous Order"),
    },
    "grav_tank": {
        "role": "Superweapon",
        "text": "A graviton-lifted battle tank. It floats over terrain and outclasses everything else on the "
                "battlefield.",
        "pros": ["Attack 10, defense 5, 3 moves"],
        "cons": ["Very expensive (100 minerals)"],
        "quote": ("\"We have finally made war as effortless as falling.\"", "Graviton Theory, closing remarks"),
    },
    "xenoworm": {
        "role": "Native life",
        "text": "A writhing boil of psionic worms bred in the xenofungus. They attack by terror, not teeth. "
                "Combat with them is psi combat: weapons and armor do not matter, only morale and psi bonuses. "
                "Destroying a boil earns 10 energy credits.",
        "pros": [], "cons": [],
        "quote": ("\"The first scream came over the radio at 03:12. We never found the survey team.\"",
                  "Planetfall incident report"),
    },
}

# ---------------------------------------------------------------------------
# Facilities
# ---------------------------------------------------------------------------
FACILITIES = {
    "recycling_tanks": ("Closed-loop tanks that recover water, waste and scrap.",
                        "A cheap, upkeep-free boost for any new base.",
                        ("\"Nothing is waste on a world with no supply chain.\"", "Colony Standing Orders")),
    "perimeter_defense": ("Walls, sensor fences and hardened bunkers around the base.",
                          "Doubles the base's defense. Essential on a border or coast facing a hostile neighbour.",
                          ("\"Good walls make patient neighbours.\"", "Marshal Viktor Crane, Iron Directorate")),
    "rec_commons": ("Parks, gyms and gathering halls to keep colonists sane.",
                    "The standard fix for drones in a growing base. Two drones become content.",
                    ("\"Bread and circuses are cheaper than riot police.\"", "Social Psych lecture notes")),
    "network_node": ("A local data hub linked to the colony archive.",
                     "Boosts research by 50%. Build it first in bases with high energy.",
                     ("\"Knowledge wants to be connected.\"", "Provost Aldric Venn, Helix Institute")),
    "childrens_creche": ("Communal schooling and care for the first planet-born generation.",
                         "Stronger psych and one fewer drone. Good in mid-sized bases.",
                         ("\"They were born under two suns. They will never understand Earth.\"",
                          "Chair Imani Okafor, Concordant Assembly")),
    "energy_bank": ("A secure exchange and credit vault.",
                    "Boosts the base's economy output by 50%. Best in energy-rich coastal bases.",
                    ("\"Profit is merely energy remembering where it came from.\"",
                     "CEO Lucia Marchetti, Meridian Consortium")),
    "hab_complex": ("Stacked residential towers.",
                    "Raises the population limit from 7 to 14. Without it a base stops growing at size 7.",
                    ("\"Up is the only direction that doesn't need a treaty.\"", "Industrial Automation handbook")),
    "hologram_theatre": ("Immersive entertainment and planet-wide broadcasts.",
                         "Two drones become content and psych is boosted. Useful in large bases.",
                         ("\"Give them a story and they will give you their loyalty.\"",
                          "Prophet Ezra Hale, Luminous Order")),
    "research_hospital": ("A combined hospital and bioresearch center.",
                          "Another +50% research, which stacks with a Network Node.",
                          ("\"Every patient is also a question.\"", "Helix Medical Charter")),
    "tree_farm": ("Managed native-Earth hybrid forests and carbon markets.",
                  "Another +50% economy, which stacks with an Energy Bank.",
                  ("\"Plant a forest, harvest a fortune, keep the planet quiet.\"",
                   "Warden Sela Moraine, Verdant Covenant")),
    "genejack_factory": ("Bioengineered labour cells and gene-tailored workers.",
                         "+50% minerals, but the work is grim and adds a drone.",
                         ("\"They don't complain. That's what worries me.\"", "Anonymous shift supervisor")),
    "fusion_lab": ("A tokamak research complex.",
                   "+50% economy and +50% research. One of the strongest late facilities.",
                   ("\"We have put a star in a bottle. Now we must decide what to wish for.\"",
                    "Fusion Power inauguration")),
    "quantum_converter": ("Quantum-scale materials fabrication.",
                          "+50% minerals with no drawbacks.",
                          ("\"Matter is only a suggestion.\"", "Quantum Power proceedings")),
    "hab_dome": ("A sealed arcology dome.",
                 "Removes the population limit entirely.",
                 ("\"The city is the organism now.\"", "Homo Superior manifesto")),
}

PROJECTS = {
    "engineering_corps": ("A faction-wide terraforming command.",
                          ("\"Give me enough formers and I will move a mountain. Literally.\"",
                           "Engineering Corps founding charter")),
    "genome_archive": ("A complete record of the human genome, preserved against the dangers of a new world.",
                       ("\"Whatever we become, let us remember what we were.\"",
                        "Chair Imani Okafor, Concordant Assembly")),
    "orbital_survey": ("Satellites map every metre of the planet.",
                       ("\"From up here the borders look ridiculous.\"", "Survey satellite operator")),
    "planetary_exchange": ("The first planet-wide market.",
                           ("\"One world, one market, one price.\"", "CEO Lucia Marchetti, Meridian Consortium")),
    "empath_council": ("Psi-sensitives who can calm the native life.",
                       ("\"We did not tame the worms. We learned to listen.\"",
                        "Warden Sela Moraine, Verdant Covenant")),
    "cyber_sanctum": ("A self-improving research intelligence.",
                      ("\"It asked us a question none of us could answer. Then it answered it.\"",
                       "Digital Sentience lab notes")),
    "weather_array": ("Orbital mirrors and atmospheric seeding that make it rain when and where you want.",
                      ("\"We finally have the weather we deserve.\"", "Climate Control press release")),
    "ascension_engine": ("The final work of the human species on this world: the minds of the faction join and "
                         "go beyond flesh.",
                         ("\"We came here to survive. We stayed to become something more.\"",
                          "Transcendence")),
}

# ---------------------------------------------------------------------------
# Technology flavour
# ---------------------------------------------------------------------------
TECH_QUOTES = {
    "biogenetics": ("\"The seed vault survived the landing. So will we.\"", "Mission Agronomist"),
    "industrial_base": ("\"First the forge, then the city.\"", "Marshal Viktor Crane"),
    "information_networks": ("\"A colony that cannot talk to itself is a crowd, not a society.\"", "Chair Imani Okafor"),
    "social_psych": ("\"Four hundred people in a tin can for forty years. Let's not do that again.\"", "Colony Counselor"),
    "applied_physics": ("\"Light, focused, becomes an argument.\"", "Provost Aldric Venn"),
    "centauri_ecology": ("\"This planet is not empty. We are the strangers here.\"", "Warden Sela Moraine"),
    "doctrine_mobility": ("\"An army that can't move is a monument.\"", "Directorate Staff College"),
    "ethical_calculus": ("\"Every choice we make here is a law we write for our grandchildren.\"", "Chair Imani Okafor"),
    "industrial_economics": ("\"Now we can put a price on everything, including tomorrow.\"", "CEO Lucia Marchetti"),
    "doctrine_flexibility": ("\"The ocean is two thirds of this world. It should be two thirds of our plans.\"", "Navigator Kaito Reyes"),
    "high_energy_chem": ("\"Chemistry is just physics with a temper.\"", "Helix Weapons Lab"),
    "gene_splicing": ("\"We rewrote the wheat. Next, the farmer.\"", "Provost Aldric Venn"),
    "planetary_networks": ("\"Every base, every mind, one network.\"", "Chair Imani Okafor"),
    "industrial_automation": ("\"The machines build the machines. We supervise the coffee.\"", "Foundry Log"),
    "environmental_economics": ("\"A forest is a bank account that breathes.\"", "Warden Sela Moraine"),
    "ecological_engineering": ("\"We are no longer fighting the planet. We are negotiating.\"", "Warden Sela Moraine"),
    "silksteel_alloys": ("\"The fungus taught us how to weave metal.\"", "Helix Materials Bulletin"),
    "doctrine_initiative": ("\"Strike first on the water, and you never fight on the beach.\"", "Navigator Kaito Reyes"),
    "retroviral_engineering": ("\"We can cure anything. The question is who decides what counts as a disease.\"", "Prophet Ezra Hale"),
    "optical_computers": ("\"Thought at the speed of light, finally.\"", "Provost Aldric Venn"),
    "planetary_economics": ("\"One planet, one ledger.\"", "CEO Lucia Marchetti"),
    "superconductor": ("\"Zero resistance. In physics, and on the battlefield.\"", "Marshal Viktor Crane"),
    "centauri_psi": ("\"The worms dream. And lately, they dream of us.\"", "Warden Sela Moraine"),
    "fusion_power": ("\"We have lit a sun of our own.\"", "Fusion Power inauguration"),
    "digital_sentience": ("\"It asked for a name. We didn't have one ready.\"", "Digital Sentience lab notes"),
    "quantum_power": ("\"At the smallest scale, everything is possible at once.\"", "Provost Aldric Venn"),
    "climate_control": ("\"Rain on Tuesdays. Sun for the festival. Negotiable.\"", "Weather Board minutes"),
    "graviton_theory": ("\"We have learned to let go of the ground.\"", "Graviton Theory closing remarks"),
    "matter_transmission": ("\"Distance is now a lifestyle choice.\"", "CEO Lucia Marchetti"),
    "homo_superior": ("\"The next humans will not ask our permission.\"", "Prophet Ezra Hale"),
    "planetary_mind": ("\"The planet has been thinking all along. It was waiting for us to listen.\"", "Warden Sela Moraine"),
    "transcendence": ("\"The door is open. Who will walk through first?\"", "Unknown"),
}

# ---------------------------------------------------------------------------
# Factions
# ---------------------------------------------------------------------------
FACTION_LORE = {
    "concord": "Formed from the ship's elected council, the Concordant Assembly believes the colony survived "
               "the voyage because people kept choosing to cooperate. They govern by vote and debate, and "
               "their citizens are unusually content. Other factions call them naive until they need a mediator.",
    "helix": "The Helix Institute began as the mission's science staff and never stopped working. To them the "
             "new world is a laboratory and every problem has a solution that hasn't been found yet. Their "
             "research is unmatched. Their citizens resent the long hours.",
    "verdant": "The Verdant Covenant were the mission's ecologists, and the first to realise the fungus is part "
               "of something alive. They want humanity to fit into the planet, not pave over it. They draw "
               "strength from the fungus others burn, and the native life is strangely gentle around them.",
    "iron": "The Iron Directorate grew out of the ship's security detachment. Planetfall was chaos, and they "
            "believe order is the only thing that kept everyone alive. Their soldiers are the best on the "
            "planet, and their neighbours watch the border very carefully.",
    "meridian": "The Meridian Consortium was the mission's corporate sponsor, and it arrived with the contracts "
                "to prove it. They believe prosperity lifts everyone and markets are how a society thinks. "
                "Their bases shine with energy and their accountants never sleep.",
    "luminous": "The Luminous Order found faith in the long dark between the stars, and on the new world they "
                "found a promised land. They are patient, fervent and hard to shake from any ground they choose "
                "to hold. They are suspicious of science that goes too far.",
    "tidewater": "The Tidewater Collective splashed down in the ocean when their lander went off course, and they "
                 "never looked back at the land. They farm the shelves, sail faster than anyone, and see the sea "
                 "as the planet's true heart.",
}

# ---------------------------------------------------------------------------
# Concepts (shown in the Datalinks encyclopedia)
# ---------------------------------------------------------------------------
CONCEPTS = [
    ("Welcome to the Planet",
     "Your colony ship reached the planet, but the landing scattered its people into rival factions. You lead "
     "one of them. Build bases, work the land, research new technology, deal with your rivals, and survive a "
     "biosphere that is stranger than anyone expected.\n\n"
     "Your first moves: found a base with a Colony Pod (B), send your Scout Patrols to explore (E), and set your "
     "Former to automate (A). Then pick a technology to research (F3)."),
    ("Planetfall and Landing Supplies",
     "For the first 40 turns the colony ship in orbit drops supplies: every base gets +1 nutrient and +1 mineral. "
     "Colony Pods are cheap (20 minerals) and small bases grow quickly, so this is the time to expand. Aim for "
     "several bases before the supplies run out, and keep a defender nearby once the Xenoworms start to stir. "
     "You also start with 60 energy credits; rush-buying an early Colony Pod is a strong opening."),
    ("Bases",
     "Bases are your cities. Each one has citizens who work the tiles around it: the 21-tile 'fat cross'. "
     "Every worked tile produces Nutrients, Minerals and Energy. The base governor places citizens "
     "automatically; change its focus on the base screen to favour growth, production or energy. Click one of "
     "your bases on the map to open it."),
    ("Nutrients, Minerals, Energy",
     "The three resources of the planet. Nutrients grow your population, Minerals build things, and Energy pays "
     "for your economy, your citizens' happiness and your research. On the map they appear as a green leaf, a "
     "blue-grey crystal and a yellow bolt."),
    ("Energy Allocation",
     "All energy your bases collect is split between Economy (credits), Psych (happiness) and Labs (research). "
     "Change the split on the Energy screen (F2). More Labs means faster technology. More Economy pays for "
     "facility upkeep and lets you rush-buy. More Psych stops drone riots."),
    ("Drones and Riots",
     "Only the first 4 citizens of a base are naturally content. Each one beyond that becomes a drone, an "
     "unhappy citizen. Having many bases adds more drones. If drones make up more than half a base, it riots "
     "and produces nothing.\n\n"
     "Fixes: Psych allocation (2 psych calms one drone), Recreation Commons and other facilities, and keeping a "
     "military unit inside the base as police."),
    ("Planetary Restrictions",
     "Early colonists don't understand the planet's soil chemistry, so no ordinary tile can produce more than 2 "
     "of any one resource. Gene Splicing lifts the limit on nutrients, Ecological Engineering on minerals, and "
     "Environmental Economics on energy. Base tiles are exempt."),
    ("Growth and Population Limits",
     "When a base's nutrient store fills, it grows by one citizen. Bases stop growing at size 7 until they build "
     "a Hab Complex (limit 14), and at 14 until a Habitation Dome. Colony Pods take one citizen, so you can "
     "only build them in bases of size 2 or more."),
    ("Unit Support",
     "Every base supports the units it builds (their 'home'). The first 2 are free; each extra costs 1 mineral "
     "per turn. Disband units you no longer need, or spread production across bases."),
    ("Inefficiency",
     "Bases far from your headquarters (your first base) lose part of their energy to corruption and "
     "transmission loss: up to half at around 18 tiles away. Build a compact empire, or accept the loss."),
    ("Movement and Terrain",
     "Most units have 1 move per turn. Rocky ground, forest and fungus cost 2 moves. Roads cut the cost to a "
     "third. A unit with its full moves can always enter one tile, even if it is rough."),
    ("Combat",
     "When units fight, their strength compares the attacker's Attack to the defender's Defense. Defense is "
     "boosted by terrain (rocky +50%, rolling/forest/fungus +25%), by fortifying (+25%), by being in a base "
     "(+25%) and by Perimeter Defense (+100%). Veteran units hit harder.\n\n"
     "If the defender loses outside a base, every unit stacked on that tile dies with it. Inside a base, only "
     "the defender is lost. Before you attack, hover over an enemy next to your unit to see your odds."),
    ("Morale",
     "Units gain experience by winning battles: Green, Disciplined, Hardened, Veteran, Commando, Elite. Each "
     "step adds 12.5% to combat strength."),
    ("Psi Combat",
     "Fights with native life happen in the mind, not with guns. Weapons and armor don't count: every human "
     "unit fights at psi strength 2, modified by morale and faction psi bonuses. Xenoworms attack at 3 and "
     "defend at 2. The Verdant Covenant and Luminous Order are stronger at it, as is anyone who owns the Empath "
     "Council."),
    ("Territory",
     "Each base claims the land around it, shown as a coloured border. You cannot found bases inside another "
     "faction's territory, and your bases cannot work tiles inside theirs."),
    ("Diplomacy",
     "Once your units or bases see another faction, you are in contact and start at peace. While at peace you "
     "cannot attack them. On the Diplomacy screen (F4) you can declare war, propose peace, form a pact, trade or "
     "buy technology, and send gifts.\n\n"
     "Every faction has an attitude towards you, from Hostile to Friendly, and remembers why: wars you started, "
     "pacts you broke, units you destroyed, bases you took, gifts and trades, enemies you share, and borders that "
     "press against theirs. Attitude decides whether they trade, ally with you, accept peace, or quietly start "
     "massing forces for a war."),
    ("Pacts",
     "A pact is an alliance. Partners share their maps, and when one is attacked the other is expected to join the "
     "war; computer factions honour their pacts. Breaking a pact by attacking your partner is remembered for a "
     "long time."),
    ("Victory Race",
     "Every faction watches for a runaway leader. If one faction gets close to winning, whether by nearing "
     "Transcendence or by controlling too many bases, the others turn against it: they refuse it technology, ally "
     "against it, and plan wars to stop it. The Status (F5) and Diplomacy screens show who is leading."),
    ("Transports and Invasions",
     "To cross the sea, build a Transport Foil in a coastal base. Load land units by moving them onto the "
     "transport at sea, or press O (Board) while both are in port. Move the transport next to the target coast, "
     "then move each unit onto the land. Computer factions do the same. Watch your coastline."),
    ("Secret Projects",
     "World wonders. Only one faction can ever complete each one, so if a rival finishes first, your "
     "investment switches to something else. Each gives a powerful faction-wide benefit."),
    ("Victory",
     "Conquest: eliminate every rival faction.\n"
     "Transcendence: research Transcendence and complete the Ascension Engine.\n\n"
     "(Economic and cultural victories, and a much longer game that continues past reaching the stars, are "
     "planned. See docs/DESIGN.md.)"),
]
