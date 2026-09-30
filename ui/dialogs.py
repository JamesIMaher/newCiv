"""Modal windows: base screen, research, economy, diplomacy, status, help and menus."""
import pygame

from game.data import TECHS, UNITS, FACILITIES, PROJECTS, TERRAFORMS, FACTIONS, ERAS
from game.victory import VICTORY_CONDITIONS
from . import theme
from .renderer import draw_tile


def unlocks(tech_id):
    out = []
    out += [f"Unit: {u.name}" for u in UNITS.values() if u.prereq == tech_id]
    out += [f"Facility: {f.name}" for f in FACILITIES.values() if f.prereq == tech_id]
    out += [f"Project: {p.name}" for p in PROJECTS.values() if p.prereq == tech_id]
    out += [f"Terraform: {t.name}" for t in TERRAFORMS.values() if t.prereq == tech_id]
    return out


def item_description(item):
    kind, iid = item
    if kind == "unit":
        u = UNITS[iid]
        extra = ""
        if u.colony:
            extra = " Founds a new base (uses 1 population)."
        elif u.former:
            extra = " Terraforms land."
        elif u.capacity:
            extra = f" Carries {u.capacity} land units."
        return f"{u.name}: attack {u.attack}, defense {u.defense}, moves {u.moves}{' (sea)' if u.domain == 'sea' else ''}.{extra}"
    if kind == "facility":
        f = FACILITIES[iid]
        return f"{f.name}: {f.description} Upkeep {f.upkeep}."
    if kind == "project":
        p = PROJECTS[iid]
        return f"Secret project - {p.name}: {p.description}"
    return "Converts this base's minerals into energy credits each turn."


class Dialog:
    width, height = 600, 400
    title = ""

    def __init__(self, app):
        self.app = app
        self.scroll = 0

    @property
    def game(self):
        return self.app.game

    def rect(self, surf):
        sw, sh = surf.get_size()
        w = min(self.width, sw - 20)
        h = min(self.height, sh - 20)
        return pygame.Rect((sw - w) // 2, (sh - h) // 2, w, h)

    def frame(self, surf, ui):
        r = self.rect(surf)
        shadow = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 110))
        surf.blit(shadow, (0, 0))
        theme.panel(surf, r, theme.PANEL, theme.PANEL_BORDER)
        pygame.draw.rect(surf, theme.PANEL_LIGHT, (r.x + 1, r.y + 1, r.width - 2, 36), border_radius=6)
        theme.text(surf, self.title, (r.x + 14, r.y + 9), 26, theme.ACCENT, bold=True)
        ui.button(surf, (r.right - 36, r.y + 6, 28, 26), "X", self.close)
        return r

    def draw(self, surf, ui):
        self.frame(surf, ui)

    def close(self):
        self.app.close_dialog(self)

    def on_key(self, event):
        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self.close()
            return True
        return False

    def on_wheel(self, dy):
        self.scroll = max(0, self.scroll - dy)


# ---------------------------------------------------------------------------
class BaseDialog(Dialog):
    width, height = 1060, 680

    def __init__(self, app, base):
        super().__init__(app)
        self.base = base
        self.hover_item = None

    @property
    def title(self):
        b = self.base
        return f"{b.name}  -  size {b.pop}"

    def on_key(self, event):
        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self.close()
            return True
        if event.key == pygame.K_b:
            self.buy()
            return True
        return False

    def buy(self):
        self.game.buy_production(self.base)
        self.game.base_report(self.base)

    def set_focus(self, focus):
        self.base.focus = focus
        self.game.assign_workers(self.base)
        self.game.base_report(self.base)

    def set_prod(self, item):
        self.game.set_production(self.base, item)

    def draw(self, surf, ui):
        game = self.game
        b = self.base
        if b.id not in game.bases or b.owner != game.human_id:
            self.close()
            return
        r = self.frame(surf, ui)
        game.assign_workers(b)
        rep = game.base_report(b)
        p = game.players[b.owner]

        # --- Left column: resources -----------------------------------------
        x, y = r.x + 16, r.y + 50
        colw = 300
        theme.text(surf, "Resources", (x, y), 22, theme.ACCENT, bold=True)
        y += 26
        surplus = rep["nutrient_surplus"]
        grow = rep["growth_threshold"]
        if b.pop >= rep["pop_cap"]:
            gtxt = "at population limit"
        elif surplus > 0:
            gtxt = f"grows in {max(1, -(-(grow - b.nutrients) // surplus))} turns"
        elif surplus < 0:
            gtxt = "STARVING"
        else:
            gtxt = "stagnant"
        theme.text(surf, f"Nutrients  {rep['nutrients']}  ({surplus:+d})", (x, y), 20, theme.NUTRIENT)
        y += 20
        theme.bar(surf, (x, y, colw - 20, 10), b.nutrients / max(1, grow), theme.NUTRIENT)
        y += 13
        theme.text(surf, f"{b.nutrients}/{grow}, {gtxt}", (x, y), 17, theme.TEXT_DIM)
        y += 24
        theme.text(surf, f"Minerals  {rep['minerals']}  (net {rep['minerals_net']})", (x, y), 20, theme.MINERAL)
        y += 20
        theme.text(surf, f"Unit support cost: {rep['support']}", (x, y), 17, theme.TEXT_DIM)
        y += 24
        theme.text(surf, f"Energy  {rep['energy']}  (inefficiency -{rep['inefficiency']})", (x, y), 20, theme.ENERGY)
        y += 20
        theme.text(surf, f"Economy {rep['econ']}   Psych {rep['psych']}   Labs {rep['labs']}", (x, y), 17, theme.TEXT_DIM)
        y += 18
        theme.text(surf, f"Facility upkeep: {rep['upkeep']}", (x, y), 17, theme.TEXT_DIM)
        y += 26
        # Citizens
        theme.text(surf, "Citizens", (x, y), 22, theme.ACCENT, bold=True)
        y += 26
        drones = rep["drones"]
        cx = x
        for i in range(b.pop):
            is_drone = i >= b.pop - drones
            is_spec = i < b.specialists
            col = (220, 80, 70) if is_drone else (110, 200, 240) if is_spec else (120, 220, 130)
            pygame.draw.circle(surf, col, (cx + 9, y + 9), 8)
            pygame.draw.circle(surf, (0, 0, 0), (cx + 9, y + 9), 8, 1)
            cx += 20
            if cx > x + colw - 20:
                cx = x
                y += 20
        y += 24
        theme.text(surf, f"{drones} drone(s), {b.specialists} specialist(s)", (x, y), 17, theme.TEXT_DIM)
        y += 18
        if rep["rioting"]:
            theme.text(surf, "DRONE RIOT - production halted!", (x, y), 19, theme.WARN, bold=True)
            y += 18
            theme.text(surf, "Raise psych (F2) or build Rec Commons.", (x, y), 17, theme.WARN)
            y += 18
        y += 8
        theme.text(surf, f"Population limit: {rep['pop_cap']}", (x, y), 17, theme.TEXT_DIM)

        # --- Centre: base map -------------------------------------------------
        z = 46
        mx = r.x + 16 + colw + 10
        my = r.y + 52
        world = game.world
        pygame.draw.rect(surf, (0, 0, 0), (mx - 2, my - 2, 5 * z + 4, 5 * z + 4))
        worked = set(b.worked)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                tx, ty = (b.x + dx) % world.width, b.y + dy
                px, py = mx + (dx + 2) * z, my + (dy + 2) * z
                if not world.in_bounds(tx, ty) or (abs(dx) == 2 and abs(dy) == 2):
                    pygame.draw.rect(surf, (8, 8, 8), (px, py, z, z))
                    continue
                t = world.tiles[tx][ty]
                if not game.is_explored(b.owner, tx, ty):
                    pygame.draw.rect(surf, (0, 0, 0), (px, py, z, z))
                    continue
                draw_tile(surf, world, t, px, py, z, game.base_pos)
                if (tx, ty) == (b.x, b.y):
                    pygame.draw.rect(surf, p.color, (px + 8, py + 8, z - 16, z - 16), border_radius=5)
                    n, m, e = game.tile_yield(t, b.owner, True)
                    self._yields(surf, px, py, z, n, m, e)
                elif (tx, ty) in worked:
                    n, m, e = game.tile_yield(t, b.owner)
                    pygame.draw.rect(surf, (255, 255, 255), (px, py, z, z), 2)
                    self._yields(surf, px, py, z, n, m, e)
                else:
                    s = pygame.Surface((z, z), pygame.SRCALPHA)
                    s.fill((0, 0, 0, 80))
                    surf.blit(s, (px, py))
                    if t.owner is not None and t.owner != b.owner:
                        pygame.draw.line(surf, (200, 60, 60), (px + 4, py + 4), (px + z - 4, py + z - 4), 2)
        fy = my + 5 * z + 10
        theme.text(surf, "Governor focus", (mx, fy), 18, theme.TEXT_DIM)
        fy += 20
        bw = (5 * z) // 2 - 3
        for i, (key, label) in enumerate((("balanced", "Balanced"), ("growth", "Growth"),
                                           ("production", "Production"), ("energy", "Energy"))):
            bx = mx + (i % 2) * (bw + 6)
            by = fy + (i // 2) * 30
            ui.button(surf, (bx, by, bw, 26), label, lambda k=key: self.set_focus(k), selected=b.focus == key, size=18)

        # --- Right: production --------------------------------------------------
        px0 = mx + 5 * z + 20
        pw = r.right - px0 - 16
        py0 = r.y + 50
        theme.text(surf, "Production", (px0, py0), 22, theme.ACCENT, bold=True)
        py0 += 26
        item = b.production
        cost = game.item_cost(item)
        theme.text(surf, game.item_name(item), (px0, py0), 22, theme.TEXT, bold=True)
        py0 += 24
        if item[0] != "special":
            theme.bar(surf, (px0, py0, pw, 14), b.minerals / max(1, cost), theme.MINERAL)
            turns = game.turns_to_complete(b)
            theme.text(surf, f"{b.minerals}/{cost}  -  {turns if turns < 999 else '--'} turns", (px0, py0 + 16), 17, theme.TEXT_DIM)
            bc = game.buy_cost(b)
            ui.button(surf, (px0 + pw - 150, py0 + 16, 150, 24), f"Buy ({bc} cr) [B]", self.buy,
                      enabled=0 < bc <= p.credits, size=18)
        else:
            theme.text(surf, f"+{rep['minerals_net']} credits per turn", (px0, py0), 17, theme.TEXT_DIM)
        py0 += 48
        theme.text(surf, "Change production:", (px0, py0), 18, theme.TEXT_DIM)
        py0 += 20
        opts = game.production_options(b)
        list_h = r.bottom - 150 - py0
        row_h = 25
        visible = max(1, list_h // row_h)
        self.scroll = min(self.scroll, max(0, len(opts) - visible))
        self.hover_item = None
        mouse = ui.mouse
        for i, opt in enumerate(opts[self.scroll:self.scroll + visible]):
            ry = py0 + i * row_h
            rr = pygame.Rect(px0, ry, pw, row_h - 2)
            kind = opt[0]
            label = game.item_name(opt)
            c = game.item_cost(opt)
            t = game.turns_to_complete(b, opt) if kind != "special" else 0
            tag = {"unit": "U", "facility": "F", "project": "P", "special": "$"}[kind]
            txt = f"[{tag}] {label}"
            ui.button(surf, rr, "", lambda o=opt: self.set_prod(o), selected=opt == b.production)
            theme.text(surf, txt, (rr.x + 6, rr.y + 4), 18,
                       theme.GOLD if kind == "project" else theme.TEXT)
            if kind != "special":
                theme.text(surf, f"{c}  ({t if t < 999 else '--'}t)", (rr.right - 6, rr.y + 4), 17, theme.TEXT_DIM, right=True)
            if rr.collidepoint(mouse):
                self.hover_item = opt
        if len(opts) > visible:
            theme.text(surf, f"scroll for more ({self.scroll + 1}-{min(len(opts), self.scroll + visible)} of {len(opts)})",
                       (px0, py0 + visible * row_h), 15, theme.TEXT_DIM)
        desc_item = self.hover_item or b.production
        theme.text_block(surf, item_description(desc_item), (px0, r.bottom - 124, pw, 60), 17, theme.TEXT)

        # --- Bottom: facilities and units -----------------------------------------
        by0 = fy + 70
        theme.text(surf, "Facilities", (mx, by0), 20, theme.ACCENT, bold=True)
        by0 += 22
        facs = sorted(b.facilities, key=lambda f: FACILITIES[f].name)
        projs = [PROJECTS[k].name for k, v in game.projects_built.items() if v == b.id]
        names = [FACILITIES[f].name for f in facs] + [f"* {n}" for n in projs]
        if not names:
            names = ["(none)"]
        for i, n in enumerate(names[:9]):
            theme.text(surf, n, (mx, by0 + i * 18), 17, theme.GOLD if n.startswith("*") else theme.TEXT)
        if len(names) > 9:
            theme.text(surf, f"... and {len(names) - 9} more", (mx, by0 + 9 * 18), 17, theme.TEXT_DIM)

        ux = r.x + 16
        uy = r.bottom - 120
        theme.text(surf, "Units in base", (ux, uy), 20, theme.ACCENT, bold=True)
        uy += 22
        units = game.units_at(b.x, b.y)
        if not units:
            theme.text(surf, "(none - the base is undefended!)", (ux, uy), 17, theme.WARN)
        for i, u in enumerate(units[:6]):
            bx = ux + (i % 2) * 150
            byy = uy + (i // 2) * 28
            ui.button(surf, (bx, byy, 144, 25), f"{u.name}", lambda u=u: self.activate(u),
                      enabled=u.owner == b.owner, size=16,
                      tooltip=f"{u.name} ({u.morale_name}) {u.type.attack}/{u.type.defense}/{u.type.moves} - click to activate")
        supported = sum(1 for u in game.units.values() if u.home == b.id)
        theme.text(surf, f"Supports {supported} unit(s)", (ux + 160, r.bottom - 118), 16, theme.TEXT_DIM)

    def _yields(self, surf, px, py, z, n, m, e):
        s = 12
        f = theme.font(s + 4, True)
        items = [(n, theme.NUTRIENT), (m, theme.MINERAL), (e, theme.ENERGY)]
        x = px + 3
        bg = pygame.Surface((z - 4, 14), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 170))
        surf.blit(bg, (px + 2, py + z - 16))
        for val, col in items:
            img = f.render(str(val), True, col)
            surf.blit(img, (x, py + z - 16))
            x += (z - 6) // 3

    def activate(self, u):
        self.app.select_unit(u)
        u.orders = None
        u.fortified = False
        self.close()

    def on_wheel(self, dy):
        self.scroll = max(0, self.scroll - dy)


# ---------------------------------------------------------------------------
class TechDialog(Dialog):
    width, height = 900, 640
    title = "Research"

    def draw(self, surf, ui):
        r = self.frame(surf, ui)
        game = self.game
        p = game.human
        x, y = r.x + 16, r.y + 48
        known = len(p.techs)
        total = len(TECHS)
        theme.text(surf, f"Known technologies: {known}/{total}    Era: {game.era(p.id)}", (x, y), 20, theme.TEXT_DIM)
        y += 26
        labs = sum(game.base_report(b)["labs"] for b in game.player_bases(p.id))
        if p.current_tech:
            cost = game.tech_cost(p.id, p.current_tech)
            theme.text(surf, f"Researching: {TECHS[p.current_tech].name}  ({p.research_progress}/{cost}, {labs} labs/turn)",
                       (x, y), 20, theme.ACCENT)
        else:
            theme.text(surf, "Choose a technology to research:", (x, y), 20, theme.WARN)
        y += 30
        opts = sorted(game.available_techs(p.id), key=lambda t: (t.era, t.name))
        row_h = 62
        visible = max(1, (r.bottom - y - 10) // row_h)
        self.scroll = min(self.scroll, max(0, len(opts) - visible))
        for t in opts[self.scroll:self.scroll + visible]:
            rr = pygame.Rect(x, y, r.width - 32, row_h - 6)
            ui.button(surf, rr, "", lambda t=t: self.pick(t.id), selected=p.current_tech == t.id)
            cost = game.tech_cost(p.id, t.id)
            turns = -(-(cost - (p.research_progress if p.current_tech == t.id else 0)) // max(1, labs))
            theme.text(surf, t.name, (rr.x + 8, rr.y + 5), 22, theme.TEXT, bold=True)
            theme.text(surf, f"{ERAS[t.era]} / {t.category}   cost {cost} (~{turns} turns)", (rr.right - 8, rr.y + 6), 17,
                       theme.TEXT_DIM, right=True)
            un = unlocks(t.id)
            line = t.description + ("   Unlocks: " + ", ".join(un) if un else "")
            theme.text_block(surf, line, (rr.x + 8, rr.y + 26, rr.width - 16, 30), 16, theme.TEXT_DIM, 0)
            y += row_h
        if not opts:
            theme.text(surf, "All technologies are known.", (x, y), 20, theme.GOOD)

    def pick(self, tech_id):
        self.game.set_research(self.game.human_id, tech_id)
        self.close()


# ---------------------------------------------------------------------------
class EconomyDialog(Dialog):
    width, height = 860, 640
    title = "Energy Allocation & Bases"

    def draw(self, surf, ui):
        r = self.frame(surf, ui)
        game = self.game
        p = game.human
        x, y = r.x + 16, r.y + 50
        names = ["Economy", "Psych", "Labs"]
        cols = [theme.ENERGY, (230, 130, 180), (120, 180, 240)]
        tips = ["Energy credits for upkeep and rush-buying.",
                "Makes drones content, preventing riots.",
                "Research towards new technologies."]
        for i in range(3):
            theme.text(surf, names[i], (x, y + 4), 22, cols[i], bold=True)
            ui.button(surf, (x + 110, y, 30, 26), "-", lambda i=i: self.shift(i, -1), enabled=p.alloc[i] > 0)
            theme.bar(surf, (x + 148, y + 6, 200, 14), p.alloc[i] / 10, cols[i])
            theme.text(surf, f"{p.alloc[i] * 10}%", (x + 356, y + 4), 20)
            ui.button(surf, (x + 404, y, 30, 26), "+", lambda i=i: self.shift(i, 1), enabled=p.alloc[i] < 10)
            theme.text(surf, tips[i], (x + 450, y + 5), 17, theme.TEXT_DIM)
            y += 34
        bases = sorted(game.player_bases(p.id), key=lambda b: b.founded)
        reps = [game.base_report(b) for b in bases]
        econ = sum(rp["econ"] for rp in reps)
        labs = sum(rp["labs"] for rp in reps)
        upkeep = sum(rp["upkeep"] for rp in reps)
        stock = sum(rp["minerals_net"] for b, rp in zip(bases, reps) if b.production == ("special", "stockpile"))
        y += 6
        theme.text(surf, f"Income {econ + stock}  -  upkeep {upkeep}  =  {econ + stock - upkeep:+d} credits/turn     "
                         f"Research {labs} labs/turn     Reserves {p.credits}", (x, y), 20, theme.TEXT)
        y += 34
        headers = [("Base", 0), ("Size", 190), ("N", 240), ("M", 280), ("E", 320), ("Drones", 360), ("Building", 430)]
        for h, dx in headers:
            theme.text(surf, h, (x + dx, y), 18, theme.ACCENT, bold=True)
        y += 22
        row_h = 26
        visible = max(1, (r.bottom - y - 10) // row_h)
        self.scroll = min(self.scroll, max(0, len(bases) - visible))
        for b, rp in list(zip(bases, reps))[self.scroll:self.scroll + visible]:
            rr = pygame.Rect(x - 4, y - 2, r.width - 24, row_h - 2)
            ui.button(surf, rr, "", lambda b=b: self.app.open_base(b))
            theme.text(surf, b.name, (x, y + 2), 18, theme.WARN if rp["rioting"] else theme.TEXT)
            theme.text(surf, b.pop, (x + 190, y + 2), 18)
            theme.text(surf, f"{rp['nutrient_surplus']:+d}", (x + 240, y + 2), 18, theme.NUTRIENT)
            theme.text(surf, rp["minerals_net"], (x + 280, y + 2), 18, theme.MINERAL)
            theme.text(surf, rp["energy"], (x + 320, y + 2), 18, theme.ENERGY)
            theme.text(surf, rp["drones"], (x + 360, y + 2), 18, theme.WARN if rp["drones"] else theme.TEXT)
            t = game.turns_to_complete(b)
            theme.text(surf, f"{game.item_name(b.production)} ({t if t < 999 else '--'})", (x + 430, y + 2), 18)
            y += row_h
        if not bases:
            theme.text(surf, "You have no bases yet. Use a Colony Pod to found one (B).", (x, y), 19, theme.WARN)

    def shift(self, i, d):
        p = self.game.human
        a = p.alloc
        if not 0 <= a[i] + d <= 10:
            return
        # Take from / give to the other categories, preferring the larger one.
        others = sorted([j for j in range(3) if j != i], key=lambda j: -a[j] if d > 0 else a[j])
        for j in others:
            if 0 <= a[j] - d <= 10:
                a[j] -= d
                a[i] += d
                return


# ---------------------------------------------------------------------------
class DiplomacyDialog(Dialog):
    width, height = 820, 560
    title = "Diplomacy"

    def draw(self, surf, ui):
        r = self.frame(surf, ui)
        game = self.game
        me = game.human
        x, y = r.x + 16, r.y + 50
        others = [p for p in game.players if not p.is_native and p.id != me.id]
        for p in others:
            rr = pygame.Rect(x, y, r.width - 32, 70)
            theme.panel(surf, rr, theme.PANEL_LIGHT, None)
            pygame.draw.rect(surf, p.color, (rr.x, rr.y, 8, rr.height))
            if not me.has_contact(p.id):
                theme.text(surf, "Unknown faction", (rr.x + 18, rr.y + 10), 22, theme.TEXT_DIM, bold=True)
                theme.text(surf, "You have not made contact yet.", (rr.x + 18, rr.y + 38), 18, theme.TEXT_DIM)
            else:
                f = p.faction
                status = "ELIMINATED" if not p.alive else me.relations[p.id].upper()
                col = theme.WARN if status == "WAR" else theme.GOOD if status == "PEACE" else theme.TEXT_DIM
                theme.text(surf, f"{f.name}", (rr.x + 18, rr.y + 8), 22, p.color, bold=True)
                theme.text(surf, f"{f.leader}", (rr.x + 18, rr.y + 32), 18, theme.TEXT_DIM)
                theme.text(surf, status, (rr.x + 330, rr.y + 10), 22, col, bold=True)
                nb = len(game.player_bases(p.id))
                theme.text(surf, f"{nb} bases   score {game.score(p.id)}", (rr.x + 330, rr.y + 38), 18, theme.TEXT_DIM)
                if p.alive:
                    if status == "PEACE":
                        ui.button(surf, (rr.right - 170, rr.y + 20, 156, 30), "Declare War",
                                  lambda p=p: game.declare_war(me.id, p.id))
                    else:
                        ui.button(surf, (rr.right - 170, rr.y + 20, 156, 30), "Propose Peace",
                                  lambda p=p: self.peace(p))
            y += 78
        if hasattr(self, "result"):
            theme.text(surf, self.result, (x, r.bottom - 34), 20, theme.GOLD)

    def peace(self, p):
        if self.game.propose_peace(self.game.human_id, p.id):
            self.result = f"{p.faction.leader} accepts your offer of peace."
        else:
            self.result = f"{p.faction.leader} rejects your offer. \"Not while we are winning.\""


# ---------------------------------------------------------------------------
class StatusDialog(Dialog):
    width, height = 820, 580
    title = "Planetary Status"

    def draw(self, surf, ui):
        r = self.frame(surf, ui)
        game = self.game
        me = game.human
        x, y = r.x + 16, r.y + 50
        theme.text(surf, f"Mission Year {game.year} (turn {game.turn})", (x, y), 22, theme.TEXT)
        y += 34
        theme.text(surf, "Faction", (x, y), 18, theme.ACCENT, bold=True)
        for h, dx in (("Bases", 300), ("Pop", 370), ("Techs", 430), ("Score", 500)):
            theme.text(surf, h, (x + dx, y), 18, theme.ACCENT, bold=True)
        y += 24
        rows = sorted([p for p in game.players if not p.is_native], key=lambda p: -game.score(p.id))
        for p in rows:
            known = p.id == me.id or me.has_contact(p.id)
            name = p.name if known else "Unknown faction"
            theme.text(surf, name + ("" if p.alive else " (eliminated)"), (x, y), 19, p.color if known else theme.TEXT_DIM)
            if known:
                bases = game.player_bases(p.id)
                theme.text(surf, len(bases), (x + 300, y), 19)
                theme.text(surf, sum(b.pop for b in bases), (x + 370, y), 19)
                theme.text(surf, len(p.techs), (x + 430, y), 19)
                theme.text(surf, game.score(p.id), (x + 500, y), 19)
            y += 24
        y += 16
        theme.text(surf, "Victory conditions", (x, y), 22, theme.ACCENT, bold=True)
        y += 28
        for name, desc, _fn in VICTORY_CONDITIONS:
            theme.text(surf, f"{name}: {desc}", (x, y), 19, theme.TEXT)
            y += 22
        y += 10
        theme.text(surf, "Secret projects", (x, y), 22, theme.ACCENT, bold=True)
        y += 28
        for pid, bid in game.projects_built.items():
            owner = game.project_owner(pid)
            who = game.players[owner].name if owner is not None else "(destroyed)"
            theme.text(surf, f"{PROJECTS[pid].name} - {who}", (x, y), 18, theme.GOLD)
            y += 20
        if not game.projects_built:
            theme.text(surf, "None completed yet.", (x, y), 18, theme.TEXT_DIM)


# ---------------------------------------------------------------------------
HELP_TEXT = """GOAL: Build a thriving civilization on an alien world. Win by Conquest or by Transcendence (research Transcendence and build the Ascension Engine).

MOUSE: Left-click a unit to select it, left-click your base to open it. Right-click a tile to send the selected unit there. Drag the map to pan, mouse wheel to zoom. Click the minimap to jump.

MOVEMENT: Arrow keys or numpad 1-9 move the selected unit (Home/PgUp/End/PgDn for diagonals). Moving into an enemy attacks it.

UNIT ORDERS: B found base (Colony Pod) | H hold/fortify | L sentry | Space skip turn | W wait | E explore | G go-to (then click) | C centre | Tab next unit | Delete disband.

FORMERS: F farm | M mine | S solar collector | R road | N plant forest | X remove fungus | A automate.

SCREENS: F1 help | F2 energy allocation & base list | F3 research | F4 diplomacy | F5 status | Esc menu | Enter end turn. Ctrl+S quicksave, Ctrl+L quickload.

TIPS: Bases need defenders - native Xenoworms roam the fungus. Tiles yield Nutrients (growth), Minerals (production) and Energy (credits, psych, labs). Bases larger than 4 produce drones; if drones outnumber the other citizens the base riots. Move energy to Psych or build Recreation Commons to keep order. Early on, no tile can produce more than 2 of any resource - Gene Splicing, Ecological Engineering and Environmental Economics lift those limits."""


class HelpDialog(Dialog):
    width, height = 900, 620
    title = "How to Play"

    def draw(self, surf, ui):
        r = self.frame(surf, ui)
        theme.text_block(surf, HELP_TEXT, (r.x + 18, r.y + 50, r.width - 36, r.height - 60), 20, theme.TEXT, 3)


# ---------------------------------------------------------------------------
class GameMenuDialog(Dialog):
    width, height = 360, 330
    title = "Menu"

    def draw(self, surf, ui):
        r = self.frame(surf, ui)
        x = r.x + 40
        y = r.y + 56
        w = r.width - 80
        for label, cb in (("Resume", self.close), ("Quick Save  (Ctrl+S)", self.app.quick_save),
                          ("Quick Load  (Ctrl+L)", self.app.quick_load), ("Help  (F1)", lambda: self.app.open_dialog(HelpDialog(self.app))),
                          ("Main Menu", self.app.to_main_menu), ("Quit", self.app.quit)):
            ui.button(surf, (x, y, w, 36), label, cb)
            y += 44


class GameOverDialog(Dialog):
    width, height = 560, 300
    title = "The Game Is Decided"

    def draw(self, surf, ui):
        r = self.frame(surf, ui)
        game = self.game
        pid, kind = game.winner
        me = game.human_id
        if pid == me:
            msg = f"VICTORY! The {game.players[pid].name} wins by {kind}."
            col = theme.GOOD
        else:
            msg = f"The {game.players[pid].name} wins by {kind}."
            col = theme.WARN
        theme.text(surf, msg, (r.centerx, r.y + 80), 26, col, bold=True, center=True)
        theme.text(surf, f"Mission Year {game.year}   Your score: {game.score(me)}", (r.centerx, r.y + 120), 20,
                   theme.TEXT, center=True)
        ui.button(surf, (r.x + 30, r.bottom - 60, 150, 36), "Keep Looking", self.close)
        ui.button(surf, (r.centerx - 75, r.bottom - 60, 150, 36), "Main Menu", self.app.to_main_menu)
        ui.button(surf, (r.right - 180, r.bottom - 60, 150, 36), "Quit", self.app.quit)


class LoadDialog(Dialog):
    width, height = 560, 460
    title = "Load Game"

    def draw(self, surf, ui):
        r = self.frame(surf, ui)
        saves = self.app.list_saves()
        y = r.y + 56
        if not saves:
            theme.text(surf, "No saved games found.", (r.x + 20, y), 20, theme.TEXT_DIM)
        for name in saves[:10]:
            ui.button(surf, (r.x + 20, y, r.width - 40, 32), name, lambda n=name: self.app.load_game(n))
            y += 38
