# New Civilization: Design Direction

This file records design decisions for the game beyond the base Alpha Centauri-style game. It's a living document:
update it when a decision changes.

## Pillars

1. **Every victory type is a real strategy.** Economic and cultural wins must be as reachable as conquest. Each must
   also be *contestable*: rivals can see you coming and push back without only declaring war.
2. **Reaching the stars is a turning point, not the ending.** Launch/Transcendence-era tech opens new phases with new
   rules, maps and victory tracks.
3. **The AI plays the whole game.** Computer factions pursue every victory type, and they defend against yours.

---

## Economic victory: "Economic Hegemony"

Three chosen mechanics feed a single victory track.

| Mechanic | Role |
| --- | --- |
| **Market dominance** | *The metric.* Trade routes and markets between bases (yours and foreign) create planetary GDP. Your **market share** is your faction's plus your bloc members' share of planetary GDP. |
| **Planetary currency** | *The bloc.* Once your economy is big enough you can issue a reserve currency. Factions that take your loans or join your trade bloc count toward your market share. Their debt gives you leverage, and they can default or leave. |
| **Corporate buyout** | *The finisher.* You can buy out foreign bases with credits, and eventually whole factions. The price rises with the target's size, happiness, defenders, and your relations with them. Rivals can raise the price with economic defences such as tariffs, nationalisation, or leaving the bloc. |

**Win condition (draft):** your bloc holds at least 60% of planetary GDP for 20 consecutive turns. The status
screen shows this progress to everyone, so rivals can react.

**Counter-play:** tariffs and embargoes, leaving a bloc, defaulting on loans, sabotage by probe teams, and war.

## Cultural victory: "Ideological Ascendancy"

| Mechanic | Role |
| --- | --- |
| **Ideology adoption** | *The goal.* Factions choose ideologies/values through social engineering (see below). Your ideology spreads when other factions adopt your choices. |
| **Influence pressure** | *The engine.* Bases radiate influence from population, facilities and works. Sustained pressure flips border tiles, creates unrest in foreign bases, and eventually makes bases defect peacefully. |
| **Legacy works** | *The fuel.* Great works, achievements and secret projects generate legacy points. Legacy powers influence and breaks ties. |

**Win condition (draft):** a majority of the surviving factions (including yours) share your ideology, and you have the
highest legacy, both held for 20 turns.

**Counter-play:** counter-ideologies, psych/police investment to resist defection, cultural isolation (with
research/trade penalties), and destroying works.

**Dependency:** needs a **social engineering** system (government, economics, values, future society) with trade-offs.
It also gives the economic track levers, such as a free-market economy that boosts trade but costs psych.

## Past the stars: game phases

The game moves through phases instead of ending at a launch. Each phase adds rules and victory tracks. Earlier
tracks remain available.

| Phase | Trigger | What changes |
| --- | --- | --- |
| **1. Planetfall** | Game start | The current base game. |
| **2. Planetary** | Mid-game tech | Trade, blocs and influence switch on fully. The planet's psi field starts to stir. |
| **3. Awakening** | Planetary Consciousness *or* a high level of ecological damage | **The planet becomes an actor.** A planet-mind with its own agenda responds to terraforming and pollution with fungal blooms, worm surges and climate shifts. Factions choose to *commune* (bonuses and obligations) or *resist* (tech to suppress it). A new victory track: become the planet's chosen steward, or subdue it. |
| **4. Orbital / System** | Orbital launch tech (replaces "launch a ship = win") | **New map layers:** orbit (satellites, stations), moons, an asteroid belt for mining, and other planets to settle and fight over. Existing victory tracks extend to the whole system. |
| **5. Deeper eras** | Continued research | Post-scarcity, digital minds, transhumanism. **Transcendence becomes a multi-milestone track** (several projects or achievements spread across phases) instead of one wonder. |

Existing Transcendence victory → becomes the final milestone of a longer track in phase 5.

## AI roadmap (next build target)

- **Naval invasions:** load transports, escort them, land beside targets, and establish beachheads.
- **Coordinated attacks:** group units into task forces with siege targets, and gather before striking instead of
  trickling in one at a time.
- **Diplomacy:** tech and credit trades, pacts and alliances, and a memory of grudges and favours (broken treaties,
  shared enemies, border pressure). Personalities shape all of this.
- **Victory awareness:** each AI chooses a victory strategy that fits its personality and situation, tracks rivals'
  progress, and acts to stop a leader (for example, embargo the economic leader or counter-propagandise the cultural
  leader).

## Proposed build order

1. Smarter AI: military (naval invasions, task forces), then diplomacy (trades, pacts, memory).
2. Social engineering (prerequisite for the cultural track, and it adds economic levers).
3. Economic track: trade routes → markets/GDP → currency bloc → buyouts → victory + AI use.
4. Cultural track: influence → legacy works → ideology adoption → victory + AI use.
5. Phase system + the planet awakens.
6. Orbital/system map layers.
7. Deeper eras and the multi-milestone Transcendence track.
