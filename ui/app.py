"""Top-level application: main menu, new-game setup, and the in-game screen."""
import math
import os
import pickle
import random

import pygame

from game.data import FACTION_LIST, FACTIONS, TECHS, TERRAFORMS
from game.entities import MOVE_POINTS
from game.game import Game, MAP_SIZES
from game.pathfinding import find_path
from . import theme
from game import lore
from . import describe
from .dialogs import (BaseDialog, TechDialog, EconomyDialog, DiplomacyDialog, StatusDialog, HelpDialog,
                      GameMenuDialog, GameOverDialog, LoadDialog, DatalinksDialog, DiscoveryDialog,
                      ProposalDialog, EventDialog, SocietyDialog)

ACTION_TIPS = {
    "Found Base": "Turn this Colony Pod into a new base on this tile. Bases must be at least 3 tiles apart and "
                  "outside other factions' territory.",
    "Automate": "Let the Former choose and build improvements around your bases by itself, every turn.",
    "Fortify": "Dig in: +25% defense from next turn. The unit stays put until you select it again.",
    "Sentry": "Stand watch without digging in. The unit won't ask for orders until you select it.",
    "Explore": "Automatically scout unexplored land and pick up supply pods, every turn.",
    "Go to": "Pick a destination; the unit travels there over the next turns. Right-clicking a tile does the same.",
    "Wait": "Skip to the next unit for now and come back to this one later this turn.",
    "Skip": "This unit does nothing this turn.",
    "Disband": "Permanently remove this unit. Frees its home base from paying its upkeep.",
    "Next unit": "Jump to the next unit that is waiting for orders.",
    "Board": "Load this unit onto the transport in this base. It sails with the transport; move it onto "
             "land next to the transport to go ashore.",
}
from .renderer import MapView
from .widgets import UI, Button

GAME_TITLE = "New Civilization"
TOP_H = 34
SIDE_W = 290
SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saves")

# Screen directions on the diamond grid. Up/Down/Left/Right move to the corner-touching neighbours
# (straight up, down, left, right on screen); the diagonals move across the diamond edges.
MOVE_KEYS = {
    pygame.K_UP: "N", pygame.K_DOWN: "S", pygame.K_LEFT: "W", pygame.K_RIGHT: "E",
    pygame.K_KP8: "N", pygame.K_KP2: "S", pygame.K_KP4: "W", pygame.K_KP6: "E",
    pygame.K_KP7: "NW", pygame.K_KP9: "NE", pygame.K_KP1: "SW", pygame.K_KP3: "SE",
    pygame.K_HOME: "NW", pygame.K_PAGEUP: "NE", pygame.K_END: "SW", pygame.K_PAGEDOWN: "SE",
}
PAN_VECTORS = {"N": (0, 1), "S": (0, -1), "W": (1, 0), "E": (-1, 0),
               "NW": (1, 1), "NE": (-1, 1), "SW": (1, -1), "SE": (-1, -1)}


class App:
    def __init__(self, screen):
        self.screen = screen
        self.surf = screen.screen
        self.clock = screen.clock
        self.ui = UI()
        self.state = "menu"
        self.game = None
        self.view = None
        self.dialogs = []
        self.selected = None
        self.hover_tile = None
        self.goto_mode = False
        self.path_cache = (None, None, None)
        self.waited = set()
        self.running = True
        self.toast = None
        self.drag = None
        self.minimap_geom = None
        self.setup = {"faction": "concord", "map": "standard", "ai": 3}
        self.stars = [(random.random(), random.random(), random.random()) for _ in range(180)]
        self.globe = None
        self._caption = None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self):
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            self.surf = pygame.display.get_surface()
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)

    def quit(self):
        self.running = False

    def show_toast(self, msg, color=theme.TEXT):
        self.toast = (msg, pygame.time.get_ticks() + 2800, color)

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------
    def open_dialog(self, d):
        self.dialogs.append(d)

    def close_dialog(self, d):
        if d in self.dialogs:
            self.dialogs.remove(d)

    def open_base(self, base):
        self.dialogs = [d for d in self.dialogs if not isinstance(d, BaseDialog)]
        self.open_dialog(BaseDialog(self, base))

    # ------------------------------------------------------------------
    # Game lifecycle
    # ------------------------------------------------------------------
    def start_game(self):
        cfg = self.setup
        self.game = Game(cfg["faction"], cfg["ai"], cfg["map"])
        self._enter_game()
        self.open_dialog(TechDialog(self))
        self.show_toast("Planetfall! Found your first base with a Colony Pod (B). Press F1 for help.")

    def _enter_game(self):
        self.view = MapView(self.game)
        self.dialogs = []
        self.selected = None
        self.waited = set()
        self.state = "game"
        self._layout()
        units = self.game.player_units(self.game.human_id)
        bases = self.game.player_bases(self.game.human_id)
        if units:
            self.view.center_on(units[0].x, units[0].y)
        elif bases:
            self.view.center_on(bases[0].x, bases[0].y)
        self.select_next()

    def to_main_menu(self):
        self.state = "menu"
        self.dialogs = []
        self.game = None

    def list_saves(self):
        if not os.path.isdir(SAVE_DIR):
            return []
        files = [f for f in os.listdir(SAVE_DIR) if f.endswith(".sav")]
        files.sort(key=lambda f: -os.path.getmtime(os.path.join(SAVE_DIR, f)))
        return files

    def save_game(self, name):
        if not self.game:
            return
        os.makedirs(SAVE_DIR, exist_ok=True)
        with open(os.path.join(SAVE_DIR, name), "wb") as fh:
            pickle.dump(self.game, fh)

    def quick_save(self):
        self.save_game("quicksave.sav")
        self.dialogs = [d for d in self.dialogs if not isinstance(d, GameMenuDialog)]
        self.show_toast("Game saved.")

    def quick_load(self):
        if "quicksave.sav" in self.list_saves():
            self.load_game("quicksave.sav")
        else:
            self.show_toast("No quicksave found.", theme.WARN)

    def load_game(self, name):
        try:
            with open(os.path.join(SAVE_DIR, name), "rb") as fh:
                self.game = pickle.load(fh)
        except Exception as exc:  # corrupt or incompatible save
            self.show_toast(f"Could not load {name}: {exc}", theme.WARN)
            return
        self._enter_game()
        self.show_toast(f"Loaded {name}.")

    def _layout(self):
        w, h = self.surf.get_size()
        if self.view:
            self.view.rect = pygame.Rect(0, TOP_H, w - SIDE_W, h - TOP_H)
            self.view.clamp()

    # ------------------------------------------------------------------
    # Unit selection & orders
    # ------------------------------------------------------------------
    def select_unit(self, u):
        self.selected = u
        self.goto_mode = False
        if u and self.view and not self.view.is_on_screen(u.x, u.y):
            self.view.center_on(u.x, u.y)

    def select_next(self):
        game = self.game
        units = game.units_needing_orders(game.human_id)
        pending = [u for u in units if u.id not in self.waited]
        if not pending and units:
            self.waited.clear()
            pending = units
        if not pending:
            self.selected = None if not self.selected or self.selected.id not in game.units else self.selected
            if self.selected and self.selected.moves_left <= 0:
                self.selected = None
            return
        if self.selected and self.selected.id in game.units:
            s = self.selected
            pending.sort(key=lambda u: game.world.distance(u.x, u.y, s.x, s.y))
        self.select_unit(pending[0])

    def show_events(self):
        if self.game and self.game.events and not any(isinstance(d, EventDialog) for d in self.dialogs):
            self.open_dialog(EventDialog(self))

    def _after_action(self):
        u = self.selected
        if u is None or u.id not in self.game.units or u.moves_left <= 0 or u.orders:
            self.select_next()
        self.show_events()
        self._check_game_over()

    def _check_game_over(self):
        if self.game.winner and not any(isinstance(d, GameOverDialog) for d in self.dialogs) \
                and not getattr(self.game, "_winner_shown", False):
            self.game._winner_shown = True
            self.open_dialog(GameOverDialog(self))

    def move_selected(self, direction):
        u = self.selected
        if not u or u.id not in self.game.units:
            return
        u.orders = None if u.orders in ("goto", "explore", "auto", "fortify", "sentry") else u.orders
        dest = self.game.world.step(u.x, u.y, direction)
        if dest is None:
            self.show_toast("That's the edge of the world.", theme.WARN)
            return
        res = self.game.move_unit(u, *dest)
        if res.startswith("blocked"):
            self.show_toast(res.split(":", 1)[1].capitalize(), theme.WARN)
            if u.moves_left <= 0:
                self._after_action()
            return
        if u.id in self.game.units and not self.view.is_on_screen(u.x, u.y, 3):
            self.view.center_on(u.x, u.y)
        self._after_action()

    def act_found(self):
        u = self.selected
        if not u:
            return
        ok, why = self.game.can_found_base(u)
        if not ok:
            self.show_toast(why, theme.WARN)
            return
        b = self.game.found_base(u)
        self.selected = None
        self.open_base(b)
        self._after_action()
        waiting = len(self.game.units_needing_orders(self.game.human_id))
        if waiting:
            self.show_toast(f"{b.name} founded. {waiting} unit(s) still await orders - Tab cycles through them.")

    def act_fortify(self):
        if self.selected:
            self.game.fortify(self.selected)
            self._after_action()

    def act_sentry(self):
        if self.selected:
            self.game.sentry(self.selected)
            self._after_action()

    def act_skip(self):
        if self.selected:
            self.selected.moves_left = 0
            self._after_action()

    def act_wait(self):
        if self.selected:
            self.waited.add(self.selected.id)
            self.select_next()

    def act_explore(self):
        from game import ai
        u = self.selected
        if u:
            u.orders = "explore"
            if not ai.act_explore(self.game, u):
                u.orders = None
                self.show_toast("Nothing left to explore.", theme.WARN)
            self._after_action()

    def act_automate(self):
        from game import ai
        u = self.selected
        if u and u.type.former:
            u.orders = "auto"
            ai.act_former(self.game, u)
            self._after_action()

    def act_terraform(self, kind):
        u = self.selected
        if not u or not u.type.former:
            return
        if self.game.start_terraform(u, kind):
            self._after_action()
        else:
            self.show_toast(f"Cannot {TERRAFORMS[kind].name.lower()} here.", theme.WARN)

    def act_board(self):
        u = self.selected
        if not u:
            return
        for t in self.game.units_at(u.x, u.y):
            if t.owner == u.owner and self.game.board(u, t):
                self.show_toast(f"{u.name} boards the {t.name}. Move the transport to carry it.")
                self._after_action()
                return
        self.show_toast("No transport with room here.", theme.WARN)

    def act_disband(self):
        u = self.selected
        if u:
            self.game.kill_unit(u)
            self.selected = None
            self.select_next()

    def act_goto_mode(self):
        if self.selected:
            self.goto_mode = True
            self.show_toast("Click a destination (right-click also works).")

    def goto(self, tile):
        u = self.selected
        if not u:
            return
        if self.game.set_goto(u, *tile):
            self.game.follow_path(u)
            if u.id in self.game.units and not u.path and u.orders == "goto":
                u.orders = None
            self._after_action()
        else:
            self.show_toast("No route to that destination.", theme.WARN)
        self.goto_mode = False

    def end_turn(self):
        game = self.game
        techs_before = set(game.human.techs)
        projects_before = set(game.projects_built)
        game.end_turn()
        new_techs = sorted(game.human.techs - techs_before)
        new_projects = [k for k in game.projects_built if k not in projects_before
                        and game.project_owner(k) == game.human_id]
        self.waited.clear()
        if game.turn % 10 == 0:
            self.save_game("autosave.sav")
        self.view.minimap_dirty = True
        self.selected = None
        self.select_next()
        if game.human.current_tech is None and game.available_techs(game.human_id) and game.human.alive:
            self.open_dialog(TechDialog(self))
        if new_techs or new_projects:
            self.open_dialog(DiscoveryDialog(self, new_techs, new_projects))
        if game.proposals:
            self.open_dialog(ProposalDialog(self))
        self.show_events()
        self.show_toast(f"Mission Year {game.year}")
        self._check_game_over()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self.surf = pygame.display.get_surface()
            self._layout()
            return
        if self.state != "game":
            self.handle_menu_event(event)
            return
        if event.type == pygame.KEYDOWN:
            self.handle_key(event)
        elif event.type == pygame.MOUSEWHEEL:
            if self.dialogs:
                self.dialogs[-1].on_wheel(event.y)
            elif self.view.rect.collidepoint(pygame.mouse.get_pos()):
                self.view.zoom(1 if event.y > 0 else -1, pygame.mouse.get_pos())
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (4, 5):
                return
            if event.button == 1:
                if self.ui.click(event.pos):
                    return
                if self.dialogs:
                    return
                if self.minimap_geom and self.view.minimap_click(event.pos, *self.minimap_geom):
                    return
                if self.view.rect.collidepoint(event.pos):
                    self.drag = [event.pos, event.pos, False]
            elif event.button == 3 and not self.dialogs:
                tile = self.view.screen_to_tile(event.pos)
                if tile and self.selected:
                    self.goto(tile)
            elif event.button == 2 and not self.dialogs:
                self.drag = [event.pos, event.pos, True]
        elif event.type == pygame.MOUSEMOTION:
            if self.drag:
                start, last, moved = self.drag
                if moved or abs(event.pos[0] - start[0]) + abs(event.pos[1] - start[1]) > 6:
                    self.view.pan(event.pos[0] - last[0], event.pos[1] - last[1])
                    self.drag = [start, event.pos, True]
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button in (1, 2) and self.drag:
                start, _, moved = self.drag
                self.drag = None
                if not moved and event.button == 1:
                    tile = self.view.screen_to_tile(event.pos)
                    if tile:
                        self.map_click(tile)

    def map_click(self, tile):
        game = self.game
        if self.goto_mode and self.selected:
            self.goto(tile)
            return
        base = game.base_at(*tile)
        if base and base.owner == game.human_id:
            self.open_base(base)
            return
        mine = [u for u in game.units_at(*tile) if u.owner == game.human_id]
        if mine:
            if self.selected in mine and len(mine) > 1:
                i = mine.index(self.selected)
                u = mine[(i + 1) % len(mine)]
            else:
                u = next((m for m in mine if not m.carried_by), mine[0])
            if u.orders in ("fortify", "sentry"):
                u.orders = None
                u.fortified = False
            self.select_unit(u)

    def handle_key(self, event):
        key = event.key
        mods = event.mod
        if self.dialogs:
            d = self.dialogs[-1]
            if not d.on_key(event) and key == pygame.K_ESCAPE:
                d.close()
            return
        ctrl = mods & pygame.KMOD_CTRL
        if ctrl and key == pygame.K_s:
            self.quick_save()
            return
        if ctrl and key == pygame.K_l:
            self.quick_load()
            return
        if key == pygame.K_ESCAPE:
            if self.goto_mode:
                self.goto_mode = False
            else:
                self.open_dialog(GameMenuDialog(self))
            return
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.end_turn()
            return
        fkeys = {pygame.K_F1: HelpDialog, pygame.K_F2: EconomyDialog, pygame.K_F3: TechDialog,
                 pygame.K_F6: DatalinksDialog, pygame.K_F7: SocietyDialog,
                 pygame.K_F4: DiplomacyDialog, pygame.K_F5: StatusDialog}
        if key in fkeys:
            self.open_dialog(fkeys[key](self))
            return
        if key == pygame.K_TAB or key == pygame.K_PERIOD:
            self.select_next()
            return
        if key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            self.view.zoom(1)
            return
        if key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.view.zoom(-1)
            return
        u = self.selected
        if key in MOVE_KEYS:
            direction = MOVE_KEYS[key]
            if u and u.id in self.game.units:
                self.move_selected(direction)
            else:
                px, py = PAN_VECTORS[direction]
                self.view.pan(px * self.view.tw * 2, py * self.view.tw)
            return
        if not u or u.id not in self.game.units:
            return
        if key == pygame.K_c:
            self.view.center_on(u.x, u.y)
        elif key == pygame.K_b:
            self.act_found()
        elif key == pygame.K_h:
            self.act_fortify()
        elif key == pygame.K_l:
            self.act_sentry()
        elif key == pygame.K_SPACE:
            self.act_skip()
        elif key == pygame.K_w:
            self.act_wait()
        elif key == pygame.K_e:
            self.act_explore()
        elif key == pygame.K_g:
            self.act_goto_mode()
        elif key == pygame.K_a:
            self.act_automate()
        elif key == pygame.K_DELETE:
            self.act_disband()
        elif key == pygame.K_o:
            self.act_board()
        elif u.type.former:
            for tf in TERRAFORMS.values():
                if key == pygame.key.key_code(tf.key):
                    self.act_terraform(tf.id)
                    return

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def update_caption(self):
        """Window title: the game's name, plus your faction and the date while playing."""
        if self.state == "game" and self.game:
            p = self.game.human
            caption = f"{GAME_TITLE}  -  {p.name}  -  Mission Year {self.game.year}"
        else:
            caption = f"{GAME_TITLE}  -  Planetfall is only the beginning"
        if caption != self._caption:
            pygame.display.set_caption(caption)
            self._caption = caption

    def draw(self):
        self.update_caption()
        mouse = pygame.mouse.get_pos()
        self.ui.begin(mouse)
        if self.state == "game":
            self.draw_game(mouse)
        elif self.state == "setup":
            self.draw_setup(mouse)
        else:
            self.draw_menu(mouse)
        tip = self.ui.hovered_tooltip()
        if tip:
            lines = theme.wrap(tip, 17, 320)
            w = max(theme.font(17).size(l)[0] for l in lines) + 12
            h = len(lines) * 18 + 8
            x = min(mouse[0] + 14, self.surf.get_width() - w - 4)
            y = min(mouse[1] + 18, self.surf.get_height() - h - 4)
            theme.panel(self.surf, (x, y, w, h), (10, 14, 18), theme.PANEL_BORDER, radius=3)
            for i, l in enumerate(lines):
                theme.text(self.surf, l, (x + 6, y + 4 + i * 18), 17)

    def draw_game(self, mouse):
        surf = self.surf
        game = self.game
        self._layout()
        surf.fill(theme.BG)
        ticks = pygame.time.get_ticks()
        self.hover_tile = self.view.screen_to_tile(mouse) if not self.dialogs else None
        if self.selected and self.selected.id not in game.units:
            self.selected = None
        path = None
        if self.selected and self.hover_tile and (self.goto_mode or pygame.mouse.get_pressed()[2] or
                                                  pygame.key.get_mods() & pygame.KMOD_SHIFT):
            key = (self.selected.id, self.selected.x, self.selected.y, self.hover_tile)
            if self.path_cache[0] != key:
                self.path_cache = (key, find_path(game, self.selected, *self.hover_tile), None)
            path = self.path_cache[1]
        elif self.selected and self.selected.orders == "goto" and self.selected.path:
            path = self.selected.path
        self.view.draw(surf, game.human_id, self.selected, self.hover_tile, path, ticks)
        self.draw_log(surf)
        self.draw_topbar(surf)
        self.draw_sidebar(surf, ticks)
        if self.toast and ticks < self.toast[1]:
            msg, _, col = self.toast
            img = theme.font(24, True).render(msg, True, col)
            r = img.get_rect(midtop=(self.view.rect.centerx, self.view.rect.y + 12))
            theme.panel(surf, r.inflate(24, 12), (10, 14, 18), theme.PANEL_BORDER, alpha=220)
            surf.blit(img, r)
        for d in list(self.dialogs):
            if d is self.dialogs[-1]:
                self.ui.buttons = []  # modal: only the top dialog is clickable
            d.draw(surf, self.ui)

    def draw_topbar(self, surf):
        game = self.game
        p = game.human
        w = surf.get_width()
        pygame.draw.rect(surf, theme.PANEL, (0, 0, w, TOP_H))
        pygame.draw.line(surf, theme.PANEL_BORDER, (0, TOP_H - 1), (w, TOP_H - 1))
        bx = w - 8
        for label, cb, tip in reversed((
                ("Research", lambda: self.open_dialog(TechDialog(self)), "Choose research (F3)"),
                ("Energy", lambda: self.open_dialog(EconomyDialog(self)), "Energy allocation and base list (F2)"),
                ("Society", lambda: self.open_dialog(SocietyDialog(self)), "Choose how your faction governs itself (F7)"),
                ("Diplomacy", lambda: self.open_dialog(DiplomacyDialog(self)), "Relations with other factions (F4)"),
                ("Status", lambda: self.open_dialog(StatusDialog(self)), "Scores and victory conditions (F5)"),
                ("Datalinks", lambda: self.open_dialog(DatalinksDialog(self)),
                 "Encyclopedia: every unit, facility, terrain, technology and rule explained (F6)"),
                ("Help", lambda: self.open_dialog(HelpDialog(self)), "Controls and rules (F1)"),
                ("Menu", lambda: self.open_dialog(GameMenuDialog(self)), "Save, load, quit (Esc)"))):
            bw = theme.font(18).size(label)[0] + 18
            bx -= bw + 4
            self.ui.button(surf, (bx, 4, bw, TOP_H - 8), label, cb, tooltip=tip, size=18)
        surf.set_clip((0, 0, bx - 8, TOP_H))  # status text never runs under the buttons
        x = 10
        pygame.draw.rect(surf, p.color, (x, 9, 16, 16))
        x += 24
        r = theme.text(surf, p.name, (x, 9), 22, p.color, bold=True)
        x = r.right + 18
        r = theme.text(surf, f"M.Y. {game.year}  (turn {game.turn})", (x, 10), 20)
        x = r.right + 18
        bases = game.player_bases(p.id)
        reps = [b.last_report or game.base_report(b) for b in bases]
        income = sum(rp["econ"] for rp in reps) - sum(rp["upkeep"] for rp in reps) + sum(
            rp["minerals_net"] for b, rp in zip(bases, reps) if b.production == ("special", "stockpile"))
        r = theme.text(surf, f"Credits {p.credits} ({income:+d})", (x, 10), 20, theme.ENERGY)
        self.ui.hotspot(r, "Energy credits in reserve, and the change per turn (economy output minus facility "
                           "upkeep). Spend credits to rush-buy production in a base.")
        x = r.right + 18
        labs = sum(rp["labs"] for rp in reps)
        if p.current_tech:
            cost = game.tech_cost(p.id, p.current_tech)
            turns = -(-(cost - p.research_progress) // labs) if labs > 0 else "--"
            rt = f"{TECHS[p.current_tech].name} {p.research_progress}/{cost} ({turns}t)"
        else:
            rt = "Research: none!"
        r = theme.text(surf, rt, (x, 10), 20, (130, 190, 250))
        self.ui.hotspot(r, f"Current research: progress / cost, and turns left at {labs} labs per turn. "
                           "Click Research (F3) to change it.")
        x = r.right + 18
        r = theme.text(surf, f"Econ {p.alloc[0] * 10}%  Psych {p.alloc[1] * 10}%  Labs {p.alloc[2] * 10}%", (x, 10),
                       18, theme.TEXT_DIM)
        self.ui.hotspot(r, "How your energy is split: Economy (credits), Psych (keeps citizens happy) and Labs "
                           "(research). Change it on the Energy screen (F2).")
        surf.set_clip(None)

    def draw_log(self, surf):
        game = self.game
        hid = game.human_id
        msgs = [m for m in game.log if (m[1] is None or m[1] == hid) and m[0] >= game.turn - 1][-7:]
        if not msgs:
            return
        x = self.view.rect.x + 8
        lh = 19
        y = self.view.rect.bottom - 8 - lh * len(msgs)
        w = min(620, self.view.rect.width - 16)
        theme.panel(surf, (x - 4, y - 4, w, lh * len(msgs) + 8), (0, 0, 0), None, alpha=140)
        for turn, _pid, txt, pos in msgs:
            col = theme.TEXT if turn >= game.turn - 1 else theme.TEXT_DIM
            if turn < game.turn:
                col = theme.TEXT_DIM
            r = theme.text(surf, txt[:95], (x, y), 18, col)
            if pos:
                self.ui.buttons.append(Button(r, "", lambda p=pos: self.view.center_on(*p), tooltip="Click to show on map"))
            y += lh

    def draw_sidebar(self, surf, ticks):
        game = self.game
        w, h = surf.get_size()
        x0 = w - SIDE_W
        pygame.draw.rect(surf, theme.PANEL, (x0, TOP_H, SIDE_W, h - TOP_H))
        pygame.draw.line(surf, theme.PANEL_BORDER, (x0, TOP_H), (x0, h))
        mm_rect = pygame.Rect(x0 + 8, TOP_H + 8, SIDE_W - 16, 150)
        pygame.draw.rect(surf, (0, 0, 0), mm_rect)
        self.minimap_geom = self.view.draw_minimap(surf, mm_rect, game.human_id)
        x = x0 + 12
        y = mm_rect.bottom + 10
        u = self.selected
        if u and u.id in game.units:
            y = self._unit_panel(surf, u, x, y)
        else:
            y = self._pending_panel(surf, x, y)
        # Tile info
        tile = self.hover_tile or ((u.x, u.y) if u else None)
        end_y = h - 60
        if tile and y < end_y - 80:
            self._tile_panel(surf, tile, x, y, end_y)
        # End turn
        pending = game.units_needing_orders(game.human_id)
        ready = not pending
        pulse = ready and (ticks // 500) % 2 == 0
        label = "End Turn  [Enter]" if ready else f"End Turn ({len(pending)} waiting)"
        self.ui.button(surf, (x0 + 10, h - 50, SIDE_W - 20, 40), label, self.end_turn, selected=pulse, size=22)

    def _pending_panel(self, surf, x, y):
        """List of units still waiting for orders, each clickable."""
        game = self.game
        pending = game.units_needing_orders(game.human_id)
        if not pending:
            theme.text(surf, "All units have orders.", (x, y), 19, theme.GOOD)
            y += 22
            theme.text(surf, "Press Enter to end the turn.", (x, y), 17, theme.TEXT_DIM)
            return y + 26
        theme.text(surf, f"{len(pending)} unit(s) awaiting orders", (x, y), 19, theme.ACCENT, bold=True)
        y += 24
        for u in pending[:8]:
            b = game.base_at(u.x, u.y)
            where = f"in {b.name}" if b else f"at ({u.x},{u.y})"
            self.ui.button(surf, (x - 2, y, SIDE_W - 24, 24), f"{u.name}  {where}", lambda u=u: self.select_unit(u),
                           size=17, tooltip=describe.unit_tooltip(u.type) + "\nClick to select it.")
            y += 27
        if len(pending) > 8:
            theme.text(surf, f"... and {len(pending) - 8} more (Tab)", (x, y), 16, theme.TEXT_DIM)
            y += 20
        return y + 6

    def _unit_panel(self, surf, u, x, y):
        game = self.game
        owner = game.players[u.owner]
        r = theme.text(surf, u.name, (x, y), 22, owner.color, bold=True)
        role = lore.UNITS.get(u.type_id, {}).get("role", "")
        theme.text(surf, role, (r.right + 8, y + 3), 17, theme.TEXT_DIM)
        self.ui.hotspot(r, describe.unit_tooltip(u.type))
        y += 22
        r = theme.text(surf, f"{u.morale_name}   Attack {u.type.attack}  Defense {u.type.defense}", (x, y), 18,
                       theme.TEXT)
        self.ui.hotspot(r, f"Morale: {u.morale_name} (each level adds 12.5% strength; win fights to gain more). "
                           f"Attack is used when this unit strikes, Defense when it is attacked. Fights with native "
                           f"life use psi strength instead (see Datalinks).")
        y += 20
        theme.bar(surf, (x, y + 3, 120, 9), u.hp / 10, (80, 220, 80))
        mv = u.moves_left / MOVE_POINTS
        mvs = f"{mv:.0f}" if u.moves_left % MOVE_POINTS == 0 else f"{mv:.1f}"
        theme.text(surf, f"Moves {mvs}/{game.full_moves(u) // MOVE_POINTS}", (x + 130, y), 18, theme.TEXT_DIM)
        y += 18
        status = u.orders or "ready"
        if u.terraform:
            status = f"{TERRAFORMS[u.terraform[0]].name} ({u.terraform[1]} turns)"
        if u.carried_by:
            status = "aboard transport"
        if u.cargo:
            status += f", carrying {len(u.cargo)}"
        home = game.bases.get(u.home)
        theme.text(surf, f"{status}" + (f"  | home: {home.name}" if home else ""), (x, y), 17, theme.TEXT_DIM)
        y += 22
        if u.owner != game.human_id:
            return y
        acts = []
        if u.type.colony:
            acts.append(("Found Base [B]", self.act_found, game.can_found_base(u)[0]))
        if u.type.former:
            for tf in game.terraform_options(u):
                acts.append((f"{tf.name} [{tf.key.upper()}]", lambda k=tf.id: self.act_terraform(k), True))
            acts.append(("Automate [A]", self.act_automate, True))
        if u.type.domain == "land" and not u.carried_by and any(
                t.type.capacity and t.owner == u.owner and len(t.cargo) < t.type.capacity for t in game.units_at(u.x, u.y)):
            acts.append(("Board [O]", self.act_board, True))
        acts += [("Fortify [H]", self.act_fortify, True), ("Sentry [L]", self.act_sentry, True),
                 ("Explore [E]", self.act_explore, True), ("Go to [G]", self.act_goto_mode, True),
                 ("Wait [W]", self.act_wait, True), ("Skip [Space]", self.act_skip, True),
                 ("Disband [Del]", self.act_disband, True), ("Next unit [Tab]", self.select_next, True)]
        bw = (SIDE_W - 30) // 2
        for i, (label, cb, en) in enumerate(acts):
            bx = x - 2 + (i % 2) * (bw + 6)
            name = label.split(" [")[0]
            tip = ACTION_TIPS.get(name)
            if tip is None:
                imp = next((v for k, v in lore.IMPROVEMENTS.items() if v[0] == name), None)
                tip = imp[1] if imp else None
            if name == "Found Base" and not en:
                tip = game.can_found_base(u)[1] + " " + ACTION_TIPS["Found Base"]
            self.ui.button(surf, (bx, y, bw, 24), label, cb, enabled=en, size=17, tooltip=tip)
            if i % 2 == 1:
                y += 28
        if len(acts) % 2 == 1:
            y += 28
        return y + 6

    def _tile_panel(self, surf, tile, x, y, end_y):
        game = self.game
        hid = game.human_id
        tx, ty = tile
        w = SIDE_W - 24
        pygame.draw.line(surf, theme.PANEL_BORDER, (x - 4, y), (x + SIDE_W - 20, y))
        y += 6
        if not game.is_explored(hid, tx, ty):
            theme.text(surf, "Unexplored", (x, y), 19, theme.TEXT_DIM)
            theme.text_block(surf, "Send a unit to see what's here. Scouts can explore automatically (E).",
                             (x, y + 22, w, 60), 16, theme.TEXT_DIM)
            return
        t = game.world.tiles[tx][ty]
        theme.text(surf, t.terrain_name(), (x, y), 19, theme.TEXT, bold=True)
        y += 20
        theme.text(surf, f"Elevation {t.elevation}m", (x, y), 16, theme.TEXT_DIM)
        y += 18
        n, m, e = game.tile_yield(t, hid, (tx, ty) in game.base_pos)
        for kind, rr in theme.yields(surf, (x, y), n, m, e, size=18, words=True, gap=8):
            self.ui.hotspot(rr, lore.RESOURCES[kind]["name"] + ": " + lore.RESOURCES[kind]["short"])
        y += 22
        imps = describe.improvement_names(t)
        if t.special:
            imps.append(lore.SPECIALS[t.special][0])
        if t.supply_pod:
            imps.append("Supply Pod")
        if imps:
            theme.text(surf, "Here: " + ", ".join(imps), (x, y), 16, theme.GOLD)
            y += 18
        if t.owner is not None:
            theme.text(surf, f"Territory of the {game.players[t.owner].name}", (x, y), 16, game.players[t.owner].color)
            y += 18
        b = game.base_at(tx, ty)
        if b:
            theme.text(surf, f"Base: {b.name} (size {b.pop})", (x, y), 18, game.players[b.owner].color, bold=True)
            y += 20
        if game.is_visible(hid, tx, ty):
            for u in game.units_at(tx, ty)[:4]:
                if y > end_y - 18:
                    break
                o = game.players[u.owner]
                txt = f"{u.name} ({o.name if not o.is_native else 'native life'})"
                if self.selected and u.owner != hid and self.selected.owner == hid and game.can_attack(self.selected) \
                        and game.world.distance(u.x, u.y, self.selected.x, self.selected.y) == 1:
                    txt += f"  win {int(game.combat_odds(self.selected, tx, ty) * 100)}%"
                rr = theme.text(surf, txt, (x, y), 16, o.color)
                self.ui.hotspot(rr, describe.unit_tooltip(u.type))
                y += 18
        # Description of the land itself
        y += 4
        for para in describe.tile_description(t)[:2] + [describe.best_use_hint(t)]:
            if y > end_y - 36:
                break
            y = theme.text_block(surf, para, (x, y, w, end_y - y), 15, theme.TEXT_DIM, 0) + 4

    # ------------------------------------------------------------------
    # Menus
    # ------------------------------------------------------------------
    def handle_menu_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.ui.click(event.pos)
        elif event.type == pygame.KEYDOWN:
            if self.dialogs:
                d = self.dialogs[-1]
                if not d.on_key(event) and event.key == pygame.K_ESCAPE:
                    d.close()
            elif event.key == pygame.K_ESCAPE:
                if self.state == "setup":
                    self.state = "menu"
                else:
                    self.running = False
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.state == "setup":
                    self.start_game()
                else:
                    self.state = "setup"

    def _draw_space(self, surf):
        w, h = surf.get_size()
        surf.fill((4, 6, 14))
        t = pygame.time.get_ticks() / 1000
        for sx, sy, b in self.stars:
            c = int(120 + 120 * b * (0.7 + 0.3 * math.sin(t * (1 + b) + sx * 20)))
            surf.set_at((int(sx * w), int(sy * h)), (c, c, min(255, c + 20)))
        # Alpha Centauri A and B, far away
        for (fx, fy, rad, col) in ((0.12, 0.16, 5, (255, 236, 190)), (0.15, 0.13, 3, (255, 200, 150))):
            for i in range(6, 0, -1):
                glow = pygame.Surface((rad * 8 * 2, rad * 8 * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*col, 12), (rad * 8, rad * 8), rad * i * 1.3)
                surf.blit(glow, (fx * w - rad * 8, fy * h - rad * 8))
            pygame.draw.circle(surf, col, (int(fx * w), int(fy * h)), rad)
        size = int(min(w, h) * 0.78)
        if self.globe is None or self.globe.d != size:
            from .globe import Globe
            self.globe = Globe(size)
        self.globe.draw(surf, (int(w * 0.8), int(h * 0.78)), (t / 90) % 1.0)

    def draw_menu(self, mouse):
        surf = self.surf
        self._draw_space(surf)
        w, h = surf.get_size()
        theme.text(surf, "NEW CIVILIZATION", (w // 2, h // 4), 84, theme.ACCENT, bold=True, center=True)
        theme.text(surf, "Planetfall is only the beginning.", (w // 2, h // 4 + 58), 26, theme.TEXT_DIM, center=True)
        bw, bh = 280, 44
        y = h // 2 - 20
        for label, cb in (("New Game", lambda: setattr(self, "state", "setup")),
                          ("Load Game", lambda: self.open_dialog(LoadDialog(self))),
                          ("Quit", self.quit)):
            self.ui.button(surf, (w // 2 - bw // 2, y, bw, bh), label, cb, size=26)
            y += bh + 12
        for d in list(self.dialogs):
            if d is self.dialogs[-1]:
                self.ui.buttons = []
            d.draw(surf, self.ui)

    def draw_setup(self, mouse):
        surf = self.surf
        self._draw_space(surf)
        w, h = surf.get_size()
        pw, ph = min(1000, w - 40), min(640, h - 40)
        r = pygame.Rect((w - pw) // 2, (h - ph) // 2, pw, ph)
        theme.panel(surf, r, theme.PANEL, theme.PANEL_BORDER, alpha=235)
        theme.text(surf, "Choose Your Faction", (r.x + 20, r.y + 14), 32, theme.ACCENT, bold=True)
        y = r.y + 60
        for f in FACTION_LIST:
            sel = self.setup["faction"] == f.id
            b = self.ui.button(surf, (r.x + 20, y, 330, 38), "", lambda fid=f.id: self.setup.__setitem__("faction", fid),
                               selected=sel)
            pygame.draw.rect(surf, f.color, (b.rect.x + 8, b.rect.y + 9, 20, 20))
            theme.text(surf, f.name, (b.rect.x + 38, b.rect.y + 11), 22, theme.TEXT, bold=sel)
            y += 44
        f = FACTIONS[self.setup["faction"]]
        dx = r.x + 380
        theme.text(surf, f.name, (dx, r.y + 62), 30, f.color, bold=True)
        theme.text(surf, f.leader, (dx, r.y + 94), 22, theme.TEXT_DIM)
        yb = theme.text_block(surf, f.description, (dx, r.y + 124, r.right - dx - 20, 50), 20, theme.GOLD)
        theme.text_block(surf, lore.FACTION_LORE.get(f.id, ""), (dx, yb + 6, r.right - dx - 20, 110), 18, theme.TEXT)
        y = r.y + 300
        theme.text(surf, "Planet size", (dx, y), 22, theme.ACCENT, bold=True)
        y += 28
        for i, size in enumerate(MAP_SIZES):
            mw, mh = MAP_SIZES[size]
            self.ui.button(surf, (dx + i * 150, y, 140, 34), f"{size.title()} {mw}x{mh}",
                           lambda s=size: self.setup.__setitem__("map", s), selected=self.setup["map"] == size, size=19)
        y += 56
        theme.text(surf, "Rival factions", (dx, y), 22, theme.ACCENT, bold=True)
        y += 28
        self.ui.button(surf, (dx, y, 34, 34), "-", lambda: self.setup.__setitem__("ai", max(1, self.setup["ai"] - 1)))
        theme.text(surf, self.setup["ai"], (dx + 60, y + 7), 26, theme.TEXT, bold=True, center=False)
        self.ui.button(surf, (dx + 90, y, 34, 34), "+", lambda: self.setup.__setitem__("ai", min(6, self.setup["ai"] + 1)))
        y += 60
        theme.text_block(surf, "Victory: Conquest (eliminate all rivals) or Transcendence (research Transcendence and "
                               "complete the Ascension Engine).", (dx, y, r.right - dx - 20, 60), 19, theme.TEXT_DIM)
        self.ui.button(surf, (r.right - 200, r.bottom - 60, 180, 44), "Start  [Enter]", self.start_game, size=24)
        self.ui.button(surf, (r.right - 340, r.bottom - 60, 120, 44), "Back", lambda: setattr(self, "state", "menu"),
                       size=24)
