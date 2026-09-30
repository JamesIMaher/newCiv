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
| **Planet** | Procedural cylinder map (wraps east–west) with elevation, rainfall (arid/moist/rainy), rockiness (flat/rolling/rocky), ocean shelf, xenofungus, resource specials and supply pods. Three map sizes. |
| **Factions** | 7 original factions with bonuses and AI personalities: Concordant Assembly, Helix Institute, Verdant Covenant, Iron Directorate, Meridian Consortium, Luminous Order, Tidewater Collective. |
| **Bases** | Population, nutrients/growth, minerals/production, energy. Citizens are auto-assigned to the 21-tile radius by a governor focus (balanced/growth/production/energy). Drones and riots, population caps, unit support costs, inefficiency by distance from HQ, rush-buying, energy stockpiling. |
| **Economy** | Energy is split between Economy / Psych / Labs sliders. Facilities have upkeep. Early "planetary restrictions" cap tile yields at 2 until the right techs. |
| **Technology** | 33 techs across 5 eras (Landfall → Transcendence). Cost rises with techs known and drops if contacted factions already know the tech. |
| **Units** | 14 unit types: colony pods, formers, land/sea military, transports (with boarding/unloading). Morale levels, HP, fortification, terrain defense, stack-kill outside bases, base capture. |
| **Terraforming** | Farms, mines, solar collectors, roads, forests, fungus removal. Formers can be automated. |
| **Native life** | Xenoworms spawn from fungus. Fights with them use psi combat, which ignores weapons and armor. |
| **Diplomacy** | Contact, peace, and war. AI factions declare war based on aggression and relative strength, and consider peace offers. |
| **Secret projects** | 8 world wonders, including the Ascension Engine. |
| **Victory** | Conquest or Transcendence (research *Transcendence* and complete the *Ascension Engine*). Victory conditions are pluggable (`game/victory.py`). |
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
| Screens | `F1` help · `F2` energy & bases · `F3` research · `F4` diplomacy · `F5` status · `Esc` menu |
| Turn / files | `Enter` end turn · `Ctrl+S` quicksave · `Ctrl+L` quickload |

## Code layout

```
main.py            entry point
Screen/screen.py   pygame display setup
game/              rules engine; no pygame, fully testable headless
  data.py          techs, units, facilities, projects, factions (pure data - rebalance here)
  world.py         map, tiles, procedural generation
  entities.py      Player, Base, Unit
  game.py          the rules: yields, growth, production, movement, combat, research, turn processing
  ai.py            computer players, native life, and automation for human units
  pathfinding.py   A* / flood fill on the wrapped map
  victory.py       pluggable victory conditions
ui/                pygame front-end (app loop, map renderer, dialogs, widgets)
tests/             pytest suite for the rules engine
tools/simulate.py  headless all-AI games for balancing
```

## Roadmap: where we go next

The base game is intentionally close to the classics. The planned divergences:

1. **Viable cultural and economic victories.** Right now only Conquest and Transcendence exist.
2. **A game that doesn't end at the "space" moment.** The tech tree, projects and victories should continue past
   Transcendence-era technology into later eras.
