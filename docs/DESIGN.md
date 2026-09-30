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
| **Corporate buyout** | *The finisher.* You buy individual **bases**, not factions. See "Buyouts" below for how this works against human players. |

### Buyouts: how they work against a human

A buyout can never knock a player out of the game. Buying a whole faction would be an instant loss for a human,
and no human would ever accept that at any price. So:

- **Buyouts target single bases, and the base's citizens decide, not the owner.** You make an offer to a foreign
  base. Whether it accepts depends on its unhappiness (drones, riots), its distance from the owner's headquarters,
  how dependent it is on your trade, and the price.
- **The owner always gets a chance to respond.** A human is told "Meridian is courting the citizens of Tidehold",
  with a few turns to react: pay a loyalty bonus, raise psych, station police, or cut trade ties. Buyouts become a
  pressure game over neglected edge bases, not a surprise loss.
- **Protected bases:** a faction's headquarters, and any base founded in its first N turns (its core), can never
  be bought. A faction always keeps a playable core.
- **Mergers (AI only):** an AI faction deep in your bloc (heavily indebted, trade-dependent, friendly) can agree to
  merge into you peacefully. Humans are never offered or subjected to a merger.
- Humans can buy AI bases under the same rules, and AI factions use buyouts against humans (only on
  non-protected bases).

Buyouts are a way to grow and to punish neglect. The economic *win* is still market share (below).

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
| **3. Awakening** | Planetary Consciousness, *or* enough accumulated ecological damage | **The planet becomes an actor**, and the world gets harder: climate change, fungal blooms, worm surges, and the fallout of nuclear war. It never ends the game for everyone. See "The Awakening" below. |
| **4. Orbital / System** | Orbital launch tech (replaces "launch a ship = win") | **New map layers:** orbit (satellites, stations), moons, an asteroid belt for mining, and other planets to settle and fight over. Existing victory tracks extend to the whole system. |
| **5. Deeper eras** | Continued research | Post-scarcity, digital minds, transhumanism. **Transcendence becomes a multi-milestone track** (several projects or achievements spread across phases) instead of one wonder. |

### The Awakening: harder, never hopeless

There is no shared-loss condition. The planet makes the world harder to live in, and factions must adapt:

- **Climate change:** industry (minerals), fungus clearing and pollution raise a planet-wide *climate stress*
  meter. As it rises: sea levels climb and flood low coastal tiles (and eventually low coastal bases, which must be
  protected or abandoned); rainfall belts shift, so farmland dries out and deserts get wetter; storms damage
  improvements. It can be slowed or reversed with forests, clean energy techs, climate projects, and treaties
  between factions.
- **The planet's reaction:** fungal blooms and worm surges target the worst polluters. Factions that commune with
  the planet gain psi bonuses and calmer native life, but take on obligations (limits on mining and clearing).
  Factions that resist research tech to suppress the planet and pay in stronger backlash.
- **Survivable nuclear war:** late-game weapons can devastate a base or region: population and units lost,
  fallout tiles that yield little until Formers clean them, and a *nuclear winter* that cools the planet
  (lower nutrients everywhere for a while). Every use is an atrocity: diplomatic penalties with everyone and
  possible council sanctions. Enough use pushes climate stress sharply. The world is scarred, but players can
  recover and keep playing.
- **Recovery is part of the game:** cleanup projects, formers restoring land, and cooperation between factions
  create late-game goals that are not war.

Existing Transcendence victory → becomes the final milestone of a longer track in phase 5.

## Pacing

- **Target length:** 400–500 turns on a standard map, and a game speed option later on.
- **Fast opening (done):** *Planetfall* rules. For the first 40 turns every base gets +1 nutrient and +1
  mineral from landing supplies. Colony Pods cost 20, small bases grow quickly, early techs are cheaper, and you
  start with 60 credits for rush-buying. In all-AI tests this roughly halved the time to expand: the 3rd base
  comes around turn 11 instead of 22, and the 6th around turn 25 instead of 42.
- **Longer middle and late game:** growth gets steeper for large bases (already in). Research pacing and the
  phase system will spread the game over 400–500 turns as that content arrives. It is not stretched yet, because
  there's no new content to fill the time.

## AI roadmap (first pass implemented)

- **Naval invasions:** load transports, escort them, land beside targets, and establish beachheads.
- **Coordinated attacks:** group units into task forces with siege targets, and gather before striking instead of
  trickling in one at a time.
- **Diplomacy:** tech and credit trades, pacts and alliances, and a memory of grudges and favours (broken treaties,
  shared enemies, border pressure). Personalities shape all of this.
- **Victory awareness:** each AI chooses a victory strategy that fits its personality and situation, tracks rivals'
  progress, and acts to stop a leader (for example, embargo the economic leader or counter-propagandise the cultural
  leader).

## Proposed build order

1. ~~Smarter AI: military (naval invasions, task forces), then diplomacy (trades, pacts, memory).~~ First pass done:
   `game/ai_military.py` (war plans, gathering, sieges, naval landings) and `game/diplomacy.py` (attitude, memory,
   pacts, trades, offers to the player, victory-race awareness).
2. Social engineering (prerequisite for the cultural track, and it adds economic levers).
3. Economic track: trade routes → markets/GDP → currency bloc → buyouts → victory + AI use.
4. Cultural track: influence → legacy works → ideology adoption → victory + AI use.
5. Phase system + the planet awakens.
6. Orbital/system map layers.
7. Deeper eras and the multi-milestone Transcendence track.
