"""Deterministic planner: Google OR-Tools, vehicle routing with time windows.
Each task may have several candidate places; the solver visits at most one per task,
respects opening hours and 'before' deadlines, and minimises travel time.
Tasks that cannot fit are dropped with a reason instead of being silently ignored."""
import math
from dataclasses import dataclass
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

HORIZON = 3 * 1440
PENALTY = 100_000
SPEED = {'car': 22.0, 'foot': 4.8}


@dataclass
class Cand:
    lat: float
    lon: float
    name: str = ''
    intervals: list | None = None  # None = hours unknown


@dataclass
class Task:
    id: str
    title: str
    dur: int
    cands: list
    before: int | None = None
    pin: int | None = None


def hav(a, b):
    r = math.pi / 180
    dl, dn = (b[0] - a[0]) * r, (b[1] - a[1]) * r
    x = math.sin(dl / 2) ** 2 + math.cos(a[0] * r) * math.cos(b[0] * r) * math.sin(dn / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


def estimate(a, b, mode):
    return math.ceil(hav(a, b) * 1.3 / SPEED.get(mode, 22.0) * 60)


def fmt(m):
    m = int(m) % 1440
    return f"{(m // 60) % 12 or 12}:{m % 60:02d} {'am' if m < 720 else 'pm'}"


def _pieces(c, dur, now, before):
    out = []
    for s, e in (c.intervals if c.intervals is not None else [(0, HORIZON)]):
        lo, hi = max(s, now), e - dur
        if before is not None:
            hi = min(hi, before)
        if lo <= hi:
            out.append((lo, hi))
    return out


def build_nodes(now, tasks):
    nodes, dropped = [], []
    for t in tasks:
        idx = [t.pin] if t.pin is not None and 0 <= t.pin < len(t.cands) else range(len(t.cands))
        found = False
        for i in idx:
            p = _pieces(t.cands[i], t.dur, now, t.before)
            if p:
                nodes.append((t, i, p))
                found = True
        if not found:
            why = ('No place for this task is open in time' + (f' before {fmt(t.before)}' if t.before is not None else '')
                   + '. Try another day, a different place, or a later deadline.')
            dropped.append({'task_id': t.id, 'reason': why})
    return nodes, dropped


def points(start, nodes):
    return [start] + [(t.cands[i].lat, t.cands[i].lon) for t, i, _ in nodes]


def plan(start, now, tasks, mode='car', matrix=None):
    nodes, dropped = build_nodes(now, tasks)
    res = {'stops': [], 'dropped': dropped, 'travel_min': 0}
    if not nodes:
        return res
    pts = points(start, nodes)
    n = len(pts) + 1
    end = n - 1
    M = [[(matrix[i][j] if matrix and matrix[i][j] is not None else estimate(pts[i], pts[j], mode))
          for j in range(len(pts))] for i in range(len(pts))]
    service = [0] + [t.dur for t, _, _ in nodes] + [0]

    def travel(i, j):
        return 0 if i == end or j == end else M[i][j]

    mgr = pywrapcp.RoutingIndexManager(n, 1, [0], [end])
    rt = pywrapcp.RoutingModel(mgr)
    cost = rt.RegisterTransitCallback(lambda a, b: travel(mgr.IndexToNode(a), mgr.IndexToNode(b)))
    tcb = rt.RegisterTransitCallback(
        lambda a, b: travel(mgr.IndexToNode(a), mgr.IndexToNode(b)) + service[mgr.IndexToNode(a)])
    rt.SetArcCostEvaluatorOfAllVehicles(cost)
    rt.AddDimension(tcb, HORIZON, HORIZON, False, 'T')
    dim = rt.GetDimensionOrDie('T')
    dim.CumulVar(rt.Start(0)).SetRange(now, now)
    groups = {}
    for k, (t, i, p) in enumerate(nodes, start=1):
        idx = mgr.NodeToIndex(k)
        dim.CumulVar(idx).SetRange(p[0][0], p[-1][1])
        for (_, b), (c, _) in zip(p, p[1:]):
            if c - b > 1:
                dim.CumulVar(idx).RemoveInterval(b + 1, c - 1)
        groups.setdefault(t.id, []).append(idx)
    for idxs in groups.values():
        rt.AddDisjunction(idxs, PENALTY, 1)
    sp = pywrapcp.DefaultRoutingSearchParameters()
    sp.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    sp.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    sp.time_limit.seconds = 2
    sol = rt.SolveWithParameters(sp)
    visited, prev = set(), 0
    if sol:
        idx = sol.Value(rt.NextVar(rt.Start(0)))
        while not rt.IsEnd(idx):
            k = mgr.IndexToNode(idx)
            t, ci, pcs = nodes[k - 1]
            arr = sol.Value(dim.CumulVar(idx))
            hi = next((b for a, b in pcs if a <= arr <= b), pcs[-1][1])
            urgent = hi - arr < 45 and hi < HORIZON - t.dur
            binding_deadline = t.before is not None and hi == t.before
            why = 'Nearest next stop'
            if urgent:
                why = ('Early because you need it done by ' + fmt(t.before)) if binding_deadline \
                    else 'Early because it closes at ' + fmt(hi + t.dur)
            res['stops'].append({'task_id': t.id, 'cand': ci, 'arrive': arr, 'depart': arr + t.dur,
                                 'dur': t.dur, 'why': why})
            res['travel_min'] += M[prev][k]
            visited.add(t.id)
            prev = k
            idx = sol.Value(rt.NextVar(idx))
    seen = {d['task_id'] for d in dropped}
    for t in tasks:
        if t.id not in visited and t.id not in seen:
            res['dropped'].append({'task_id': t.id, 'reason':
                'It does not fit before its deadline or closing time together with your other tasks. '
                'Consider skipping it today or moving it to tomorrow.'})
    return res
