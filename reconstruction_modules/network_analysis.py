# ======================================================
# network_analysis.py - Connectivity-Based Street Criticality
# ======================================================

import os
import numpy as np
import geopandas as gpd
from shapely.geometry import LineString, MultiLineString
from config import GAZA_BBOX, TARGET_CRS


def _safe_lines(geom):
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [geom]
    if isinstance(geom, MultiLineString):
        return [line for line in geom.geoms if line is not None and not line.is_empty]
    return []


def _nearest_node(node_xy, point_xy):
    if not node_xy:
        return None
    px, py = point_xy
    best_node = None
    best_dist = float("inf")
    for node_id, (nx, ny) in node_xy.items():
        d2 = (nx - px) ** 2 + (ny - py) ** 2
        if d2 < best_dist:
            best_dist = d2
            best_node = node_id
    return best_node


def _extract_facility_nodes(node_xy, facilities_gdf):
    if facilities_gdf is None or facilities_gdf.empty:
        return []
    facility_nodes = []
    for _, row in facilities_gdf.iterrows():
        pt = row.geometry.representative_point()
        n = _nearest_node(node_xy, (pt.x, pt.y))
        if n is not None:
            facility_nodes.append(n)
    return list(set(facility_nodes))


def _build_graph_from_streets(streets_gdf):
    import networkx as nx

    G = nx.Graph()
    node_map = {}
    node_xy = {}
    edge_rows = {}
    next_node_id = 1

    for idx, row in streets_gdf.iterrows():
        damage = float(row.get("damage_severity", 0) or 0)
        lines = _safe_lines(row.geometry)
        for line in lines:
            coords = list(line.coords)
            if len(coords) < 2:
                continue

            p1 = (round(coords[0][0], 2), round(coords[0][1], 2))
            p2 = (round(coords[-1][0], 2), round(coords[-1][1], 2))

            if p1 not in node_map:
                node_map[p1] = next_node_id
                node_xy[next_node_id] = p1
                next_node_id += 1
            if p2 not in node_map:
                node_map[p2] = next_node_id
                node_xy[next_node_id] = p2
                next_node_id += 1

            u = node_map[p1]
            v = node_map[p2]
            length = float(line.length or 1.0)
            weight_base = max(length, 1.0)
            weight_damaged = weight_base * (1.0 + (damage / 3.0))

            if G.has_edge(u, v):
                if weight_damaged < G[u][v].get("weight_damaged", weight_damaged):
                    G[u][v]["weight_base"] = weight_base
                    G[u][v]["weight_damaged"] = weight_damaged
                    G[u][v]["damage_severity"] = damage
            else:
                G.add_edge(
                    u,
                    v,
                    weight_base=weight_base,
                    weight_damaged=weight_damaged,
                    damage_severity=damage,
                )

            edge_rows.setdefault(tuple(sorted((u, v))), set()).add(idx)

    return G, node_xy, edge_rows


def _download_osmnx_graph():
    if os.environ.get("ENABLE_OSMNX_FALLBACK", "0") != "1":
        return None

    try:
        import osmnx as ox
    except Exception:
        return None

    try:
        north = GAZA_BBOX["max_lat"]
        south = GAZA_BBOX["min_lat"]
        east = GAZA_BBOX["max_lon"]
        west = GAZA_BBOX["min_lon"]
        return ox.graph_from_bbox(north, south, east, west, network_type="drive")
    except Exception:
        return None


def apply_network_criticality(streets_gdf, hospitals_gdf=None, water_gdf=None):
    """
    Compute connectivity-based criticality for streets.
    Adds:
    - edge_betweenness
    - connectivity_impedance_increase
    - connectivity_critical
    - network_priority_boost
    """
    streets = streets_gdf.copy() if streets_gdf is not None else gpd.GeoDataFrame()

    if streets.empty:
        G_osm = _download_osmnx_graph()
        if G_osm is not None:
            try:
                import osmnx as ox
                _, edges = ox.graph_to_gdfs(G_osm, nodes=True, edges=True)
                streets = edges.reset_index(drop=True)[["geometry"]].copy()
                streets["damage_severity"] = 0.0
            except Exception:
                pass

    if streets.empty:
        return streets_gdf

    # Keep all network calculations in projected CRS for metric lengths.
    if streets.crs != TARGET_CRS:
        streets = streets.to_crs(TARGET_CRS)
    if hospitals_gdf is not None and not hospitals_gdf.empty and hospitals_gdf.crs != TARGET_CRS:
        hospitals_gdf = hospitals_gdf.to_crs(TARGET_CRS)
    if water_gdf is not None and not water_gdf.empty and water_gdf.crs != TARGET_CRS:
        water_gdf = water_gdf.to_crs(TARGET_CRS)

    try:
        import networkx as nx
    except Exception:
        streets["edge_betweenness"] = 0.0
        streets["connectivity_impedance_increase"] = 0.0
        streets["connectivity_critical"] = False
        streets["network_priority_boost"] = 0.0
        return streets

    G, node_xy, edge_rows = _build_graph_from_streets(streets)
    if G.number_of_nodes() == 0 or G.number_of_edges() == 0:
        streets["edge_betweenness"] = 0.0
        streets["connectivity_impedance_increase"] = 0.0
        streets["connectivity_critical"] = False
        streets["network_priority_boost"] = 0.0
        return streets

    facility_nodes = _extract_facility_nodes(node_xy, hospitals_gdf)
    if not facility_nodes:
        facility_nodes = _extract_facility_nodes(node_xy, water_gdf)

    if not facility_nodes:
        streets["edge_betweenness"] = 0.0
        streets["connectivity_impedance_increase"] = 0.0
        streets["connectivity_critical"] = False
        streets["network_priority_boost"] = 0.0
        return streets

    # Exact betweenness on 60k+ roads is too slow; use approximation for large graphs.
    if G.number_of_edges() > 15000:
        k = min(800, max(100, G.number_of_nodes() // 40))
        edge_centrality = nx.edge_betweenness_centrality(
            G,
            k=k,
            weight="weight_damaged",
            normalized=True,
            seed=42
        )
    else:
        edge_centrality = nx.edge_betweenness_centrality(G, weight="weight_damaged", normalized=True)
    base_dist = nx.multi_source_dijkstra_path_length(G, facility_nodes, weight="weight_base")
    damaged_dist = nx.multi_source_dijkstra_path_length(G, facility_nodes, weight="weight_damaged")

    node_imp = {}
    for n in G.nodes:
        b = float(base_dist.get(n, 0.0))
        d = float(damaged_dist.get(n, b))
        node_imp[n] = max(0.0, d - b)

    streets["edge_betweenness"] = 0.0
    streets["connectivity_impedance_increase"] = 0.0

    for uv, rows in edge_rows.items():
        u, v = uv
        c = float(edge_centrality.get((u, v), edge_centrality.get((v, u), 0.0)))
        imp = (node_imp.get(u, 0.0) + node_imp.get(v, 0.0)) / 2.0
        for ridx in rows:
            streets.at[ridx, "edge_betweenness"] = max(streets.at[ridx, "edge_betweenness"], c)
            streets.at[ridx, "connectivity_impedance_increase"] = max(
                streets.at[ridx, "connectivity_impedance_increase"], imp
            )

    damaged = streets[streets.get("damage_severity", 0) >= 2].copy()
    if damaged.empty:
        streets["connectivity_critical"] = False
        streets["network_priority_boost"] = streets["edge_betweenness"] * 0.5
        return streets

    centrality_thr = float(damaged["edge_betweenness"].quantile(0.75))
    impedance_thr = float(damaged["connectivity_impedance_increase"].quantile(0.75))

    streets["connectivity_critical"] = (
        (streets.get("damage_severity", 0) >= 2)
        & (streets["edge_betweenness"] >= centrality_thr)
        & (streets["connectivity_impedance_increase"] >= impedance_thr)
    )
    streets["network_priority_boost"] = (
        streets["edge_betweenness"] * 0.6
        + (streets["connectivity_impedance_increase"] / max(streets["connectivity_impedance_increase"].max(), 1.0)) * 0.4
        + streets["connectivity_critical"].astype(float) * 0.5
    )

    return streets
