import pandas as pd
import math
from geopy.distance import geodesic
from collections import defaultdict
import heapq

FLIGHT_SPEED_KMH = 900
KM_TO_MILES = 0.621371

def load_airport_data():
    cols = [
        "airport_id","name","city","country","iata","icao","latitude",
        "longitude","altitude","timezone","dst","tz_timezone","type","source"
    ]
    df = pd.read_csv(
        "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat",
        header=None,
        names=cols,
        index_col=False
    )
    df = df[
        (df["iata"] != "\\N") &
        df["iata"].notna() &
        df["latitude"].notna() &
        df["longitude"].notna()
    ].copy()
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df.dropna(subset=["latitude","longitude"], inplace=True)
    return df

def build_flight_network(df):
    cols = ["airline","airline_id","src_iata","src_id","dst_iata","dst_id","codeshare","stops","equipment"]
    routes_df = pd.read_csv(
        "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat",
        header=None,
        names=cols
    )
    valid_iata = set(df["iata"])
    airport_locations = {r["iata"]:(r["latitude"], r["longitude"]) for _,r in df.iterrows()}
    graph = defaultdict(dict)
    for _, row in routes_df.iterrows():
        src = row["src_iata"]
        dst = row["dst_iata"]
        if src in valid_iata and dst in valid_iata:
            distance = geodesic(airport_locations[src], airport_locations[dst]).kilometers
            if distance < graph[src].get(dst, math.inf):
                graph[src][dst] = distance
    return {s: list(d.items()) for s,d in graph.items()}

def optimized_dijkstra(graph, start_airports, end_airports):
    dist = {n: math.inf for n in graph}
    prev = {n: None for n in graph}
    pq = []
    for s in start_airports:
        if s in dist:
            dist[s] = 0
            heapq.heappush(pq, (0, s))
    visited = set()
    best_dist = math.inf
    best_node = None
    while pq:
        current_dist, node = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)
        if node in end_airports:
            best_dist = current_dist
            best_node = node
            break
        for neighbor, weight in graph.get(node, []):
            if neighbor not in dist:
                continue
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
    return best_dist, path[::-1]

def main():
    df = load_airport_data()
    graph = build_flight_network(df)
    
    origin_city = input("Enter origin city: ").strip().lower()
    destination_city = input("Enter destination city: ").strip().lower()
    
    start_airports = df[df["city"].str.lower() == origin_city]["iata"].tolist()
    end_airports = df[df["city"].str.lower() == destination_city]["iata"].tolist()
    
    if not start_airports:
        print(f"No airports found for city '{origin_city}'.")
        return
    if not end_airports:
        print(f"No airports found for city '{destination_city}'.")
        return
    
    dist_km, route = optimized_dijkstra(graph, start_airports, end_airports)
    if math.isinf(dist_km):
        print(f"No route found from '{origin_city}' to '{destination_city}'.")
        return
    
    info_map = {r["iata"]:(r["city"], r["country"]) for _,r in df.iterrows()}
    print(f"\nTotal distance: {dist_km * KM_TO_MILES:.1f} miles ({dist_km:.1f} km)")
    print(f"Estimated flight time: {dist_km / FLIGHT_SPEED_KMH:.1f} hours\n")
    print("Route:")
    for airport_code in route:
        city, country = info_map.get(airport_code, ("Unknown City","Unknown Country"))
        print(f"→ {airport_code} ({city}, {country})")

if __name__ == "__main__":
    main()
