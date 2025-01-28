import pandas as pd
import math
from geopy.distance import geodesic
from collections import defaultdict
import heapq
import tkinter as tk
from tkinter import ttk

FLIGHT_SPEED_KMH = 900
KM_TO_MILES = 0.621371

class FlightRouteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Flight Route Finder")
        self.df = self.load_airport_data()
        self.graph = self.build_flight_network()
        self.create_widgets()
        self.route_coords = []

    def load_airport_data(self):
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

    def build_flight_network(self):
        cols = ["airline","airline_id","src_iata","src_id","dst_iata","dst_id","codeshare","stops","equipment"]
        routes_df = pd.read_csv(
            "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat",
            header=None,
            names=cols
        )
        valid_iata = set(self.df["iata"])
        airport_locations = {r["iata"]:(r["latitude"], r["longitude"]) for _,r in self.df.iterrows()}
        graph = defaultdict(dict)
        for _, row in routes_df.iterrows():
            src = row["src_iata"]
            dst = row["dst_iata"]
            if src in valid_iata and dst in valid_iata:
                distance = geodesic(airport_locations[src], airport_locations[dst]).kilometers
                if distance < graph[src].get(dst, math.inf):
                    graph[src][dst] = distance
        return {s: list(d.items()) for s,d in graph.items()}

    def optimized_dijkstra(self, start_airports, end_airports):
        graph = self.graph
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

    def create_widgets(self):
        input_frame = ttk.Frame(self.root, padding=10)
        input_frame.pack(fill=tk.X)
        
        ttk.Label(input_frame, text="Origin City:").grid(row=0, column=0, padx=5)
        self.origin_entry = ttk.Entry(input_frame, width=30)
        self.origin_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(input_frame, text="Destination City:").grid(row=0, column=2, padx=5)
        self.dest_entry = ttk.Entry(input_frame, width=30)
        self.dest_entry.grid(row=0, column=3, padx=5)
        
        search_btn = ttk.Button(input_frame, text="Find Route", command=self.search_route)
        search_btn.grid(row=0, column=4, padx=5)
        
        self.result_frame = ttk.Frame(self.root, padding=10)
        self.result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.route_list = tk.Listbox(self.result_frame, width=50)
        self.route_list.pack(side=tk.LEFT, fill=tk.Y)
        
        self.canvas = tk.Canvas(self.result_frame, bg="white", width=800, height=500)
        self.canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.status_label = ttk.Label(self.root, text="Ready")
        self.status_label.pack(fill=tk.X)

    def search_route(self):
        self.status_label.config(text="Searching...")
        self.root.update_idletasks()
        
        origin_city = self.origin_entry.get().strip().lower()
        destination_city = self.dest_entry.get().strip().lower()
        
        start_airports = self.df[self.df["city"].str.lower() == origin_city]["iata"].tolist()
        end_airports = self.df[self.df["city"].str.lower() == destination_city]["iata"].tolist()
        
        if not start_airports:
            self.status_label.config(text=f"No airports found for city '{origin_city}'")
            return
        if not end_airports:
            self.status_label.config(text=f"No airports found for city '{destination_city}'")
            return
        
        dist_km, route = self.optimized_dijkstra(start_airports, end_airports)
        
        if math.isinf(dist_km):
            self.status_label.config(text=f"No route found")
            return
        
        self.route_list.delete(0, tk.END)
        info_map = {r["iata"]:(r["city"], r["country"]) for _,r in self.df.iterrows()}
        
        for airport_code in route:
            city, country = info_map.get(airport_code, ("Unknown", "Unknown"))
            self.route_list.insert(tk.END, f"{airport_code} - {city}, {country}")
        
        self.draw_route(route)
        self.status_label.config(text=f"Distance: {dist_km * KM_TO_MILES:.1f} miles | Flight Time: {dist_km / FLIGHT_SPEED_KMH:.1f} hours")

    def project_coordinates(self, lon, lat):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        x = (lon + 180) * (canvas_width / 360)
        y = (90 - lat) * (canvas_height / 180)
        return x, y

    def draw_route(self, route):
        self.canvas.delete("all")
        coords = []
        
        for code in route:
            airport = self.df[self.df["iata"] == code].iloc[0]
            x, y = self.project_coordinates(airport["longitude"], airport["latitude"])
            coords.append((x, y))
        
        if len(coords) > 1:
            self.canvas.create_line(coords, fill="blue", width=2, smooth=True)
        
        for i, (x, y) in enumerate(coords):
            color = "green" if i == 0 else "red" if i == len(coords)-1 else "blue"
            self.canvas.create_oval(x-4, y-4, x+4, y+4, fill=color, outline="black")
            self.canvas.create_text(x+10, y, text=route[i], anchor=tk.W)

if __name__ == "__main__":
    root = tk.Tk()
    app = FlightRouteApp(root)
    root.mainloop()
