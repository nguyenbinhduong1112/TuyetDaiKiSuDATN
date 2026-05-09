import math


def haversine_km(point_a, point_b):
    lat1, lon1 = point_a
    lat2, lon2 = point_b
    radius_km = 6371.0
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))
    rlat1 = math.radians(float(lat1))
    rlat2 = math.radians(float(lat2))
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return radius_km * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def route_distance_km(locations, route_indices=None, close_loop=False, detour_factor=1.3):
    route = list(route_indices) if route_indices else list(range(len(locations)))
    if len(route) < 2:
        return 0.0

    if close_loop and route[-1] != route[0]:
        route = route + [route[0]]

    total = 0.0
    for prev_idx, next_idx in zip(route, route[1:]):
        total += haversine_km(locations[prev_idx], locations[next_idx])
    return total * detour_factor


def _nearest_neighbor_route(locations, start=0):
    if len(locations) <= 1:
        return [0] if locations else []

    unvisited = set(range(len(locations)))
    unvisited.remove(start)
    route = [start]

    while unvisited:
        current = route[-1]
        next_idx = min(unvisited, key=lambda idx: haversine_km(locations[current], locations[idx]))
        route.append(next_idx)
        unvisited.remove(next_idx)

    return route


def _two_opt_closed_route(locations, closed_route):
    if len(closed_route) <= 4:
        return closed_route

    best = list(closed_route)
    best_distance = route_distance_km(locations, best, close_loop=False, detour_factor=1.0)
    improved = True

    while improved:
        improved = False
        for i in range(1, len(best) - 2):
            for k in range(i + 1, len(best) - 1):
                candidate = best[:i] + best[i:k + 1][::-1] + best[k + 1:]
                candidate_distance = route_distance_km(locations, candidate, close_loop=False, detour_factor=1.0)
                if candidate_distance + 1e-9 < best_distance:
                    best = candidate
                    best_distance = candidate_distance
                    improved = True
                    break
            if improved:
                break

    return best


def solve_delivery_route(locations, start=0, close_loop=True):
    points = [tuple(point) for point in locations]
    if not points:
        return []
    if len(points) == 1:
        return [0, 0] if close_loop else [0]

    route = _nearest_neighbor_route(points, start=start)
    if close_loop:
        route.append(start)
        return _two_opt_closed_route(points, route)

    return route
