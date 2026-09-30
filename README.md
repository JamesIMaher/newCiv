# New Civilization

A turn-based 4X strategy game in the spirit of *Sid Meier's Alpha Centauri*, written in Python with pygame.
Seven human factions make planetfall on an alien world covered in xenofungus and native life. You expand, terraform,
research, and fight your way to victory.

This is the **base game**. It's meant to be extended: better cultural and economic victories, and a longer game that
keeps going after the "launch a ship" moment.

## Running

```bash
pip install -r requirements.txt
python main.py
```

Tests and a headless balancing simulator:

```bash
pip install pytest
python -m pytest -q
python tools/simulate.py --seed 3 --turns 300 --ai 4   # all-AI game, prints progress
```

## What's in the base game

| System | Summary |
| --- | --- |
| **Planet** | Isometric diamond map in the Alpha Centauri style (hill-shaded rust soils, magenta xenofungus, teal seas; wraps east–west) with elevation, rainfall (arid/moist/rainy), rockiness (flat/rolling/rocky), ocean shelf, xenofungus, resource specials and supply pods. Three map sizes. Animated seas, drifting cloud shadows, snow-capped mountains, beaches, and a rotating planet on the title screen. |
| **Factions** | 7 original factions with bonuses and AI personalities: Concordant Assembly, Helix Institute, Verdant Covenant, Iron Directorate, Meridian Consortium, Luminous Order, Tidewater Collective. |
| **Bases** | Population, nutrients/growth, minerals/production, energy. Citizens are auto-assigned to the 21-tile radius by a governor focus (balanced/growth/production/energy). Drones and riots, population caps, unit support costs, inefficiency by distance from HQ, rush-buying, energy stockpiling. |
| **Economy** | Energy is split between Economy / Psych / Labs sliders. Facilities have upkeep. Early "planetary restrictions" cap tile yields at 2 until the right techs. |
| **Technology** | 33 techs across 5 eras (Landfall → Transcendence). Cost rises with techs known and drops if contacted factions already know the tech. |
| **Units** | 14 unit types: colony pods, formers, land/sea military, transports (with boarding/unloading). Morale levels, HP, fortification, terrain defense, stack-kill outside bases, base capture. Land units board transports at sea or in port (O). |
| **Terraforming** | Farms, mines, solar collectors, roads, forests, fungus removal. Formers can be automated. |
| **Native life** | Xenoworms spawn from fungus. Fights with them use psi combat, which ignores weapons and armor. |
| **Diplomacy** | Peace, war and pacts (shared maps, allies join wars). Factions have attitudes towards each other with remembered reasons (wars, broken pacts, captured bases, gifts, trades, shared enemies, border friction). Tech trading and buying, gifts, and AI offers to the player. |
| **Society** | Social engineering in four categories (Politics, Economics, Values, Future Society), 16 models shifting 11 social factors. Each faction champions one ideology and opposes another, which colours diplomacy. |
| **Secret projects** | 8 world wonders, including the Ascension Engine. |
| **Victory** | Conquest or Transcendence (research *Transcendence* and complete the *Ascension Engine*). Victory conditions are pluggable (`game/victory.py`). |
| **Learning the world** | Datalinks encyclopedia (F6) covering rules, resources, terrain, units, facilities, projects, techs and factions. Tooltips on most things; resources shown as leaf/crystal/bolt icons with names. The base screen explains what each option would do *in that base*. Discovery pop-ups include flavour quotes. |
| **UI** | Scrollable/zoomable map with fog of war and territory borders, minimap, unit panel, base screen, research, energy/base list, diplomacy, status, help. Go-to path preview (hold Shift or right mouse). Save/load (quicksave + autosave every 10 turns). |

## Controls

| Action | Keys / mouse |
| --- | --- |
| Select unit / open base | Left-click |
| Go to | Right-click a tile (or `G`, then click). Hold `Shift` to preview the path |
| Move / attack | Arrow keys or numpad; `Home`/`PgUp`/`End`/`PgDn` for diagonals |
| Pan / zoom | Drag the map, mouse wheel, `+`/`-`, click the minimap |
| Unit orders | `B` found base · `H` fortify · `L` sentry · `Space` skip · `W` wait · `E` explore · `C` centre · `Tab` next unit · `Del` disband |
| Former orders | `F` farm · `M` mine · `S` solar · `R` road · `N` forest · `X` remove fungus · `A` automate |
| Screens | `F1` help · `F2` energy & bases · `F3` research · `F4` diplomacy · `F5` status · `F6` Datalinks encyclopedia · `F7` society · `Esc` menu |
| Turn / files | `Enter` end turn · `Ctrl+S` quicksave · `Ctrl+L` quickload |

## Code layout

```
main.py            entry point
Screen/screen.py   pygame display setup
game/              rules engine; no pygame, fully testable headless
  data.py          techs, units, facilities, projects, factions (pure data - rebalance here)
  lore.py          world text: descriptions, advice, flavour quotes, faction histories, rules guide
  world.py         map, tiles, procedural generation
  entities.py      Player, Base, Unit
  game.py          the rules: yields, growth, production, movement, combat, research, turn processing
  ai.py            computer players, native life, and automation for human units
  ai_military.py   AI war planning: strike forces, sieges, naval invasions
  diplomacy.py     attitudes & memory, pacts, trades, AI offers, victory-race awareness
  society.py       social engineering models, factors and faction ideologies
  pathfinding.py   A* / flood fill on the wrapped map
  victory.py       pluggable victory conditions
ui/                pygame front-end (app loop, map renderer, dialogs, widgets; describe.py builds tooltips/info text)
tests/             pytest suite for the rules engine
tools/simulate.py  headless all-AI games for balancing
```

## Roadmap: where we go next

See [docs/DESIGN.md](docs/DESIGN.md) for the design direction:

- **Economic Hegemony** victory: market share, a planetary currency bloc, and corporate buyouts.
- **Ideological Ascendancy** victory: influence pressure, ideology adoption, and legacy works.
- **Game phases past the stars:** the planet awakens as an actor, then orbital/star-system map layers, then deeper
  eras and a multi-milestone Transcendence.
- **Smarter AI** (first pass done): war planning, massed strike forces and sieges, naval invasions, pacts/trades/grudges, and ganging up on a runaway leader.
