"""Run an all-AI game headless and print progress - handy for balancing.

    python tools/simulate.py --seed 3 --turns 300 --map standard --ai 4
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game import ai  # noqa: E402
from game.game import Game  # noqa: E402


def summary(g):
    rows = []
    for p in g.players:
        if p.is_native or not p.alive:
            continue
        bases = g.player_bases(p.id)
        rows.append(f"{p.faction.adjective[:10]:<10} bases {len(bases):>2} pop {sum(b.pop for b in bases):>3} "
                    f"techs {len(p.techs):>2} credits {p.credits:>5} units {len(g.player_units(p.id)):>3}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--turns", type=int, default=300)
    ap.add_argument("--map", default="standard")
    ap.add_argument("--ai", type=int, default=4)
    ap.add_argument("--every", type=int, default=50)
    args = ap.parse_args()
    start = time.time()
    g = Game("concord", num_ai=args.ai, map_size=args.map, seed=args.seed, all_ai=True)
    for _ in range(args.turns):
        ai.take_turn(g, g.players[g.human_id])
        g.end_turn()
        if g.turn % args.every == 0:
            print(f"--- turn {g.turn} ({time.time() - start:.1f}s)")
            print("\n".join(summary(g)))
        if g.winner:
            break
    print(f"=== finished at turn {g.turn}, winner: {g.winner}")
    print("\n".join(summary(g)))
    print("projects:", {k: g.players[g.project_owner(k)].faction.adjective if g.project_owner(k) else None
                        for k in g.projects_built})


if __name__ == "__main__":
    main()
