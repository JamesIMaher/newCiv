"""Builds player-facing descriptions from game data + lore (shared by several screens)."""
from game import lore
from game.data import UNITS, FACILITIES, PROJECTS, TECHS, TERRAFORMS, ERAS
from game.world import ARID, MOIST, RAINY, FLAT, ROLLING, ROCKY


def tile_description(tile):
    """Short paragraphs explaining a tile, most specific first."""
    parts = []
    if tile.fungus:
        parts.append(lore.TERRAIN["fungus"][1])
    if tile.is_ocean:
        parts.append(lore.TERRAIN["shelf" if tile.is_shelf else "deep_ocean"][1])
    else:
        if "forest" in tile.improvements:
            parts.append(lore.TERRAIN["forest"][1])
        rain = {ARID: "arid", MOIST: "moist", RAINY: "rainy"}[tile.rainfall]
        rock = {FLAT: "flat", ROLLING: "rolling", ROCKY: "rocky"}[tile.rockiness]
        parts.append(lore.TERRAIN[rain][1])
        parts.append(lore.TERRAIN[rock][1])
    if tile.special:
        parts.append(lore.SPECIALS[tile.special][1])
    if tile.supply_pod:
        parts.append(lore.SPECIALS["supply_pod"][1])
    return parts


def improvement_names(tile):
    return [lore.IMPROVEMENTS[i][0] for i in sorted(tile.improvements) if i in lore.IMPROVEMENTS]


def best_use_hint(tile):
    if tile.is_ocean:
        return "Best use: work it from a coastal base for nutrients and energy."
    if tile.fungus:
        return "Best use: clear it with a Former (Remove Fungus) or wait for fungus technologies."
    if tile.rockiness == ROCKY:
        return "Best use: build a mine."
    if tile.rainfall == ARID:
        return "Best use: a solar collector, or plant a forest."
    if tile.rockiness == ROLLING:
        return "Best use: a farm and solar collector for growth, or a mine for production."
    return "Best use: a farm, then a solar collector."


def unit_summary(ut):
    dom = "sea" if ut.domain == "sea" else "land"
    return f"Attack {ut.attack}  Defense {ut.defense}  Moves {ut.moves} ({dom})  Cost {ut.cost}"


def unit_tooltip(ut):
    info = lore.UNITS.get(ut.id, {})
    s = f"{ut.name} - {info.get('role', '')}\n{unit_summary(ut)}\n{info.get('text', '')}"
    return s


def item_info(game, base, item):
    """Rich info for a production item. Returns dict with title, kind, stats, body, pros, cons, here, quote."""
    kind, iid = item
    out = {"title": game.item_name(item), "kind": kind, "stats": "", "body": "", "pros": [], "cons": [],
           "here": "", "quote": None}
    rep = base.last_report or game.base_report(base)
    if kind == "unit":
        ut = UNITS[iid]
        info = lore.UNITS.get(iid, {})
        out["kind"] = f"Unit - {info.get('role', '')}"
        out["stats"] = unit_summary(ut)
        out["body"] = info.get("text", "")
        out["pros"] = info.get("pros", [])
        out["cons"] = info.get("cons", [])
        out["quote"] = info.get("quote")
        supported = sum(1 for u in game.units.values() if u.home == base.id)
        if supported >= 2:
            out["here"] = f"This base already supports {supported} units. Another costs 1 mineral per turn."
        else:
            out["here"] = "This base can support it free of charge."
        if ut.colony and base.pop <= 1:
            out["here"] = "This base must grow to size 2 before it can complete a Colony Pod."
    elif kind == "facility":
        f = FACILITIES[iid]
        desc, advice, quote = lore.FACILITIES.get(iid, ("", "", None))
        out["kind"] = "Base facility"
        out["stats"] = f"Cost {f.cost}   Upkeep {f.upkeep} credit{'s' if f.upkeep != 1 else ''}/turn"
        out["body"] = f"{desc} {f.description}"
        out["pros"] = [advice] if advice else []
        out["quote"] = quote
        out["here"] = facility_effect_here(game, base, f, rep)
    elif kind == "project":
        pr = PROJECTS[iid]
        desc, quote = lore.PROJECTS.get(iid, ("", None))
        out["kind"] = "Secret project (one per world)"
        out["stats"] = f"Cost {pr.cost}   No upkeep"
        out["body"] = f"{desc}\nEffect: {pr.description}"
        out["pros"] = ["Only one faction can ever build it. If a rival finishes first, your minerals move to "
                       "something else."]
        out["quote"] = quote
    else:
        out["kind"] = "Special"
        out["body"] = ("Builds nothing. Instead, the base's mineral output is converted into energy credits every "
                       "turn. Useful when a base has nothing worthwhile left to build.")
        out["here"] = f"Here: about +{rep['minerals_net']} credits per turn."
    return out


def facility_effect_here(game, base, f, rep):
    bits = []
    if f.labs_pct:
        bits.append(f"+{rep['labs'] * f.labs_pct // 100} research")
    if f.econ_pct:
        bits.append(f"+{rep['econ'] * f.econ_pct // 100} credits")
    if f.minerals_pct:
        bits.append(f"+{rep['minerals_net'] * f.minerals_pct // 100} minerals")
    if f.tile_bonus:
        bits.append(f"+{f.tile_bonus} nutrient, mineral and energy")
    if f.drones < 0:
        calm = min(-f.drones, rep["drones"])
        bits.append(f"calms {calm} of {rep['drones']} current drone(s)" if rep["drones"] else "no drones to calm yet")
    if f.drones > 0:
        bits.append(f"+{f.drones} drone")
    if f.psych_pct:
        bits.append(f"+{rep['psych'] * f.psych_pct // 100} psych")
    if f.pop_cap:
        if base.pop >= rep["pop_cap"] - 1:
            bits.append(f"lets this base grow past {rep['pop_cap']} (it's nearly at the limit)")
        else:
            bits.append(f"population limit {rep['pop_cap']} -> {f.pop_cap} (size now {base.pop})")
    if f.defense_pct:
        bits.append("doubles the defense of units here")
    if not bits:
        return ""
    return "In this base: " + ", ".join(bits) + "."


def tech_unlocks(tech_id):
    out = []
    out += [("Unit", u.name) for u in UNITS.values() if u.prereq == tech_id]
    out += [("Facility", f.name) for f in FACILITIES.values() if f.prereq == tech_id]
    out += [("Project", p.name) for p in PROJECTS.values() if p.prereq == tech_id]
    out += [("Terraform", t.name) for t in TERRAFORMS.values() if t.prereq == tech_id]
    extra = {
        "gene_splicing": "Tiles can yield more than 2 nutrients",
        "ecological_engineering": "Tiles can yield more than 2 minerals; fungus gives +1 energy",
        "environmental_economics": "Tiles can yield more than 2 energy; forests give +1 energy",
        "centauri_psi": "Fungus gives +1 nutrient",
        "planetary_mind": "Fungus gives +1 mineral and +1 energy",
    }
    if tech_id in extra:
        out.append(("Effect", extra[tech_id]))
    return out


def tech_text(tech_id):
    t = TECHS[tech_id]
    quote = lore.TECH_QUOTES.get(tech_id)
    return {"name": t.name, "era": ERAS[t.era], "category": t.category, "description": t.description,
            "unlocks": tech_unlocks(tech_id), "quote": quote,
            "prereqs": [TECHS[p].name for p in t.prereqs]}
