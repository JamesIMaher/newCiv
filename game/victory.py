"""Victory conditions.

Each condition is a small function that inspects the game and returns the id of the
winning player or None. New victory types (economic, cultural, ...) are added by
appending to VICTORY_CONDITIONS.
"""


def conquest(game):
    alive = [p for p in game.players if p.alive and not p.is_native]
    if len(alive) == 1:
        return alive[0].id
    return None


def transcendence(game):
    base_id = game.projects_built.get("ascension_engine")
    if base_id is not None:
        return game.project_owner("ascension_engine")
    return None


VICTORY_CONDITIONS = [
    ("Conquest", "Eliminate every rival faction.", conquest),
    ("Transcendence", "Research Transcendence and complete the Ascension Engine.", transcendence),
]


def check_victory(game):
    for name, _desc, fn in VICTORY_CONDITIONS:
        winner = fn(game)
        if winner is not None:
            return winner, name
    return None
