# ======================================================
# reconstruction_modules/data_loader.py
# Data Loading and Preprocessing Functions (Facade)
# ======================================================

import os

import geopandas as gpd
import numpy as np
import pandas as pd

try:
    from .config import *
    from .data_loader_common import OVERPASS_URL, _gaza_bbox_values, filter_gaza_only, is_within_gaza
    from .data_loader_downloads import (
        download_gaza_education_facilities,
        download_gaza_hospitals,
        download_gaza_municipality_boundaries,
        download_gaza_water_infrastructure,
    )
    from .data_loader_fixed_data import (
        get_fixed_gaza_municipalities,
        get_fixed_gaza_universities,
        get_fixed_major_hospitals,
    )
    from .data_loader_loaders import (
        correct_municipality_names,
        create_synthetic_municipality_boundaries,
        load_layer,
        load_road_damage_data,
    )
except ImportError:
    from config import *
    from data_loader_common import OVERPASS_URL, _gaza_bbox_values, filter_gaza_only, is_within_gaza
    from data_loader_downloads import (
        download_gaza_education_facilities,
        download_gaza_hospitals,
        download_gaza_municipality_boundaries,
        download_gaza_water_infrastructure,
    )
    from data_loader_fixed_data import (
        get_fixed_gaza_municipalities,
        get_fixed_gaza_universities,
        get_fixed_major_hospitals,
    )
    from data_loader_loaders import (
        correct_municipality_names,
        create_synthetic_municipality_boundaries,
        load_layer,
        load_road_damage_data,
    )


def load_damage_data():
    """Load and preprocess damage assessment data."""
    try:
        print(f"   - Loading Damage Data from {GDB_PATH}...")
        damage_gdf = gpd.read_file(GDB_PATH, layer="Damage_Sites_GazaStrip_20251011")
        damage_gdf = damage_gdf.to_crs(TARGET_CRS)

        damage_status_cols = [col for col in damage_gdf.columns if col.startswith("Damage_Status_")]
        if damage_status_cols:
            print(f"   - Calculating enhanced damage age from {len(damage_status_cols)} temporal cycles...")
            damage_status_cols_sorted = sorted(
                damage_status_cols, key=lambda x: x.split("_")[-1] if len(x.split("_")) > 2 else "99999999"
            )

            damage_gdf["damage_severity_sum"] = damage_gdf[damage_status_cols].sum(axis=1)

            weights = np.linspace(TIME_WEIGHTS["min_weight"], TIME_WEIGHTS["max_weight"], len(damage_status_cols_sorted))
            weighted_damage = damage_gdf[damage_status_cols_sorted] * weights
            damage_gdf["damage_weighted_recent"] = weighted_damage.sum(axis=1)

            consecutive_bonus = []
            for _, row in damage_gdf.iterrows():
                status_values = row[damage_status_cols_sorted].values
                consecutive_count = 0
                max_consecutive = 0
                for val in status_values:
                    if val > 0:
                        consecutive_count += 1
                        max_consecutive = max(max_consecutive, consecutive_count)
                    else:
                        consecutive_count = 0
                consecutive_bonus.append(max_consecutive)
            damage_gdf["damage_consecutive"] = consecutive_bonus

            trend_scores = []
            for _, row in damage_gdf.iterrows():
                status_values = row[damage_status_cols_sorted].values
                if len(status_values) > 1:
                    trend = status_values[-1] - status_values[0]
                    trend_scores.append(max(0, trend))
                else:
                    trend_scores.append(0)
            damage_gdf["damage_trend_worsening"] = trend_scores

            from sklearn.preprocessing import MinMaxScaler

            scaler = MinMaxScaler()
            age_components = [
                "damage_severity_sum",
                "damage_weighted_recent",
                "damage_consecutive",
                "damage_trend_worsening",
            ]
            for comp in age_components:
                if damage_gdf[comp].max() > 0:
                    damage_gdf[f"{comp}_norm"] = scaler.fit_transform(damage_gdf[[comp]])
                else:
                    damage_gdf[f"{comp}_norm"] = 0

            damage_gdf["damage_age"] = (
                AGE_RANKING_WEIGHTS["severity_multiplier"] * damage_gdf["damage_severity_sum_norm"]
                + AGE_RANKING_WEIGHTS["time_decay"] * damage_gdf["damage_weighted_recent_norm"]
                + AGE_RANKING_WEIGHTS["consecutive_bonus"] * damage_gdf["damage_consecutive_norm"]
                + AGE_RANKING_WEIGHTS["trend_multiplier"] * damage_gdf["damage_trend_worsening_norm"]
            )

            if damage_gdf["damage_age"].max() > 0:
                damage_gdf["damage_age_normalized"] = damage_gdf["damage_age"] / damage_gdf["damage_age"].max()
            else:
                damage_gdf["damage_age_normalized"] = 0
        else:
            damage_gdf["damage_age"] = 1
            damage_gdf["damage_age_normalized"] = 0.5

        return damage_gdf
    except Exception as e:
        print(f"    Error loading GDB: {e}")
        damage_gdf = gpd.GeoDataFrame(columns=["geometry"], crs="EPSG:4326")
        damage_gdf["damage_age"] = 1
        damage_gdf["damage_age_normalized"] = 0.5
        return damage_gdf


def generate_synthetic_infrastructure(damage_gdf):
    """Generate synthetic infrastructure data based on damage assessment municipalities."""
    from shapely.geometry import Point

    print("   - Generating synthetic infrastructure data...")
    municipalities = damage_gdf.groupby("Municipality").agg(
        {"geometry": lambda x: x.unary_union.centroid if len(x) > 0 else Point(0, 0)}
    ).reset_index()

    health_facilities = []
    hospital_names = [
        "Al-Shifa Hospital",
        "European Gaza Hospital",
        "Ahli Arab Hospital",
        "Al-Quds Hospital",
        "Gaza Indonesian Hospital",
        "Al-Remal Clinic",
        "Al-Wafa Hospital",
        "Al-Aqsa Hospital",
        "Gaza Central Clinic",
        "Rafah Medical Center",
        "Khan Yunis Hospital",
        "Deir al-Balah Clinic",
    ]
    for i, (_, mun) in enumerate(municipalities.iterrows()):
        centroid = mun["geometry"]
        municipality = mun["Municipality"]
        num_hospitals = min(2, max(1, len(municipality.split()) // 2))
        for j in range(num_hospitals):
            point = Point(centroid.x + np.random.uniform(-500, 500), centroid.y + np.random.uniform(-500, 500))
            facility_name = f"{hospital_names[(i * 2 + j) % len(hospital_names)]} - {municipality}"
            health_facilities.append(
                {"geometry": point, "name": facility_name, "amenity": "hospital" if j == 0 else "clinic", "municipality": municipality}
            )
    health_gdf = gpd.GeoDataFrame(health_facilities, crs=damage_gdf.crs)

    education_facilities = []
    school_names = [
        "Gaza Elementary School",
        "Al-Azhar School",
        "UNRWA School",
        "Islamic University",
        "Al-Quds University",
        "Gaza Technical College",
        "Rafah High School",
        "Khan Yunis Secondary School",
        "Deir al-Balah School",
        "Al-Shifa Medical School",
        "Gaza Engineering College",
        "Al-Aqsa University",
    ]
    for i, (_, mun) in enumerate(municipalities.iterrows()):
        centroid = mun["geometry"]
        municipality = mun["Municipality"]
        num_schools = min(4, max(2, len(municipality.split()) * 2))
        for j in range(num_schools):
            point = Point(centroid.x + np.random.uniform(-400, 400), centroid.y + np.random.uniform(-400, 400))
            school_name = f"{school_names[(i * 4 + j) % len(school_names)]} - {municipality}"
            amenity = "school" if j < num_schools - 1 else ("university" if j == num_schools - 1 and i % 3 == 0 else "school")
            education_facilities.append({"geometry": point, "name": school_name, "amenity": amenity, "municipality": municipality})
    edu_gdf = gpd.GeoDataFrame(education_facilities, crs=damage_gdf.crs)

    utility_facilities = []
    water_names = [
        "Gaza Water Treatment Plant",
        "Rafah Desalination Plant",
        "Khan Yunis Water Storage",
        "Deir al-Balah Wastewater Plant",
        "Central Gaza Water Works",
        "Al-Shifa Water Facility",
    ]
    fuel_names = [
        "Gaza Power Plant",
        "Rafah Solar Plant",
        "Khan Yunis Substation",
        "Deir al-Balah Generator",
        "Central Gaza Fuel Station",
        "Al-Shifa Energy Facility",
    ]
    for i, (_, mun) in enumerate(municipalities.iterrows()):
        centroid = mun["geometry"]
        municipality = mun["Municipality"]
        if i % 2 == 0:
            point = Point(centroid.x + np.random.uniform(-600, 600), centroid.y + np.random.uniform(-600, 600))
            utility_facilities.append(
                {
                    "geometry": point,
                    "name": f"{water_names[i % len(water_names)]} - {municipality}",
                    "type": "water_works" if i % 2 == 0 else "desalination",
                    "municipality": municipality,
                }
            )
        if i % 3 == 0:
            point = Point(centroid.x + np.random.uniform(-700, 700), centroid.y + np.random.uniform(-700, 700))
            utility_facilities.append(
                {
                    "geometry": point,
                    "name": f"{fuel_names[i % len(fuel_names)]} - {municipality}",
                    "type": "power_plant" if i % 2 == 0 else "substation",
                    "municipality": municipality,
                }
            )
    util_gdf = gpd.GeoDataFrame(utility_facilities, crs=damage_gdf.crs)

    food_facilities = []
    for _, mun in municipalities.iterrows():
        centroid = mun["geometry"]
        municipality = mun["Municipality"]
        num_points = max(3, len(municipality.split()) * 2)
        for j in range(num_points):
            point = Point(centroid.x + np.random.uniform(-200, 200), centroid.y + np.random.uniform(-200, 200))
            food_facilities.append(
                {"geometry": point, "name": f"Food Distribution Point {j + 1} - {municipality}", "type": "food_distribution", "municipality": municipality}
            )
    food_gdf = gpd.GeoDataFrame(food_facilities, crs=damage_gdf.crs)

    print(f"   - Generated: {len(health_gdf)} health facilities, {len(edu_gdf)} education facilities")
    print(f"   - Generated: {len(util_gdf)} utility facilities, {len(food_gdf)} food security points")
    return health_gdf, util_gdf, edu_gdf, food_gdf


def load_infrastructure_layers():
    """Load all infrastructure layers and categorize them."""
    print("   - Loading infrastructure data...")

    manual_hospitals = get_fixed_major_hospitals()
    print(f"   - Loaded {len(manual_hospitals)} verified major hospitals")

    if os.environ.get("FAST_MODE", "0") == "1":
        print("   - FAST_MODE enabled: skipping OSM hospital download")
        osm_hospitals = gpd.GeoDataFrame(columns=["geometry", "name", "amenity", "is_major"], crs=TARGET_CRS)
    else:
        osm_hospitals = download_gaza_hospitals()

    if not osm_hospitals.empty:
        health_gdf = pd.concat([manual_hospitals, osm_hospitals], ignore_index=True)
        print(f"   - Total hospitals: {len(health_gdf)} ({len(manual_hospitals)} major + {len(osm_hospitals)} from OSM)")
    else:
        health_gdf = manual_hospitals
        print(f"   - Using {len(manual_hospitals)} major hospitals only")

    util_gdf = load_layer("utilities_infra.gpkg", "Utilities Infrastructure (Water/Electric Proxy)")
    edu_gdf = load_layer("education_centers.gpkg", "Education Centers (Optional)")
    food_gdf = load_layer("food_security.gpkg", "Food Security (Optional)")

    if edu_gdf.empty:
        print("   - No local education data. Loading verified universities and downloading schools...")
        edu_gdf = download_gaza_education_facilities()
        if edu_gdf.empty:
            print("   - WARNING: No education data available (OpenStreetMap download failed)")
            print("   - System will continue without education facilities data")
            edu_gdf = gpd.GeoDataFrame(columns=["geometry", "name", "amenity"], crs=TARGET_CRS)
    else:
        print(f"   - Loaded {len(edu_gdf)} education facilities from local files")

    try:
        streets_gdf = load_road_damage_data()
        if streets_gdf.empty:
            print("   - WARNING: No road damage data available")
            print("   - System will continue without street data")
        elif not health_gdf.empty:
            print("   - Calculating strategic importance of roads...")
            streets_gdf["near_hospital"] = False
            streets_gdf["strategic_score"] = streets_gdf.get("strategic_score", 0)

            roads_pts = streets_gdf[["geometry"]].copy()
            roads_pts["geometry"] = roads_pts.geometry.representative_point()
            hosp_pts = health_gdf[["geometry"]].copy()
            hosp_pts["geometry"] = hosp_pts.geometry.representative_point()

            nearest = gpd.sjoin_nearest(
                roads_pts,
                hosp_pts,
                how="left",
                distance_col="distance_to_hospital",
                max_distance=1000,
            )
            d = nearest["distance_to_hospital"]
            mask_500 = d.notna() & (d <= 500)
            mask_1000 = d.notna() & (d <= 1000) & ~mask_500

            streets_gdf.loc[mask_500[mask_500].index, "near_hospital"] = True
            streets_gdf.loc[mask_500[mask_500].index, "strategic_score"] = 5
            streets_gdf.loc[mask_1000[mask_1000].index, "strategic_score"] = 3
            streets_gdf["reconstruction_priority"] = (
                streets_gdf["road_priority"] * 3
                + streets_gdf["damage_severity"] * 2
                + streets_gdf["is_major_artery"] * 10
                + streets_gdf["strategic_score"] * 4
            )
            print(f"   - {streets_gdf['near_hospital'].sum()} roads within 500m of hospitals (high priority)")
    except Exception as e:
        print(f"   - Error loading road damage data: {e}")
        print("   - System will continue without street data")
        streets_gdf = gpd.GeoDataFrame(columns=["geometry"], crs=TARGET_CRS)

    municipalities_gdf = get_fixed_gaza_municipalities()
    print(f"   - Loaded {len(municipalities_gdf)} verified municipalities")

    try:
        local_mun = load_layer("municipalities.gpkg", "Municipal Boundaries")
        if not local_mun.empty:
            print(f"   - Found {len(local_mun)} additional municipalities from local files")
            municipalities_gdf = pd.concat([municipalities_gdf, local_mun], ignore_index=True)
    except Exception:
        pass

    if os.environ.get("FAST_MODE", "0") != "1":
        try:
            osm_mun = download_gaza_municipality_boundaries()
            if not osm_mun.empty:
                print(f"   - Found {len(osm_mun)} additional municipalities from OpenStreetMap")
                municipalities_gdf = pd.concat([municipalities_gdf, osm_mun], ignore_index=True)
        except Exception:
            pass

    if not streets_gdf.empty:
        streets_gdf = correct_municipality_names(streets_gdf)

    hospitals_gdf = health_gdf.copy()
    if not hospitals_gdf.empty:
        hospitals_gdf = filter_gaza_only(hospitals_gdf)

    schools_gdf = (
        edu_gdf[edu_gdf["amenity"].isin(["school", "college"])]
        if not edu_gdf.empty and "amenity" in edu_gdf.columns
        else gpd.GeoDataFrame(columns=["geometry"], crs=TARGET_CRS)
    )
    universities_gdf = (
        edu_gdf[edu_gdf["amenity"] == "university"]
        if not edu_gdf.empty and "amenity" in edu_gdf.columns
        else gpd.GeoDataFrame(columns=["geometry"], crs=TARGET_CRS)
    )
    if not schools_gdf.empty:
        schools_gdf = filter_gaza_only(schools_gdf)
    if not universities_gdf.empty:
        universities_gdf = filter_gaza_only(universities_gdf)

    water_util_gdf = (
        util_gdf[util_gdf["type"].isin(["desalination", "water_storage", "water_works", "wastewater_plant"])]
        if not util_gdf.empty and "type" in util_gdf.columns
        else gpd.GeoDataFrame(columns=["geometry"], crs=TARGET_CRS)
    )
    fuel_util_gdf = (
        util_gdf[util_gdf["type"].isin(["power_plant", "solar_plant", "substation", "generator"])]
        if not util_gdf.empty and "type" in util_gdf.columns
        else gpd.GeoDataFrame(columns=["geometry"], crs=TARGET_CRS)
    )
    if not water_util_gdf.empty:
        water_util_gdf = filter_gaza_only(water_util_gdf)
    if not fuel_util_gdf.empty:
        fuel_util_gdf = filter_gaza_only(fuel_util_gdf)
    if not streets_gdf.empty:
        streets_gdf = filter_gaza_only(streets_gdf)
    if not municipalities_gdf.empty:
        municipalities_gdf = filter_gaza_only(municipalities_gdf)

    print(
        f"   - Categorized: {len(schools_gdf)} schools, {len(universities_gdf)} universities, "
        f"{len(water_util_gdf)} water facilities, {len(fuel_util_gdf)} fuel/energy facilities"
    )
    print(f"   - Additional layers: {len(streets_gdf)} streets, {len(municipalities_gdf)} municipalities")
    print("   - All infrastructure filtered to Gaza Strip boundaries only")
    print(f"   - Verified data: {len(universities_gdf)} universities and {len(municipalities_gdf)} municipalities loaded manually")

    try:
        water_gdf = load_layer("gaza_water_infrastructure.gpkg", "Water Infrastructure")
        if water_gdf.empty and os.environ.get("FAST_MODE", "0") != "1":
            print("   - No local water infrastructure data found. Attempting to download from OpenStreetMap...")
            water_gdf = download_gaza_water_infrastructure()
        elif water_gdf.empty:
            print("   - FAST_MODE enabled: skipping OSM water download")
        if not water_gdf.empty:
            print("   - Filtering water infrastructure to Gaza boundaries...")
            water_gdf = filter_gaza_only(water_gdf)
    except Exception as e:
        print(f"   - Error loading local water infrastructure data: {e}")
        if os.environ.get("FAST_MODE", "0") != "1":
            print("   - Attempting to download from OpenStreetMap...")
            water_gdf = download_gaza_water_infrastructure()
            if not water_gdf.empty:
                water_gdf = filter_gaza_only(water_gdf)
        else:
            water_gdf = gpd.GeoDataFrame(columns=["geometry"], crs=TARGET_CRS)

    fuel_gdf = gpd.GeoDataFrame(columns=["geometry"], crs=TARGET_CRS)
    rubble_gdf = gpd.GeoDataFrame(columns=["geometry"], crs=TARGET_CRS)
    apt_gov_gdf = gpd.GeoDataFrame(columns=["geometry"], crs=TARGET_CRS)
    homes_gdf = gpd.GeoDataFrame(columns=["geometry"], crs=TARGET_CRS)

    return {
        "hospitals": hospitals_gdf,
        "schools": schools_gdf,
        "universities": universities_gdf,
        "water_util": water_util_gdf,
        "fuel_util": fuel_util_gdf,
        "education": edu_gdf,
        "food_security": food_gdf,
        "streets": streets_gdf,
        "municipalities": municipalities_gdf,
        "water": water_gdf,
        "fuel": fuel_gdf,
        "rubble": rubble_gdf,
        "apartments_gov": apt_gov_gdf,
        "homes": homes_gdf,
    }


__all__ = [
    "OVERPASS_URL",
    "_gaza_bbox_values",
    "load_damage_data",
    "generate_synthetic_infrastructure",
    "is_within_gaza",
    "filter_gaza_only",
    "create_synthetic_municipality_boundaries",
    "download_gaza_municipality_boundaries",
    "download_gaza_water_infrastructure",
    "correct_municipality_names",
    "load_road_damage_data",
    "load_layer",
    "get_fixed_major_hospitals",
    "get_fixed_gaza_universities",
    "get_fixed_gaza_municipalities",
    "download_gaza_education_facilities",
    "download_gaza_hospitals",
    "load_infrastructure_layers",
]
