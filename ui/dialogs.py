"""Modal windows: base screen, research, economy, diplomacy, status, help and menus."""
import pygame

from game import lore
from game.data import TECHS, UNITS, FACILITIES, PROJECTS, TERRAFORMS, FACTIONS, ERAS
from game.victory import VICTORY_CONDITIONS
from . import describe, theme
from .renderer import diamond, draw_base, draw_roads, tile_sprite


def draw_info(surf, rect, info):
    """Render an item_info() dict into rect, clipping at the bottom."""
    x, y, w, h = rect
    bottom = y + h
    theme.panel(surf, (x - 8, y - 6, w + 16, h + 12), (16, 22, 30), theme.PANEL_BORDER)

    def line(txt, size, color, bold=False, indent=0):
        nonlocal y
        lh = theme.font(size).get_linesize()
        for ln in theme.wrap(txt, size, w - indent):
            if y + lh > bottom:
                return False
            theme.text(surf, ln, (x + indent, y), size, color, bold)
            y += lh
        return True

    line(info["title"], 22, theme.GOLD if "project" in info["kind"].lower() else theme.TEXT, True)
    line(info["kind"], 16, theme.ACCENT)
    if info["stats"]:
        line(info["stats"], 16, theme.TEXT_DIM)
    y += 4
    for para in info["body"].split("\n"):
        if para and not line(para, 17, theme.TEXT):
            return
    for pro in info["pros"]:
        if not line("+ " + pro, 16, theme.GOOD, indent=4):
            return
    for con in info["cons"]:
        if not line("- " + con, 16, theme.WARN, indent=4):
            return
    if info["here"]:
        y += 2
        if not line(info["here"], 16, (140, 200, 250)):
            return
    if info["quote"]:
        y += 6
        q, who = info["quote"]
        if line(q, 16, (190, 185, 160)):
            line("- " + who, 15, theme.TEXT_DIM, indent=20)


def draw_quote(surf, quote, rect, size=17):
    if not quote:
        return rect[1]
    q, who = quote
    y = theme.text_block(surf, q, rect, size, (190, 185, 160))
    theme.text(surf, "- " + who, (rect[0] + 20, y), size - 2, theme.TEXT_DIM)
    return y + 20


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
        theme.resource_icon(surf, "nutrients", (x + 7, y + 7), 7)
        rr = theme.text(surf, f"Nutrients {rep['nutrients']}   eaten {b.pop * 2}   surplus {surplus:+d}",
                        (x + 20, y), 20, theme.NUTRIENT)
        ui.hotspot(pygame.Rect(x, y, rr.right - x, 20), lore.RESOURCES["nutrients"]["text"])
        y += 20
        theme.bar(surf, (x, y, colw - 20, 10), b.nutrients / max(1, grow), theme.NUTRIENT)
        y += 13
        theme.text(surf, f"{b.nutrients}/{grow}, {gtxt}", (x, y), 17, theme.TEXT_DIM)
        y += 24
        theme.resource_icon(surf, "minerals", (x + 7, y + 7), 7)
        rr = theme.text(surf, f"Minerals {rep['minerals']}   to production {rep['minerals_net']}",
                        (x + 20, y), 20, theme.MINERAL)
        ui.hotspot(pygame.Rect(x, y, rr.right - x, 20), lore.RESOURCES["minerals"]["text"])
        y += 20
        if rep.get("landing"):
            from game.game import LANDING_TURNS, START_YEAR
            rr = theme.text(surf, "Landing supplies: +1 nutrient, +1 mineral", (x, y), 16, theme.GOLD)
            ui.hotspot(rr, "Supplies dropped from the colony ship in orbit keep every base fed and building during "
                           f"planetfall, until M.Y. {START_YEAR + LANDING_TURNS - 1}. Use them to expand quickly.")
            y += 18
        theme.text(surf, f"Unit support cost: {rep['support']}" + ("  (riot: nothing built!)" if rep["rioting"] else ""),
                   (x, y), 17, theme.TEXT_DIM)
        y += 24
        theme.resource_icon(surf, "energy", (x + 7, y + 7), 7)
        rr = theme.text(surf, f"Energy {rep['energy']}   lost to distance {rep['inefficiency']}",
                        (x + 20, y), 20, theme.ENERGY)
        ui.hotspot(pygame.Rect(x, y, rr.right - x, 20), lore.RESOURCES["energy"]["text"])
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
        ui.hotspot(pygame.Rect(x, y - 24, colw, 22),
                   "Green: workers on tiles. Blue: specialists (no free tile to work; each makes 2 energy). "
                   "Red: drones (unhappy). If drones are more than half the population, the base riots.")
        theme.text(surf, f"{drones} drone(s), {b.specialists} specialist(s)", (x, y), 17, theme.TEXT_DIM)
        y += 18
        if rep["rioting"]:
            theme.text(surf, "DRONE RIOT - production halted!", (x, y), 19, theme.WARN, bold=True)
            y += 18
            theme.text(surf, "Raise psych (F2) or build Rec Commons.", (x, y), 17, theme.WARN)
            y += 18
        y += 8
        theme.text(surf, f"Population limit: {rep['pop_cap']}", (x, y), 17, theme.TEXT_DIM)

        # --- Centre: base map (isometric, the 21-tile work radius) --------------
        tw = 64
        cw = 4 * tw + 8  # the work radius is 4 diamonds wide and 2 tall
        mx = r.x + 16 + colw + 10
        my = r.y + 52
        world = game.world
        area = pygame.Rect(mx - 2, my - 2, cw + 4, 2 * tw + 12)
        pygame.draw.rect(surf, (4, 6, 10), area)
        pygame.draw.rect(surf, theme.PANEL_BORDER, area, 1)
        ccx, ccy = mx + cw / 2, my + tw + 4
        worked = set(b.worked)
        cells = []
        for tx, ty in world.base_radius(b.x, b.y):
            cells.append((ty - b.y, world.dx2(b.x, b.y, tx, ty), tx, ty))
        dim = pygame.Surface((tw, tw // 2), pygame.SRCALPHA)
        pygame.draw.polygon(dim, (0, 0, 0, 110), diamond(tw / 2, tw / 4, tw))
        for ddy, ddx2, tx, ty in sorted(cells):
            cx, cy = ccx + ddx2 * tw / 2, ccy + ddy * tw / 4
            t = world.tiles[tx][ty]
            if not game.is_explored(b.owner, tx, ty):
                pygame.draw.polygon(surf, (0, 0, 0), diamond(cx, cy, tw))
                continue
            surf.blit(tile_sprite(world, t, tw), (cx - tw / 2, cy - tw / 4))
            draw_roads(surf, world, t, cx, cy, tw, game.base_pos)
            is_base = (tx, ty) == (b.x, b.y)
            ty_ = game.tile_yield(t, b.owner, is_base)
            status = "base tile" if is_base else "worked" if (tx, ty) in worked else "not worked"
            ui.hotspot((cx - tw / 4, cy - tw / 8, tw / 2, tw / 4), f"{t.terrain_name()} ({status})\n"
                                                                    f"{ty_[0]} nutrients, {ty_[1]} minerals, {ty_[2]} energy\n"
                                                                    f"{describe.best_use_hint(t)}")
            if is_base:
                draw_base(surf, game, b, cx, cy - tw / 10, tw, label=False)
                self._yields(surf, cx, cy, tw, *ty_)
            elif (tx, ty) in worked:
                pygame.draw.polygon(surf, (255, 255, 255), diamond(cx, cy, tw, 2), 2)
                self._yields(surf, cx, cy, tw, *ty_)
            else:
                surf.blit(dim, (cx - tw / 2, cy - tw / 4))
                if t.owner is not None and t.owner != b.owner:
                    pygame.draw.line(surf, (220, 60, 60), (cx - 6, cy - 3), (cx + 6, cy + 3), 2)
                    pygame.draw.line(surf, (220, 60, 60), (cx - 6, cy + 3), (cx + 6, cy - 3), 2)
        fy = my + 2 * tw + 22
        theme.text(surf, "Governor focus", (mx, fy), 18, theme.TEXT_DIM)
        fy += 20
        bw = cw // 2 - 3
        for i, (key, label) in enumerate((("balanced", "Balanced"), ("growth", "Growth"),
                                           ("production", "Production"), ("energy", "Energy"))):
            bx = mx + (i % 2) * (bw + 6)
            by = fy + (i // 2) * 30
            ui.button(surf, (bx, by, bw, 26), label, lambda k=key: self.set_focus(k), selected=b.focus == key, size=18)

        # --- Right: production --------------------------------------------------
        px0 = mx + cw + 20
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
        list_h = r.bottom - 262 - py0
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
            tag, tcol = {"unit": ("UNIT", (90, 150, 200)), "facility": ("BLDG", (110, 170, 110)),
                         "project": ("WNDR", (200, 170, 70)), "special": ("CRED", (200, 180, 80))}[kind]
            ui.button(surf, rr, "", lambda o=opt: self.set_prod(o), selected=opt == b.production)
            chip = pygame.Rect(rr.x + 4, rr.y + 4, 40, rr.height - 8)
            pygame.draw.rect(surf, tcol, chip, border_radius=3)
            theme.text(surf, tag, chip.center, 14, (10, 12, 14), bold=True, center=True)
            theme.text(surf, label, (rr.x + 50, rr.y + 4), 18,
                       theme.GOLD if kind == "project" else theme.TEXT)
            if kind != "special":
                theme.text(surf, f"{c}  ({t if t < 999 else '--'}t)", (rr.right - 6, rr.y + 4), 17, theme.TEXT_DIM, right=True)
            if rr.collidepoint(mouse):
                self.hover_item = opt
        if len(opts) > visible:
            theme.text(surf, f"scroll for more ({self.scroll + 1}-{min(len(opts), self.scroll + visible)} of {len(opts)})",
                       (px0, py0 + visible * row_h), 15, theme.TEXT_DIM)
        desc_item = self.hover_item or b.production
        draw_info(surf, (px0 + 8, r.bottom - 236, pw - 16, 222), describe.item_info(game, b, desc_item))

        # --- Bottom: facilities and units -----------------------------------------
        by0 = fy + 70
        theme.text(surf, "Facilities", (mx, by0), 20, theme.ACCENT, bold=True)
        by0 += 22
        facs = sorted(b.facilities, key=lambda f: FACILITIES[f].name)
        projs = [PROJECTS[k].name for k, v in game.projects_built.items() if v == b.id]
        names = [FACILITIES[f].name for f in facs] + [f"* {n}" for n in projs]
        if not names:
            names = ["(none)"]
        tips = [f"{FACILITIES[f].description} Upkeep {FACILITIES[f].upkeep}." for f in facs] + \
               [PROJECTS[k].description for k, v in game.projects_built.items() if v == b.id]
        for i, n in enumerate(names[:9]):
            rr = theme.text(surf, n, (mx, by0 + i * 18), 17, theme.GOLD if n.startswith("*") else theme.TEXT)
            if i < len(tips):
                ui.hotspot(rr, tips[i])
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
                      tooltip=f"{describe.unit_tooltip(u.type)}\nMorale: {u.morale_name}. Click to give it orders.")
        supported = sum(1 for u in game.units.values() if u.home == b.id)
        theme.text(surf, f"Supports {supported} unit(s)", (ux + 160, r.bottom - 118), 16, theme.TEXT_DIM)

    def _yields(self, surf, cx, cy, tw, n, m, e):
        f = theme.font(15, True)
        w = 48
        bg = pygame.Surface((w, 13), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 175))
        surf.blit(bg, (cx - w / 2, cy + 1))
        x = cx - w / 2 + 2
        for kind, val in (("nutrients", n), ("minerals", m), ("energy", e)):
            theme.resource_icon(surf, kind, (int(x + 3), int(cy + 7)), 3)
            surf.blit(f.render(str(val), True, theme.RESOURCE_COLORS[kind]), (x + 7, cy + 1))
            x += w / 3

    def activate(self, u):
        self.app.select_unit(u)
        u.orders = None
        u.fortified = False
        self.close()

    def on_wheel(self, dy):
        self.scroll = max(0, self.scroll - dy)


# ---------------------------------------------------------------------------
class TechDialog(Dialog):
    width, height = 960, 680
    title = "Research"

    def draw(self, surf, ui):
        r = self.frame(surf, ui)
        game = self.game
        p = game.human
        x, y = r.x + 16, r.y + 48
        theme.text(surf, f"Known technologies: {len(p.techs)}/{len(TECHS)}    Era: {game.era(p.id)}", (x, y), 20,
                   theme.TEXT_DIM)
        y += 26
        labs = sum(game.base_report(b)["labs"] for b in game.player_bases(p.id))
        if p.current_tech:
            cost = game.tech_cost(p.id, p.current_tech)
            theme.text(surf, f"Researching: {TECHS[p.current_tech].name}  ({p.research_progress}/{cost}, "
                             f"{labs} labs per turn)", (x, y), 20, theme.ACCENT)
        else:
            theme.text(surf, "Choose what your scientists work on next. Hover for details.", (x, y), 20, theme.WARN)
        y += 30
        opts = sorted(game.available_techs(p.id), key=lambda t: (t.era, t.name))
        row_h = 92
        visible = max(1, (r.bottom - y - 10) // row_h)
        self.scroll = min(self.scroll, max(0, len(opts) - visible))
        for t in opts[self.scroll:self.scroll + visible]:
            info = describe.tech_text(t.id)
            rr = pygame.Rect(x, y, r.width - 32, row_h - 6)
            ui.button(surf, rr, "", lambda t=t: self.pick(t.id), selected=p.current_tech == t.id)
            cost = game.tech_cost(p.id, t.id)
            turns = -(-(cost - (p.research_progress if p.current_tech == t.id else 0)) // max(1, labs))
            theme.text(surf, t.name, (rr.x + 10, rr.y + 6), 23, theme.TEXT, bold=True)
            theme.text(surf, f"{info['era']} era  |  {t.category}  |  {cost} labs, about {turns} turns",
                       (rr.right - 10, rr.y + 8), 17, theme.TEXT_DIM, right=True)
            theme.text(surf, t.description, (rr.x + 10, rr.y + 30), 18, theme.TEXT)
            ux = rr.x + 10
            for kind, name in info["unlocks"]:
                label = f"{kind}: {name}"
                col = {"Unit": (90, 150, 200), "Facility": (110, 170, 110), "Project": (200, 170, 70),
                       "Terraform": (170, 130, 90), "Effect": (160, 120, 200)}[kind]
                wdt = theme.font(15).size(label)[0] + 10
                if ux + wdt > rr.right - 10:
                    break
                pygame.draw.rect(surf, col, (ux, rr.y + 50, wdt, 17), border_radius=3)
                theme.text(surf, label, (ux + 5, rr.y + 51), 15, (12, 14, 16), bold=True)
                ux += wdt + 6
            if info["quote"]:
                theme.text(surf, f"{info['quote'][0]}  - {info['quote'][1]}", (rr.x + 10, rr.y + 68), 15,
                           (170, 165, 140))
            y += row_h
        if not opts:
            theme.text(surf, "All technologies are known.", (x, y), 20, theme.GOOD)

    def pick(self, tech_id):
        self.game.set_research(self.game.human_id, tech_id)
        self.close()


class DiscoveryDialog(Dialog):
    """Shown when the player discovers a technology or completes a secret project."""
    width, height = 720, 440

    def __init__(self, app, tech_ids=(), project_ids=()):
        super().__init__(app)
        self.items = [("tech", t) for t in tech_ids] + [("project", p) for p in project_ids]
        self.index = 0

    @property
    def title(self):
        kind, _ = self.items[self.index]
        return "Breakthrough!" if kind == "tech" else "Secret Project Complete!"

    def draw(self, surf, ui):
        r = self.frame(surf, ui)
        kind, iid = self.items[self.index]
        x, y, w = r.x + 24, r.y + 56, r.width - 48
        if kind == "tech":
            info = describe.tech_text(iid)
            theme.text(surf, info["name"], (x, y), 34, theme.GOLD, bold=True)
            y += 38
            theme.text(surf, f"{info['era']} era  |  {info['category']}", (x, y), 18, theme.TEXT_DIM)
            y += 30
            y = draw_quote(surf, info["quote"], (x + 10, y, w - 20, 60), 20) + 8
            theme.text(surf, info["description"], (x, y), 20, theme.TEXT)
            y += 30
            if info["unlocks"]:
                theme.text(surf, "Now available:", (x, y), 20, theme.ACCENT, bold=True)
                y += 24
                for k, name in info["unlocks"][:6]:
                    theme.text(surf, f"  {k}: {name}", (x, y), 19, theme.TEXT)
                    y += 21
        else:
            pr = PROJECTS[iid]
            desc, quote = lore.PROJECTS.get(iid, ("", None))
            theme.text(surf, pr.name, (x, y), 34, theme.GOLD, bold=True)
            y += 44
            y = draw_quote(surf, quote, (x + 10, y, w - 20, 60), 20) + 8
            y = theme.text_block(surf, desc, (x, y, w, 60), 20, theme.TEXT) + 6
            theme.text_block(surf, "Effect: " + pr.description, (x, y, w, 60), 20, theme.GOOD)
        label = "Continue" if self.index < len(self.items) - 1 else "Close"
        ui.button(surf, (r.right - 160, r.bottom - 52, 140, 36), label, self.next)
        if self.index < len(self.items) - 1:
            theme.text(surf, f"{self.index + 1} of {len(self.items)}", (r.x + 24, r.bottom - 44), 18, theme.TEXT_DIM)

    def next(self):
        if self.index < len(self.items) - 1:
            self.index += 1
        else:
            self.close()

    def on_key(self, event):
        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.next()
            return True
        return False


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
def _entry(title, kind="", stats="", body="", pros=(), cons=(), here="", quote=None):
    return {"title": title, "kind": kind, "stats": stats, "body": body, "pros": list(pros), "cons": list(cons),
            "here": here, "quote": quote}


def datalinks_entries():
    """All encyclopedia entries grouped by category (order matters)."""
    cats = {}
    cats["Guide"] = [_entry(t, "Guide", body=b) for t, b in lore.CONCEPTS]
    cats["Resources"] = [_entry(v["name"], "Resource", body=v["text"], quote=v["quote"]) for v in lore.RESOURCES.values()]
    terr = [_entry(n, "Terrain", body=d) for n, d in lore.TERRAIN.values()]
    terr += [_entry(n, "Map feature", body=d) for n, d in lore.SPECIALS.values()]
    cats["Terrain"] = terr
    cats["Terraforming"] = []
    for key, (n, d) in lore.IMPROVEMENTS.items():
        tf = TERRAFORMS.get(key)
        stats = f"{tf.turns} turns of Former work   Key: {tf.key.upper()}" if tf else ""
        if tf and tf.prereq:
            stats += f"   Requires {TECHS[tf.prereq].name}"
        cats["Terraforming"].append(_entry(n, "Terrain improvement", stats, d))
    units = []
    for u in UNITS.values():
        info = lore.UNITS.get(u.id, {})
        req = "Available from the start" if not u.prereq else (
            "Native life - cannot be built" if u.native else f"Requires {TECHS[u.prereq].name}")
        units.append(_entry(u.name, f"Unit - {info.get('role', '')}", describe.unit_summary(u) + "\n" + req,
                            info.get("text", ""), info.get("pros", ()), info.get("cons", ()), quote=info.get("quote")))
    cats["Units"] = units
    facs = []
    for f in FACILITIES.values():
        desc, advice, quote = lore.FACILITIES.get(f.id, ("", "", None))
        req = f"Requires {TECHS[f.prereq].name}" if f.prereq else "Available from the start"
        facs.append(_entry(f.name, "Base facility", f"Cost {f.cost}   Upkeep {f.upkeep}   {req}",
                           f"{desc} {f.description}", [advice] if advice else [], quote=quote))
    cats["Facilities"] = facs
    projs = []
    for pr in PROJECTS.values():
        desc, quote = lore.PROJECTS.get(pr.id, ("", None))
        projs.append(_entry(pr.name, "Secret project", f"Cost {pr.cost}   Requires {TECHS[pr.prereq].name}",
                            f"{desc}\nEffect: {pr.description}", quote=quote))
    cats["Secret Projects"] = projs
    techs = []
    for t in sorted(TECHS.values(), key=lambda t: (t.era, t.name)):
        info = describe.tech_text(t.id)
        pre = ", ".join(info["prereqs"]) or "none"
        body = t.description + "\nUnlocks: " + (", ".join(f"{k} {n}" for k, n in info["unlocks"]) or "nothing directly")
        techs.append(_entry(t.name, f"Technology - {info['era']} era, {t.category}", f"Requires: {pre}", body,
                            quote=info["quote"]))
    cats["Technologies"] = techs
    facts = []
    for f in FACTIONS.values():
        facts.append(_entry(f.name, f"Faction - led by {f.leader}", f.description, lore.FACTION_LORE.get(f.id, "")))
    cats["Factions"] = facts
    return cats


class DatalinksDialog(Dialog):
    width, height = 1080, 700
    title = "Datalinks - Planetary Encyclopedia"

    def __init__(self, app, category="Guide", entry=None):
        super().__init__(app)
        self.cats = datalinks_entries()
        self.category = category
        self.entry = 0
        if entry:
            for i, e in enumerate(self.cats[category]):
                if e["title"] == entry:
                    self.entry = i

    def set_cat(self, c):
        self.category = c
        self.entry = 0
        self.scroll = 0

    def draw(self, surf, ui):
        r = self.frame(surf, ui)
        x, y = r.x + 14, r.y + 50
        for c in self.cats:
            ui.button(surf, (x, y, 170, 32), c, lambda c=c: self.set_cat(c), selected=c == self.category, size=19)
            y += 38
        entries = self.cats[self.category]
        lx, ly = x + 184, r.y + 50
        row_h = 28
        visible = max(1, (r.bottom - ly - 14) // row_h)
        self.scroll = min(self.scroll, max(0, len(entries) - visible))
        for i, e in enumerate(entries[self.scroll:self.scroll + visible]):
            idx = i + self.scroll
            ui.button(surf, (lx, ly, 240, row_h - 4), e["title"], lambda idx=idx: setattr(self, "entry", idx),
                      selected=idx == self.entry, size=17)
            ly += row_h
        dx = lx + 262
        e = entries[min(self.entry, len(entries) - 1)]
        draw_info(surf, (dx, r.y + 56, r.right - dx - 22, r.height - 76), e)

    def on_key(self, event):
        entries = self.cats[self.category]
        if event.key in (pygame.K_DOWN, pygame.K_KP2):
            self.entry = min(len(entries) - 1, self.entry + 1)
            return True
        if event.key in (pygame.K_UP, pygame.K_KP8):
            self.entry = max(0, self.entry - 1)
            return True
        return super().on_key(event)


# ---------------------------------------------------------------------------
HELP_TEXT = """NEW TO THE GAME? Open the Datalinks (F6) and read the Guide section. Hover over almost anything - resources, tiles, buttons, citizens - for an explanation.

GOAL: Build a thriving civilization on an alien world. Win by Conquest or by Transcendence (research Transcendence and build the Ascension Engine).

MOUSE: Left-click a unit to select it, left-click your base to open it. Right-click a tile to send the selected unit there. Drag the map to pan, mouse wheel to zoom. Click the minimap to jump.

MOVEMENT: Arrow keys or numpad 1-9 move the selected unit (Home/PgUp/End/PgDn for diagonals). Moving into an enemy attacks it.

UNIT ORDERS: B found base (Colony Pod) | H hold/fortify | L sentry | Space skip turn | W wait | E explore | G go-to (then click) | C centre | Tab next unit | Delete disband.

FORMERS: F farm | M mine | S solar collector | R road | N plant forest | X remove fungus | A automate.

SCREENS: F1 help | F2 energy allocation & base list | F3 research | F4 diplomacy | F5 status | F6 Datalinks encyclopedia (everything explained) | Esc menu | Enter end turn. Ctrl+S quicksave, Ctrl+L quickload.

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
