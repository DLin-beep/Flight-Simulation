import pandas as pd
import math
import heapq
import tkinter as tk
from tkinter import ttk
from geopy.distance import geodesic
from collections import defaultdict
from PIL import Image, ImageTk
import io
import base64

WORLD_MAP_BASE64 = #IDK HOW TO CODE THIS

FLIGHT_SPEED_KMH = 900
KM_TO_MILES = 0.621371
FUEL_BURN_RATE_L_PER_KM = 5
FUEL_COST_USD_PER_L = 0.8
OPERATING_COST_FACTOR = 1.2

class FlightRouteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Flight Route Finder")
        self.df = self.load_airport_data()
        self.graph = self.build_flight_network()
        self.create_widgets()
        self.route_coords = []

    def load_airport_data(self):
        cols = ["airport_id","name","city","country","iata","icao","latitude","longitude","altitude","timezone","dst","tz_timezone","type","source"]
        df = pd.read_csv("https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat", header=None, names=cols, index_col=False)
        df = df[(df["iata"] != "\\N") & df["iata"].notna() & df["latitude"].notna() & df["longitude"].notna()].copy()
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        df.dropna(subset=["latitude","longitude"], inplace=True)
        return df

    def build_flight_network(self):
        cols = ["airline","airline_id","src_iata","src_id","dst_iata","dst_id","codeshare","stops","equipment"]
        routes_df = pd.read_csv("https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat", header=None, names=cols)
        valid_iata = set(self.df["iata"])
        airport_locations = {r["iata"]: (r["latitude"], r["longitude"]) for _, r in self.df.iterrows()}
        graph = defaultdict(dict)
        for _, row in routes_df.iterrows():
            src = row["src_iata"]
            dst = row["dst_iata"]
            if src in valid_iata and dst in valid_iata:
                distance = geodesic(airport_locations[src], airport_locations[dst]).kilometers
                if distance < graph[src].get(dst, math.inf):
                    graph[src][dst] = distance
        return {s: list(d.items()) for s, d in graph.items()}

    def optimized_dijkstra(self, start_airports, end_airports):
        dist = {n: math.inf for n in self.graph}
        prev = {n: None for n in self.graph}
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
            for neighbor, weight in self.graph.get(node, []):
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
        self.canvas = tk.Canvas(self.result_frame, bg="lightblue", width=800, height=500)
        self.canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.stats_frame = ttk.Frame(self.root, padding=10)
        self.stats_frame.pack(fill=tk.X)
        self.distance_var = tk.StringVar()
        self.flight_time_var = tk.StringVar()
        self.fuel_consumption_var = tk.StringVar()
        self.fuel_cost_var = tk.StringVar()
        self.route_efficiency_var = tk.StringVar()
        self.pricing_impact_var = tk.StringVar()
        self.price_estimate_var = tk.StringVar()
        stats = [
            ("Distance:", self.distance_var),
            ("Flight Time:", self.flight_time_var),
            ("Fuel:", self.fuel_consumption_var),
            ("Fuel Cost:", self.fuel_cost_var),
            ("Efficiency:", self.route_efficiency_var),
            ("Price Impact:", self.pricing_impact_var),
            ("Ticket Range (per person):", self.price_estimate_var),
        ]
        for i, (label_text, var) in enumerate(stats):
            ttk.Label(self.stats_frame, text=label_text).grid(row=0, column=i*2, padx=5, sticky=tk.E)
            ttk.Label(self.stats_frame, textvariable=var).grid(row=0, column=i*2+1, padx=5, sticky=tk.W)
        self.status_label = ttk.Label(self.root, text="Ready")
        self.status_label.pack(fill=tk.X)
        try:
            map_data = base64.b64decode(WORLD_MAP_BASE64)
            self.world_map = Image.open(io.BytesIO(map_data))
            self.world_map = self.world_map.resize((800, 500), Image.LANCZOS)
            self.world_map_photo = ImageTk.PhotoImage(self.world_map)
        except:
            self.world_map_photo = None

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
            self.status_label.config(text="No route found")
            return
        self.route_list.delete(0, tk.END)
        info_map = {r["iata"]: (r["city"], r["country"]) for _, r in self.df.iterrows()}
        for airport_code in route:
            city, country = info_map.get(airport_code, ("Unknown", "Unknown"))
            self.route_list.insert(tk.END, f"{airport_code} - {city}, {country}")
        dist_miles = dist_km * KM_TO_MILES
        flight_time = dist_km / FLIGHT_SPEED_KMH
        fuel_consumption = dist_km * FUEL_BURN_RATE_L_PER_KM
        fuel_cost = fuel_consumption * FUEL_COST_USD_PER_L
        stops = len(route) - 1 if len(route) > 1 else 1
        route_efficiency = dist_km / stops
        pricing_impact = fuel_cost * OPERATING_COST_FACTOR
        seats = 150
        lowest_price = (pricing_impact * 1.2) / seats
        highest_price = (pricing_impact * 1.5) / seats
        self.distance_var.set(f"{format(dist_miles, ',.1f')}mi")
        self.flight_time_var.set(f"{format(flight_time, ',.1f')}h")
        self.fuel_consumption_var.set(f"{format(fuel_consumption, ',.1f')}L")
        self.fuel_cost_var.set(f"${format(fuel_cost, ',.2f')}")
        self.route_efficiency_var.set(format(route_efficiency, ',.2f'))
        self.pricing_impact_var.set(f"${format(pricing_impact, ',.2f')}")
        self.price_estimate_var.set(f"${format(lowest_price, ',.2f')}-{format(highest_price, ',.2f')}")
        self.draw_route(route)
        self.status_label.config(text="Done")

    def project_coordinates(self, lon, lat):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        x = (lon + 180) * (canvas_width / 360)
        y = (90 - lat) * (canvas_height / 180)
        return x, y

    def draw_route(self, route):
        self.canvas.delete("all")
        if self.world_map_photo:
            self.canvas.create_image(0, 0, image=self.world_map_photo, anchor=tk.NW)
        coords = []
        for code in route:
            airport = self.df[self.df["iata"] == code].iloc[0]
            x, y = self.project_coordinates(airport["longitude"], airport["latitude"])
            coords.append((x, y))
        if len(coords) > 1:
            self.canvas.create_line(coords, fill="blue", width=2, smooth=True)
        for i, (x, y) in enumerate(coords):
            color = "green" if i == 0 else ("red" if i == len(coords) - 1 else "blue")
            self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=color, outline="black")
            self.canvas.create_text(x + 10, y, text=route[i], anchor=tk.W)

if __name__ == "__main__":
    root = tk.Tk()
    app = FlightRouteApp(root)
    root.mainloop()
