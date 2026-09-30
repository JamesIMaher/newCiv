import os
import pickle
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game import ai  # noqa: E402
from game.entities import MOVE_POINTS  # noqa: E402
from game.game import Game  # noqa: E402
from game.world import FLAT, ROCKY, MOIST  # noqa: E402


@pytest.fixture
def game():
    return Game("concord", num_ai=2, map_size="small", seed=42)


def flatten(game, cx, cy, r=4):
    """Make an area plain moist flat land so tests are independent of map generation."""
    for x, y in game.world.radius(cx, cy, r):
        t = game.world.tiles[x][y]
        t.elevation = 500
        t.rockiness = FLAT
        t.rainfall = MOIST
        t.fungus = False
        t.special = None
        t.supply_pod = False
        t.improvements = set()
        t.owner = None


def clear_units(game):
    for u in list(game.units.values()):
        game.kill_unit(u)


def test_world_generation(game):
    w = game.world
    land = sum(1 for t in w.all_tiles() if t.is_land)
    assert 0.3 < land / (w.width * w.height) < 0.55
    for p in game.players[1:]:
        units = game.player_units(p.id)
        assert units, "every faction starts with units"
        assert all(w.tiles[u.x][u.y].is_land for u in units)


def test_found_base_and_spacing(game):
    human = game.human_id
    pod = next(u for u in game.player_units(human) if u.type.colony)
    b = game.found_base(pod)
    assert b is not None and b.pop == 1
    assert pod.id not in game.units
    other = next(u for u in game.player_units(human) if u.type.colony)
    ok, why = game.can_found_base(other)
    assert not ok and "close" in why


def test_rough_terrain_costs_more(game):
    clear_units(game)
    flatten(game, 10, 10)
    game.world.tiles[11][10].rockiness = ROCKY
    u = game._create_unit("speeder", game.human_id, 10, 10)
    assert game.move_cost(u, 10, 10, 11, 10) == 2 * MOVE_POINTS
    assert game.move_cost(u, 10, 10, 10, 11) == MOVE_POINTS
    game.world.tiles[10][10].improvements.add("road")
    game.world.tiles[10][11].improvements.add("road")
    assert game.move_cost(u, 10, 10, 10, 11) == 1


def test_land_unit_cannot_walk_on_ocean(game):
    clear_units(game)
    flatten(game, 10, 10)
    game.world.tiles[11][10].elevation = -500
    u = game._create_unit("scout", game.human_id, 10, 10)
    assert game.move_unit(u, 11, 10).startswith("blocked")
    assert (u.x, u.y) == (10, 10)


def test_transport_carries_units(game):
    clear_units(game)
    flatten(game, 10, 10)
    for y in range(8, 13):
        game.world.tiles[11][y].elevation = -500
        game.world.tiles[12][y].elevation = -500
    tr = game._create_unit("transport", game.human_id, 11, 10)
    s = game._create_unit("scout", game.human_id, 10, 10)
    assert game.move_unit(s, 11, 10) == "moved"
    assert s.carried_by == tr.id and s.id in tr.cargo
    assert game.move_unit(tr, 12, 10) == "moved"
    assert (s.x, s.y) == (12, 10)
    game.world.tiles[13][10].elevation = 300
    s.moves_left = MOVE_POINTS
    assert game.move_unit(s, 13, 10) == "moved"
    assert s.carried_by is None and s.id not in tr.cargo


def test_peace_blocks_attack_and_war_allows_it(game):
    clear_units(game)
    flatten(game, 10, 10)
    a, b = game.players[1], game.players[2]
    game.make_contact(a.id, b.id)
    att = game._create_unit("impact_rover", a.id, 10, 10)
    game._create_unit("scout", b.id, 11, 10)
    assert "peace" in game.move_unit(att, 11, 10)
    game.declare_war(a.id, b.id)
    assert game.move_unit(att, 11, 10) == "attack"


def test_strong_attacker_usually_wins(game):
    wins = 0
    for i in range(20):
        g = Game("concord", num_ai=1, map_size="small", seed=i)
        clear_units(g)
        flatten(g, 10, 10)
        g.declare_war(1, 2)
        att = g._create_unit("grav_tank", 1, 10, 10)
        g._create_unit("scout", 2, 11, 10)
        g._create_unit("scout", 2, 11, 10)
        g.attack(att, 11, 10)
        if not g.units_at(11, 10):
            wins += 1
    assert wins >= 18  # whole stack dies outside a base


def test_capture_undefended_base(game):
    clear_units(game)
    flatten(game, 10, 10)
    a, b = game.players[1], game.players[2]
    pod = game._create_unit("colony_pod", b.id, 11, 10)
    base = game.found_base(pod)
    base.pop = 3
    game.declare_war(a.id, b.id)
    att = game._create_unit("laser_squad", a.id, 10, 10)
    game.update_territory()
    assert game.move_unit(att, 11, 10) == "captured"
    assert base.owner == a.id and base.pop == 2


def test_production_and_colony_pod_uses_population(game):
    clear_units(game)
    flatten(game, 10, 10)
    pod = game._create_unit("colony_pod", game.human_id, 10, 10)
    base = game.found_base(pod)
    base.pop = 2
    base.production = ("unit", "colony_pod")
    base.minerals = 30
    game._check_production(base)
    assert base.pop == 1
    assert any(u.type.colony for u in game.units_at(10, 10))


def test_research_completes(game):
    p = game.human
    p.current_tech = "biogenetics"
    game._research(p, game.tech_cost(p.id, "biogenetics"))
    assert "biogenetics" in p.techs


def test_terraform_completes(game):
    clear_units(game)
    flatten(game, 10, 10)
    f = game._create_unit("former", game.human_id, 10, 10)
    assert game.start_terraform(f, "farm")
    for _ in range(4):
        game._process_units()
    assert "farm" in game.world.tiles[10][10].improvements
    assert f.terraform is None


def test_restriction_caps_yields(game):
    flatten(game, 10, 10)
    t = game.world.tiles[10][10]
    t.special = "nutrient"
    t.improvements.add("farm")
    assert game.tile_yield(t, 1)[0] == 2
    game.players[1].techs.add("gene_splicing")
    assert game.tile_yield(t, 1)[0] == 4


def test_conquest_victory(game):
    for p in game.players[2:]:
        p.alive = False
    game._end_of_round()
    assert game.winner == (1, "Conquest")


def test_transcendence_victory(game):
    clear_units(game)
    flatten(game, 10, 10)
    pod = game._create_unit("colony_pod", 2, 10, 10)
    base = game.found_base(pod)
    game.players[2].techs.add("transcendence")
    base.production = ("project", "ascension_engine")
    base.minerals = 5000
    game._check_production(base)
    assert game.winner == (2, "Transcendence")


def test_save_load_roundtrip(game):
    ai.take_turn(game, game.human)
    game.end_turn()
    data = pickle.dumps(game)
    g2 = pickle.loads(data)
    assert g2.turn == game.turn
    assert len(g2.units) == len(game.units)
    g2.end_turn()


def test_ai_only_game_runs(game):
    g = Game("helix", num_ai=3, map_size="small", seed=7, all_ai=True)
    for _ in range(80):
        ai.take_turn(g, g.players[1])
        g.end_turn()
    alive = [p for p in g.players if p.alive and not p.is_native]
    assert alive
    assert sum(len(g.player_bases(p.id)) for p in alive) >= len(alive) * 2
    assert all(len(p.techs) >= 3 for p in alive)
