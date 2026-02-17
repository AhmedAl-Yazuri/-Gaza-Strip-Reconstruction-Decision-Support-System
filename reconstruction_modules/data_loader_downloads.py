import os

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import LineString, Point, Polygon

try:
    from .config import DATA_DIR_INFRA, TARGET_CRS
    from .data_loader_common import OVERPASS_URL, _gaza_bbox_values, filter_gaza_only
    from .data_loader_fixed_data import get_fixed_gaza_universities
except ImportError:
    from config import DATA_DIR_INFRA, TARGET_CRS
    from data_loader_common import OVERPASS_URL, _gaza_bbox_values, filter_gaza_only
    from data_loader_fixed_data import get_fixed_gaza_universities


def download_gaza_municipality_boundaries():
    """Download municipality boundary data for Gaza Strip from OpenStreetMap."""
    print("   - Downloading Gaza municipality boundaries from OpenStreetMap...")
    gaza_bbox = _gaza_bbox_values()

    try:
        query = f"""
        [out:json][timeout:25];
        (
          relation["boundary"="administrative"]["admin_level"="6"]({gaza_bbox[1]},{gaza_bbox[0]},{gaza_bbox[3]},{gaza_bbox[2]});
          relation["boundary"="administrative"]["admin_level"="7"]({gaza_bbox[1]},{gaza_bbox[0]},{gaza_bbox[3]},{gaza_bbox[2]});
          relation["boundary"="administrative"]["admin_level"="8"]({gaza_bbox[1]},{gaza_bbox[0]},{gaza_bbox[3]},{gaza_bbox[2]});
        );
        out geom;
        """

        response = requests.post(OVERPASS_URL, data={"data": query}, timeout=30)
        response.raise_for_status()
        data = response.json()

        features = []
        for element in data.get("elements", []):
            if element["type"] == "relation" and "members" in element:
                boundary_coords = []
                for member in element.get("members", []):
                    if member["type"] == "way" and member.get("role") == "outer":
                        way_id = member["ref"]
                        for way_elem in data.get("elements", []):
                            if way_elem.get("id") == way_id and way_elem.get("type") == "way":
                                coords = [(point["lon"], point["lat"]) for point in way_elem.get("geometry", [])]
                                boundary_coords.extend(coords)
                                break

                if boundary_coords:
                    if boundary_coords[0] != boundary_coords[-1]:
                        boundary_coords.append(boundary_coords[0])
                    try:
                        geom = Polygon(boundary_coords)
                        tags = element.get("tags", {})
                        features.append(
                            {
                                "geometry": geom,
                                "name": tags.get("name", ""),
                                "name_ar": tags.get("name:ar", ""),
                                "admin_level": tags.get("admin_level", ""),
                                "boundary": tags.get("boundary", ""),
                                "type": "municipality",
                            }
                        )
                    except Exception as e:
                        print(f"       - Error creating polygon for relation: {e}")
                        continue

        if features:
            municipalities_gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")
            municipalities_gdf = filter_gaza_only(municipalities_gdf).to_crs(TARGET_CRS)
            print(f"   - Successfully downloaded {len(municipalities_gdf)} municipality boundaries")
            output_path = os.path.join(DATA_DIR_INFRA, "gaza_municipalities.gpkg")
            municipalities_gdf.to_file(output_path, driver="GPKG")
            print(f"   - Saved municipality boundaries to {output_path}")
            return municipalities_gdf

        print("   - No municipality boundary data found")
        return gpd.GeoDataFrame(columns=["geometry", "name", "admin_level"], crs=TARGET_CRS)
    except Exception as e:
        print(f"   - Error downloading municipality boundaries: {e}")
        return gpd.GeoDataFrame(columns=["geometry", "name", "admin_level"], crs=TARGET_CRS)


def download_gaza_water_infrastructure():
    """Download water infrastructure data for Gaza Strip from OpenStreetMap."""
    print("   - Downloading Gaza water infrastructure from OpenStreetMap...")
    gaza_bbox = _gaza_bbox_values()

    try:
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"="water_point"]({gaza_bbox[1]},{gaza_bbox[0]},{gaza_bbox[3]},{gaza_bbox[2]});
          node["man_made"="water_well"]({gaza_bbox[1]},{gaza_bbox[0]},{gaza_bbox[3]},{gaza_bbox[2]});
          node["man_made"="water_tower"]({gaza_bbox[1]},{gaza_bbox[0]},{gaza_bbox[3]},{gaza_bbox[2]});
          way["man_made"="water_works"]({gaza_bbox[1]},{gaza_bbox[0]},{gaza_bbox[3]},{gaza_bbox[2]});
          way["waterway"="canal"]({gaza_bbox[1]},{gaza_bbox[0]},{gaza_bbox[3]},{gaza_bbox[2]});
          way["waterway"="drain"]({gaza_bbox[1]},{gaza_bbox[0]},{gaza_bbox[3]},{gaza_bbox[2]});
          relation["waterway"]({gaza_bbox[1]},{gaza_bbox[0]},{gaza_bbox[3]},{gaza_bbox[2]});
        );
        out geom;
        """

        response = requests.post(OVERPASS_URL, data={"data": query}, timeout=30)
        response.raise_for_status()
        data = response.json()

        features = []
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            if element["type"] == "node":
                geom = Point(element["lon"], element["lat"])
            elif element["type"] == "way" and "geometry" in element:
                coords = [(point["lon"], point["lat"]) for point in element["geometry"]]
                if len(coords) <= 1:
                    continue
                geom = LineString(coords)
            else:
                continue

            features.append(
                {
                    "geometry": geom,
                    "name": tags.get("name", ""),
                    "type": tags.get("amenity", tags.get("man_made", tags.get("waterway", "water_infrastructure"))),
                    "operator": tags.get("operator", ""),
                    "description": tags.get("description", ""),
                }
            )

        if features:
            water_gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")
            water_gdf = filter_gaza_only(water_gdf).to_crs(TARGET_CRS)
            print(f"   - Successfully downloaded {len(water_gdf)} water infrastructure features")
            output_path = os.path.join(DATA_DIR_INFRA, "gaza_water_infrastructure.gpkg")
            water_gdf.to_file(output_path, driver="GPKG")
            print(f"   - Saved water infrastructure to {output_path}")
            return water_gdf

        print("   - No water infrastructure data found")
        return gpd.GeoDataFrame(columns=["geometry", "name", "type"], crs=TARGET_CRS)
    except Exception as e:
        print(f"   - Error downloading water infrastructure: {e}")
        return gpd.GeoDataFrame(columns=["geometry", "name", "type"], crs=TARGET_CRS)


def download_gaza_education_facilities():
    """Download education facilities from OpenStreetMap with names."""
    print("   - Loading Gaza education facilities...")
    universities_gdf = get_fixed_gaza_universities()
    print(f"   - Loaded {len(universities_gdf)} verified universities")
    gaza_bbox = _gaza_bbox_values()

    try:
        query = f"""
        [out:json][timeout:30];
        (
          node["amenity"="school"]({gaza_bbox[1]},{gaza_bbox[0]},{gaza_bbox[3]},{gaza_bbox[2]});
          way["amenity"="school"]({gaza_bbox[1]},{gaza_bbox[0]},{gaza_bbox[3]},{gaza_bbox[2]});
        );
        out center;
        """

        response = requests.post(OVERPASS_URL, data={"data": query}, timeout=45)
        response.raise_for_status()
        data = response.json()

        features = []
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            if element["type"] == "node":
                lon, lat = element["lon"], element["lat"]
            elif element["type"] == "way" and "center" in element:
                lon, lat = element["center"]["lon"], element["center"]["lat"]
            else:
                continue

            features.append({"geometry": Point(lon, lat), "name": tags.get("name", "School"), "amenity": "school"})

        if features:
            schools_gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")
            schools_gdf = filter_gaza_only(schools_gdf).to_crs(TARGET_CRS)
            print(f"   - Downloaded {len(schools_gdf)} schools from OpenStreetMap")
            edu_gdf = pd.concat([universities_gdf, schools_gdf], ignore_index=True)
            print(
                f"   - Total education facilities: {len(edu_gdf)} ({len(universities_gdf)} universities + {len(schools_gdf)} schools)"
            )
            return edu_gdf

        print("   - No schools found in OpenStreetMap, using universities only")
        return universities_gdf
    except Exception as e:
        print(f"   - Error downloading schools: {e}")
        print(f"   - Using {len(universities_gdf)} verified universities only")
        return universities_gdf


def download_gaza_hospitals():
    """Download hospital data from OpenStreetMap for Gaza Strip only."""
    cache_path = os.path.join(DATA_DIR_INFRA, "gaza_hospitals_osm.gpkg")
    if os.path.exists(cache_path):
        try:
            print("   - Loading cached Gaza hospitals...")
            cached = gpd.read_file(cache_path)
            return cached.to_crs(TARGET_CRS)
        except Exception:
            pass

    print("   - Downloading Gaza hospitals from OpenStreetMap...")
    gaza_bbox = _gaza_bbox_values()

    try:
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"="hospital"]({gaza_bbox[1]},{gaza_bbox[0]},{gaza_bbox[3]},{gaza_bbox[2]});
          node["amenity"="clinic"]({gaza_bbox[1]},{gaza_bbox[0]},{gaza_bbox[3]},{gaza_bbox[2]});
          way["amenity"="hospital"]({gaza_bbox[1]},{gaza_bbox[0]},{gaza_bbox[3]},{gaza_bbox[2]});
          way["amenity"="clinic"]({gaza_bbox[1]},{gaza_bbox[0]},{gaza_bbox[3]},{gaza_bbox[2]});
        );
        out center;
        """

        response = requests.post(OVERPASS_URL, data={"data": query}, timeout=30)
        response.raise_for_status()
        data = response.json()

        features = []
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            if element["type"] == "node":
                lon, lat = element["lon"], element["lat"]
            elif element["type"] == "way" and "center" in element:
                lon, lat = element["center"]["lon"], element["center"]["lat"]
            else:
                continue
            features.append(
                {
                    "geometry": Point(lon, lat),
                    "name": tags.get("name", "Hospital/Clinic"),
                    "amenity": tags.get("amenity", "hospital"),
                    "is_major": False,
                }
            )

        if features:
            hospitals_gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")
            hospitals_gdf = filter_gaza_only(hospitals_gdf).to_crs(TARGET_CRS)
            try:
                hospitals_gdf.to_file(cache_path, driver="GPKG")
            except Exception:
                pass
            print(f"   - Downloaded {len(hospitals_gdf)} hospitals/clinics from OpenStreetMap")
            return hospitals_gdf

        print("   - No hospitals found in OpenStreetMap")
        return gpd.GeoDataFrame(columns=["geometry", "name", "amenity", "is_major"], crs=TARGET_CRS)
    except Exception as e:
        print(f"   - Error downloading hospitals: {e}")
        return gpd.GeoDataFrame(columns=["geometry", "name", "amenity", "is_major"], crs=TARGET_CRS)
