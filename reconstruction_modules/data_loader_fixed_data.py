import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

try:
    from .config import TARGET_CRS
except ImportError:
    from config import TARGET_CRS


def get_fixed_major_hospitals():
    major_hospitals_data = {
        "name": [
            "Al-Shifa Hospital",
            "Nasser Medical Complex",
            "European Gaza Hospital",
            "Al-Quds Hospital",
            "Indonesia Hospital",
            "Kamal Adwan Hospital",
            "Al-Awda Hospital",
            "Mohammed Yousef El-Najar Hospital",
        ],
        "latitude": [31.5280, 31.3478, 31.3040, 31.5061, 31.5352, 31.5387, 31.5120, 31.2733],
        "longitude": [34.4440, 34.2933, 34.3199, 34.4306, 34.5094, 34.5013, 34.4950, 34.2731],
        "facility_type": ["major_hospital"] * 8,
        "amenity": ["hospital"] * 8,
        "is_major": [True] * 8,
    }

    df_manual = pd.DataFrame(major_hospitals_data)
    return gpd.GeoDataFrame(
        df_manual,
        geometry=gpd.points_from_xy(df_manual.longitude, df_manual.latitude),
        crs="EPSG:4326",
    ).to_crs(TARGET_CRS)


def get_fixed_gaza_universities():
    """Get verified Gaza universities with actual coordinates."""
    universities_data = {
        "name": [
            "Islamic University of Gaza",
            "Al-Azhar University - Gaza",
            "Al-Aqsa University",
            "University College of Applied Sciences",
            "Palestine Technical College - Deir al-Balah",
            "Gaza University",
        ],
        "latitude": [31.5017, 31.5244, 31.4656, 31.5156, 31.4189, 31.5089],
        "longitude": [34.4672, 34.4394, 34.3978, 34.4467, 34.3511, 34.4556],
        "amenity": ["university"] * 6,
    }

    df = pd.DataFrame(universities_data)
    return gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.longitude, df.latitude),
        crs="EPSG:4326",
    ).to_crs(TARGET_CRS)


def get_fixed_gaza_municipalities():
    """Get verified Gaza municipalities with approximate boundaries."""
    municipalities_data = [
        {"name": "Gaza City", "name_ar": "مدينة غزة", "admin_level": "8", "bbox": [34.40, 31.45, 34.50, 31.55]},
        {"name": "Khan Yunis", "name_ar": "خان يونس", "admin_level": "8", "bbox": [34.25, 31.30, 34.35, 31.40]},
        {"name": "Rafah", "name_ar": "رفح", "admin_level": "8", "bbox": [34.22, 31.22, 34.30, 31.35]},
        {"name": "Jabalia", "name_ar": "جباليا", "admin_level": "8", "bbox": [34.47, 31.50, 34.53, 31.55]},
        {"name": "Deir al-Balah", "name_ar": "دير البلح", "admin_level": "8", "bbox": [34.35, 31.40, 34.395, 31.435]},
        {"name": "Beit Lahia", "name_ar": "بيت لاهيا", "admin_level": "8", "bbox": [34.48, 31.52, 34.54, 31.58]},
        {"name": "Beit Hanoun", "name_ar": "بيت حانون", "admin_level": "8", "bbox": [34.52, 31.53, 34.54, 31.58]},
        {"name": "Nuseirat", "name_ar": "النصيرات", "admin_level": "8", "bbox": [34.395, 31.435, 34.425, 31.465]},
    ]

    features = []
    for mun in municipalities_data:
        bbox = mun["bbox"]
        polygon = Polygon(
            [
                (bbox[0], bbox[1]),
                (bbox[2], bbox[1]),
                (bbox[2], bbox[3]),
                (bbox[0], bbox[3]),
                (bbox[0], bbox[1]),
            ]
        )
        features.append(
            {
                "geometry": polygon,
                "name": mun["name"],
                "name_ar": mun["name_ar"],
                "admin_level": mun["admin_level"],
                "boundary": "administrative",
                "type": "municipality",
            }
        )

    return gpd.GeoDataFrame(features, crs="EPSG:4326").to_crs(TARGET_CRS)
