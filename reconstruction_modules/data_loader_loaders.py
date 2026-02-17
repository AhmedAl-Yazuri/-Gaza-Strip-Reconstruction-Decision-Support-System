import os

import geopandas as gpd
import pandas as pd

try:
    from .config import DATA_DIR_INFRA, TARGET_CRS
    from .data_loader_common import filter_gaza_only
except ImportError:
    from config import DATA_DIR_INFRA, TARGET_CRS
    from data_loader_common import filter_gaza_only


def create_synthetic_municipality_boundaries(streets_gdf):
    """Create synthetic municipality boundaries from street network data."""
    if streets_gdf.empty or "municipality" not in streets_gdf.columns:
        return gpd.GeoDataFrame(columns=["geometry", "name", "admin_level"], crs=streets_gdf.crs)

    municipalities = []
    for municipality_name, group in streets_gdf.groupby("municipality"):
        if not group.empty:
            try:
                hull = group.geometry.unary_union.convex_hull
                municipalities.append(
                    {
                        "geometry": hull,
                        "name": municipality_name,
                        "name_ar": "",
                        "admin_level": "8",
                        "boundary": "administrative",
                        "type": "municipality",
                    }
                )
            except Exception as e:
                print(f"   - Error creating boundary for {municipality_name}: {e}")
                continue

    if municipalities:
        municipalities_gdf = gpd.GeoDataFrame(municipalities, crs=streets_gdf.crs)
        print(f"   - Created {len(municipalities_gdf)} synthetic municipality boundaries")
        return municipalities_gdf
    return gpd.GeoDataFrame(columns=["geometry", "name", "admin_level"], crs=streets_gdf.crs)


def correct_municipality_names(gdf, municipalities_gdf=None):
    """Correct municipality names based on longitude/latitude coordinates."""
    if gdf.empty:
        return gdf

    print("   - Correcting municipality names based on coordinates...")
    municipality_bounds = {
        "Beit Hanoun": {"lon": (34.52, 34.54), "lat": (31.53, 31.58)},
        "Beit Lahia": {"lon": (34.48, 34.54), "lat": (31.52, 31.58)},
        "Jabalia": {"lon": (34.47, 34.53), "lat": (31.50, 31.55)},
        "Gaza City": {"lon": (34.40, 34.50), "lat": (31.45, 31.55)},
        "Al-Bureij": {"lon": (34.38, 34.42), "lat": (31.44, 31.47)},
        "Nuseirat": {"lon": (34.395, 34.425), "lat": (31.435, 31.465)},
        "Al-Maghazi": {"lon": (34.39, 34.43), "lat": (31.42, 31.45)},
        "Deir al-Balah": {"lon": (34.35, 34.395), "lat": (31.40, 31.435)},
        "Khan Yunis": {"lon": (34.25, 34.35), "lat": (31.30, 31.40)},
        "Rafah": {"lon": (34.22, 34.30), "lat": (31.22, 31.35)},
    }

    gdf_wgs84 = gdf.to_crs("EPSG:4326") if gdf.crs != "EPSG:4326" else gdf.copy()
    if "municipality" not in gdf.columns:
        gdf["municipality"] = "Unknown"

    rep_points = gdf_wgs84.geometry.representative_point()
    lon = rep_points.x
    lat = rep_points.y

    assigned = pd.Series(index=gdf.index, dtype="object")
    for mun_name, bounds in municipality_bounds.items():
        in_mun = lon.between(bounds["lon"][0], bounds["lon"][1]) & lat.between(bounds["lat"][0], bounds["lat"][1])
        assigned.loc[in_mun] = mun_name

    to_update = assigned.notna() & (gdf["municipality"] != assigned)
    corrected_count = int(to_update.sum())
    if corrected_count > 0:
        gdf.loc[to_update, "municipality"] = assigned.loc[to_update]
        print(f"   - Corrected {corrected_count} municipality names based on coordinates")
    return gdf


def load_road_damage_data():
    """Load road damage assessment data from UNOSAT GDB."""
    print("   - Loading Road Damage Data from UNOSAT...")
    module_dir = os.path.dirname(__file__)
    expected_name = "CE20231007PSE_UNOSAT_OCHA_GazaStrip_RoadCDA_20250708_GDB_v1.gdb"
    possible_paths = [
        expected_name,
        os.path.join(module_dir, expected_name),
        os.path.join(module_dir, "CE20231007PSE_UNOSAT_GazaStrip_RoadCDA_20250708_GDB_v1.gdb", expected_name),
    ]

    road_gdb_path = None
    for path in possible_paths:
        if os.path.exists(path):
            road_gdb_path = path
            print(f"   - Found road GDB at: {path}")
            break

    # Fallback: discover the expected road GDB anywhere under this module.
    if road_gdb_path is None:
        for root, dirs, _ in os.walk(module_dir):
            for d in dirs:
                if d == expected_name:
                    road_gdb_path = os.path.join(root, d)
                    print(f"   - Found road GDB at: {road_gdb_path}")
                    break
            if road_gdb_path is not None:
                break

    if road_gdb_path is None:
        print("   - WARNING: Road GDB not found in any expected location")
        return gpd.GeoDataFrame(columns=["geometry", "RoadType", "damage_severity", "municipality", "name"], crs=TARGET_CRS)

    try:
        roads_gdf = gpd.read_file(road_gdb_path).to_crs(TARGET_CRS)
        roads_gdf = filter_gaza_only(roads_gdf)
        if roads_gdf.empty:
            print("   - No road data after filtering")
            return gpd.GeoDataFrame(columns=["geometry", "RoadType", "damage_severity", "municipality", "name"], crs=TARGET_CRS)

        roads_gdf["municipality"] = roads_gdf["Governorate"]
        roads_gdf["name"] = roads_gdf["RoadType"] + " Road"
        roads_gdf["highway"] = roads_gdf["RoadType"].str.lower()

        road_priority = {"Main": 5, "Regional": 4, "Local": 3, "Internal": 2, "Agricultural": 1}
        roads_gdf["road_priority"] = roads_gdf["RoadType"].map(road_priority).fillna(1)
        roads_gdf["damage_severity"] = roads_gdf["DamageStatus3"].fillna(0)
        roads_gdf["strategic_score"] = 0
        roads_gdf["near_hospital"] = False

        major_roads = ["salah", "rashid", "beach", "صلاح", "رشيد", "بحر"]
        roads_gdf["is_major_artery"] = roads_gdf.apply(
            lambda row: any(keyword in str(row.get("name", "")).lower() for keyword in major_roads) if "name" in row.index else False,
            axis=1,
        )

        roads_gdf["reconstruction_priority"] = (
            roads_gdf["road_priority"] * 3 + roads_gdf["damage_severity"] * 2 + roads_gdf["is_major_artery"] * 10
        )

        print(f"   - Loaded {len(roads_gdf)} road segments")
        print(f"   - Total length: {roads_gdf['Length_km'].sum():.1f} km")
        print(f"   - Road types: {roads_gdf['RoadType'].value_counts().to_dict()}")
        print(f"   - Damaged roads: {(roads_gdf['damage_severity'] > 0).sum()}")
        return roads_gdf
    except Exception as e:
        print(f"   - Error loading road damage data: {e}")
        import traceback

        traceback.print_exc()
        return gpd.GeoDataFrame(columns=["geometry", "RoadType", "damage_severity", "municipality", "name"], crs=TARGET_CRS)


def load_layer(filename, name):
    """Generic function to load geospatial layers."""
    path = os.path.join(DATA_DIR_INFRA, filename)
    if os.path.exists(path):
        print(f"   - Loading {name} ({filename})...")
        gdf = gpd.read_file(path)
        return gdf.to_crs(TARGET_CRS)

    print(f"    Warning: {filename} not found in {DATA_DIR_INFRA}. Creating empty layer for {name}.")
    return gpd.GeoDataFrame(columns=["geometry"], crs=TARGET_CRS)
