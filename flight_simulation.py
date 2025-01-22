import pandas as pd
import math
from geopy.distance import geodesic
from collections import defaultdict
import heapq

airports_url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
airports_cols = [
    "airport_id","name","city","country","iata","icao","latitude","longitude",
    "altitude","timezone","dst","tz_timezone","type","source"
]
df_airports = pd.read_csv(
    airports_url,
    header=None,
    names=airports_cols,
    index_col=False
)

routes_url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat"
routes_cols = [
    "airline","airline_id","src_iata","src_id","dst_iata","dst_id","codeshare",
    "stops","equipment"
]
df_routes = pd.read_csv(
    routes_url,
    header=None,
    names=routes_cols,
    index_col=False
)

df_airports = df_airports[
    (df_airports["iata"] != "\\N")
    & (~df_airports["iata"].isna())
    & (~df_airports["latitude"].isna())
    & (~df_airports["longitude"].isna())
]
df_airports["latitude"] = pd.to_numeric(df_airports["latitude"], errors="coerce")
df_airports["longitude"] = pd.to_numeric(df_airports["longitude"], errors="coerce")
df_airports.dropna(subset=["latitude","longitude"], inplace=True)

airport_locations = {
    r["iata"]: (r["latitude"], r["longitude"])
    for _, r in df_airports.iterrows()
}
airport_cities = {
    r["iata"]: r["city"]
    for _, r in df_airports.iterrows()
}
airport_countries = {
    r["iata"]: r["country"]
    for _, r in df_airports.iterrows()
}

df_routes = df_routes[
    (df_routes["src_iata"] != "\\N")
    & (df_routes["dst_iata"] != "\\N")
    & (df_routes["src_iata"].isin(airport_locations.keys()))
    & (df_routes["dst_iata"].isin(airport_locations.keys()))
].copy()

graph = defaultdict(list)

def compute_distance(a, b):
    return geodesic(airport_locations[a], airport_locations[b]).kilometers

for _, row in df_routes.iterrows():
    src = row["src_iata"]
    dst = row["dst_iata"]
    dist = compute_distance(src, dst)
    _ = graph[src]
    _ = graph[dst]
    graph[src].append((dst, dist))

def multi_dijkstra(g, start_nodes, target_nodes):
    all_nodes = set(g.keys())
    for k in g:
        for neighbor, _ in g[k]:
            all_nodes.add(neighbor)

    dist = {}
    prev = {}
    for n in all_nodes:
        dist[n] = math.inf
        prev[n] = None

    pq = []
    for s in start_nodes:
        if s in dist:
            dist[s] = 0
            pq.append((0, s))

    heapq.heapify(pq)
    visited = set()
    best_dist = math.inf
    best_node = None

    while pq:
        current_dist, node = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)
        if node in target_nodes:
            best_dist = current_dist
            best_node = node
            break
        for neighbor, weight in g[node]:
            new_dist = current_dist + weight
            if new_dist < dist[neighbor]:
                dist[neighbor] = new_dist
                prev[neighbor] = node
                heapq.heappush(pq, (new_dist, neighbor))

    if math.isinf(best_dist):
        return math.inf, []

    path = []
    cur = best_node
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return best_dist, path

from_country = input("Enter the origin country: ")
to_country = input("Enter the destination country: ")

start_airports = df_airports[
    df_airports["country"].str.lower() == from_country.strip().lower()
]["iata"].tolist()

end_airports = df_airports[
    df_airports["country"].str.lower() == to_country.strip().lower()
]["iata"].tolist()

if not start_airports or not end_airports:
    print("No airports found in one or both countries.")
else:
    d_km, path_iatas = multi_dijkstra(graph, start_airports, end_airports)
    if math.isinf(d_km):
        print("No route found.")
    else:
        d_miles = d_km * 0.621371
        flight_speed_kmh = 900.0
        flight_time_hrs = d_km / flight_speed_kmh

        print(f"Distance: {d_miles:.2f} miles ({d_km:.2f} km)")
        print(f"Approximate flight time: {flight_time_hrs:.2f} hours")

        path_display = []
        for iata in path_iatas:
            cty = airport_cities.get(iata, "Unknown City")
            ctry = airport_countries.get(iata, "Unknown Country")
            path_display.append(f"{iata} ({cty}, {ctry})")

        print("Path:", " -> ".join(path_display))
