"""Path finding over the wrapped map."""
import heapq

from .entities import MOVE_POINTS


def find_path(game, unit, tx, ty, max_nodes=6000):
    """A* from the unit to (tx, ty). Returns a list of (x, y) steps (start excluded),
    or None if unreachable. The goal may hold an enemy (so the last step is an attack)."""
    world = game.world
    tx %= world.width
    start = (unit.x, unit.y)
    goal = (tx, ty)
    if start == goal:
        return []
    if not game.path_passable(unit, tx, ty, True):
        return None
    open_heap = [(0, 0, start)]
    came = {start: None}
    cost_so_far = {start: 0}
    expanded = 0
    while open_heap:
        _, g, cur = heapq.heappop(open_heap)
        if cur == goal:
            break
        if g > cost_so_far.get(cur, 1 << 30):
            continue
        expanded += 1
        if expanded > max_nodes:
            return None
        cx, cy = cur
        for nx, ny in world.neighbors(cx, cy):
            nxt = (nx, ny)
            is_goal = nxt == goal
            if not game.path_passable(unit, nx, ny, is_goal):
                continue
            ng = g + game.move_cost(unit, cx, cy, nx, ny)
            if ng < cost_so_far.get(nxt, 1 << 30):
                cost_so_far[nxt] = ng
                came[nxt] = cur
                h = world.distance(nx, ny, tx, ty) * 2
                heapq.heappush(open_heap, (ng + h, ng, nxt))
    if goal not in came:
        return None
    path = []
    node = goal
    while node != start:
        path.append(node)
        node = came[node]
    path.reverse()
    return path


def reachable(game, unit, max_cost):
    """Dijkstra flood from a unit. Returns {(x, y): cost} for passable tiles within max_cost
    movement points (foreign-occupied tiles are excluded)."""
    world = game.world
    start = (unit.x, unit.y)
    dist = {start: 0}
    heap = [(0, start)]
    while heap:
        d, cur = heapq.heappop(heap)
        if d > dist.get(cur, 1 << 30):
            continue
        cx, cy = cur
        for nx, ny in world.neighbors(cx, cy):
            if not game.path_passable(unit, nx, ny, False):
                continue
            nd = d + game.move_cost(unit, cx, cy, nx, ny)
            if nd <= max_cost and nd < dist.get((nx, ny), 1 << 30):
                dist[(nx, ny)] = nd
                heapq.heappush(heap, (nd, (nx, ny)))
    return dist


def turns_for_path(game, unit, path):
    """Rough number of turns needed to walk a path."""
    if not path:
        return 0
    full = unit.type.moves * MOVE_POINTS
    left = unit.moves_left
    turns = 1
    px, py = unit.x, unit.y
    for (x, y) in path:
        c = game.move_cost(unit, px, py, x, y)
        if left >= c:
            left -= c
        elif left == full:
            left = 0
        else:
            turns += 1
            left = full - min(c, full)
        px, py = x, y
    return turns
