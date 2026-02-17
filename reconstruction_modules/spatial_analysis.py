# ======================================================
# reconstruction_modules/spatial_analysis.py
# Spatial Analysis and Grid Generation Functions
# ======================================================

import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon
from config import *
import pandas as pd

# ======================================================
# Hexagonal Grid Generation
# ======================================================

def create_hex_grid(gdf, radius=HEX_GRID_PARAMS["radius"]):
    """Create hexagonal grid covering the damage area"""
    print(f" Generating Hexagonal Grid (Radius: {radius}m)...")

    if gdf is None or gdf.empty:
        print("    ERROR: Damage layer is empty. Cannot derive bounds for grid.")
        return gpd.GeoDataFrame({"grid_id": []}, geometry=[], crs=TARGET_CRS)

    xmin, ymin, xmax, ymax = gdf.total_bounds
    dx = radius * 3
    dy = radius * np.sqrt(3)

    hexes = []
    for x in np.arange(xmin, xmax, dx):
        for y in np.arange(ymin, ymax, dy):
            for offset in [(0, 0), (radius * 1.5, radius * np.sqrt(3) / 2)]:
                cx, cy = x + offset[0], y + offset[1]
                hexagon = Polygon([
                    (cx + radius * np.cos(np.pi / 3 * i), cy + radius * np.sin(np.pi / 3 * i))
                    for i in range(6)
                ])
                hexes.append(hexagon)

    grid = gpd.GeoDataFrame(geometry=hexes, crs=gdf.crs)
    if grid.empty:
        print("    Warning: Grid is empty (check bounds).")
        return gpd.GeoDataFrame({"grid_id": []}, geometry=[], crs=gdf.crs)

    boundary = gdf.geometry.union_all().convex_hull
    grid = grid[grid.intersects(boundary)].copy()
    grid["grid_id"] = range(len(grid))
    grid["zone_id"] = [f"ZONE-{i+1:03d}" for i in range(len(grid))]
    print(f"    Created {len(grid)} hexagonal zones.")
    return grid

# ======================================================
# Spatial Data Integration
# ======================================================

def count_features_in_hex(grid, features, col_name):
    """Count features within each hexagon"""
    if grid is None or grid.empty:
        return grid.assign(**{col_name: 0})

    if features is None or features.empty:
        grid[col_name] = 0
        return grid

    joined = gpd.sjoin(grid, features, how="inner", predicate="intersects")
    counts = joined.groupby("grid_id").size().reset_index(name=col_name)
    return grid.merge(counts, on="grid_id", how="left").fillna({col_name: 0})

def sum_road_damage_in_hex(grid, roads_gdf, col_name):
    """Sum road damage severity within each hexagon"""
    if roads_gdf.empty or 'damage_severity' not in roads_gdf.columns:
        grid[col_name] = 0
        return grid
    
    joined = gpd.sjoin(grid, roads_gdf, how="inner", predicate="intersects")
    if joined.empty:
        grid[col_name] = 0
        return grid
    
    damage_sum = joined.groupby("grid_id")['damage_severity'].sum().reset_index(name=col_name)
    return grid.merge(damage_sum, on="grid_id", how="left").fillna({col_name: 0})


def sum_numeric_in_hex(grid, features_gdf, source_col, target_col):
    """Sum a numeric source column from features into each hex."""
    if features_gdf is None or features_gdf.empty or source_col not in features_gdf.columns:
        grid[target_col] = 0.0
        return grid

    joined = gpd.sjoin(grid, features_gdf[[source_col, "geometry"]], how="inner", predicate="intersects")
    if joined.empty:
        grid[target_col] = 0.0
        return grid

    summed = joined.groupby("grid_id")[source_col].sum().reset_index(name=target_col)
    return grid.merge(summed, on="grid_id", how="left").fillna({target_col: 0.0})


def count_condition_in_hex(grid, features_gdf, source_col, target_col):
    """Count features where source_col is truthy in each hex."""
    if features_gdf is None or features_gdf.empty or source_col not in features_gdf.columns:
        grid[target_col] = 0
        return grid

    flagged = features_gdf[features_gdf[source_col].astype(bool)]
    if flagged.empty:
        grid[target_col] = 0
        return grid

    joined = gpd.sjoin(grid, flagged[[source_col, "geometry"]], how="inner", predicate="intersects")
    if joined.empty:
        grid[target_col] = 0
        return grid

    counts = joined.groupby("grid_id").size().reset_index(name=target_col)
    return grid.merge(counts, on="grid_id", how="left").fillna({target_col: 0})

def aggregate_damage_age_in_hex(grid, damage_gdf, col_name):
    """Aggregate age-normalized damage scores within hexagons"""
    if 'damage_age_normalized' not in damage_gdf.columns:
        return grid.merge(pd.DataFrame({'grid_id': grid['grid_id'], col_name: 0}), on="grid_id", how="left").fillna({col_name: 0})

    joined = gpd.sjoin(grid, damage_gdf, how="inner", predicate="intersects")
    if joined.empty:
        return grid.merge(pd.DataFrame({'grid_id': grid['grid_id'], col_name: 0}), on="grid_id", how="left").fillna({col_name: 0})

    # Sum the age-normalized scores for each hex
    age_scores = joined.groupby("grid_id")['damage_age_normalized'].sum().reset_index(name=col_name)
    return grid.merge(age_scores, on="grid_id", how="left").fillna({col_name: 0})

def count_unique_municipalities(grid, damage_gdf, col_name):
    """Count unique municipalities within each hexagon"""
    if damage_gdf.empty or 'Municipality' not in damage_gdf.columns:
        grid[col_name] = 0
        return grid

    joined = gpd.sjoin(grid, damage_gdf, how="inner", predicate="intersects")
    if joined.empty:
        grid[col_name] = 0
        return grid

    unique_mun = joined.groupby("grid_id")["Municipality"].nunique().reset_index(name=col_name)
    return grid.merge(unique_mun, on="grid_id", how="left").fillna({col_name: 0})

def get_primary_municipality(grid, damage_gdf):
    """Get the most common municipality name for each hex"""
    if damage_gdf.empty or 'Municipality' not in damage_gdf.columns:
        grid['primary_municipality'] = 'Unknown'
        return grid

    joined = gpd.sjoin(grid, damage_gdf, how="inner", predicate="intersects")
    if joined.empty:
        grid['primary_municipality'] = 'Unknown'
        return grid

    # Get most frequent municipality per hex
    municipality_mode = joined.groupby("grid_id")["Municipality"].agg(lambda x: x.mode().iloc[0] if not x.mode().empty else 'Unknown').reset_index(name='primary_municipality')
    return grid.merge(municipality_mode, on="grid_id", how="left").fillna({'primary_municipality': 'Unknown'})

# ======================================================
# Grid Enhancement Functions
# ======================================================

def integrate_spatial_data(hex_grid, damage_gdf, infrastructure_layers):
    """Integrate all spatial data into the hexagonal grid"""
    print(" Performing Spatial Joins...")

    # Count damage sites
    hex_grid = count_features_in_hex(hex_grid, damage_gdf, "damage_count")

    # Aggregate damage age scores
    hex_grid = aggregate_damage_age_in_hex(hex_grid, damage_gdf, "damage_age_score")

    # Count infrastructure features
    hex_grid = count_features_in_hex(hex_grid, infrastructure_layers['hospitals'], "hospitals_count")
    major_hospitals = infrastructure_layers['hospitals'][infrastructure_layers['hospitals'].get('is_major') == True]
    hex_grid = count_features_in_hex(hex_grid, major_hospitals, "major_hospitals_count")    
    hex_grid = get_facility_names(hex_grid, major_hospitals, "major_hospital_names")
    hex_grid = count_features_in_hex(hex_grid, infrastructure_layers['schools'], "schools_count")
    hex_grid = count_features_in_hex(hex_grid, infrastructure_layers['universities'], "universities_count")
    print(f"    - Universities: {len(infrastructure_layers['universities'])} total, {hex_grid['universities_count'].sum():.0f} in zones")
    hex_grid = count_features_in_hex(hex_grid, infrastructure_layers['water_util'], "water_util_count")
    hex_grid = count_features_in_hex(hex_grid, infrastructure_layers['fuel_util'], "fuel_util_count")
    hex_grid = count_features_in_hex(hex_grid, infrastructure_layers['streets'], "streets_count")
    print(f"    - Streets: {len(infrastructure_layers['streets'])} total, {hex_grid['streets_count'].sum():.0f} in zones")
    
    # Add road damage severity
    hex_grid = sum_road_damage_in_hex(hex_grid, infrastructure_layers['streets'], "road_damage_severity")
    hex_grid = sum_numeric_in_hex(hex_grid, infrastructure_layers['streets'], "edge_betweenness", "street_centrality_sum")
    hex_grid = sum_numeric_in_hex(
        hex_grid,
        infrastructure_layers['streets'],
        "connectivity_impedance_increase",
        "street_impedance_sum"
    )
    hex_grid = count_condition_in_hex(
        hex_grid,
        infrastructure_layers['streets'],
        "connectivity_critical",
        "critical_streets_count"
    )
    
    hex_grid = count_features_in_hex(hex_grid, infrastructure_layers['municipalities'], "municipalities_count")

    # Municipality analysis (must be done before population estimation)
    hex_grid = count_unique_municipalities(hex_grid, damage_gdf, "municipality_count")
    hex_grid = get_primary_municipality(hex_grid, damage_gdf)

    # Population density: Use WorldPop data or fallback estimation
    try:
        from population_data import extract_population_for_zones
        hex_grid = extract_population_for_zones(hex_grid)
        print(f"    - Population data loaded: {hex_grid['population_total'].sum():,.0f} total people")
    except Exception as e:
        print(f"    - Warning: Could not load WorldPop data ({e})")
        print("    - Using fallback population estimation")
        from population_data import estimate_population_fallback
        hex_grid = estimate_population_fallback(hex_grid)

    # Optional layers
    hex_grid = count_features_in_hex(hex_grid, infrastructure_layers['education'], "education_count")

    # Add max damage count for strategy determination
    hex_grid['max_damage_count'] = hex_grid['damage_count'].max()

    return hex_grid




def get_facility_names(grid, features, col_name):
    if features is None or features.empty:
        grid[col_name] = "None"
        return grid
        
    joined = gpd.sjoin(grid, features, how="inner", predicate="intersects")
    
    if joined.empty:
        grid[col_name] = "None"
        return grid
    name_col = 'name' if 'name' in joined.columns else 'Name'
    
    names = joined.groupby("grid_id")[name_col].agg(lambda x: ", ".join(set(str(i) for i in x))).reset_index(name=col_name)
    return grid.merge(names, on="grid_id", how="left").fillna({col_name: "None"})
