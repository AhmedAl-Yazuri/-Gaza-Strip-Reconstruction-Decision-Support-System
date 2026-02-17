import geopandas as gpd

try:
    from .config import GAZA_BBOX
except ImportError:
    from config import GAZA_BBOX


OVERPASS_URL = "http://overpass-api.de/api/interpreter"


def _gaza_bbox_values():
    """Return Gaza bbox as [min_lon, min_lat, max_lon, max_lat]."""
    return [GAZA_BBOX["min_lon"], GAZA_BBOX["min_lat"], GAZA_BBOX["max_lon"], GAZA_BBOX["max_lat"]]


def is_within_gaza(lon, lat):
    """Check if coordinates are within Gaza Strip boundaries."""
    return (
        GAZA_BBOX["min_lon"] <= lon <= GAZA_BBOX["max_lon"]
        and GAZA_BBOX["min_lat"] <= lat <= GAZA_BBOX["max_lat"]
    )


def filter_gaza_only(gdf):
    """Filter GeoDataFrame to keep only features within Gaza Strip."""
    if gdf.empty:
        return gdf

    if gdf.crs != "EPSG:4326":
        gdf_wgs84 = gdf.to_crs("EPSG:4326")
    else:
        gdf_wgs84 = gdf.copy()

    rep_points = gdf_wgs84.geometry.representative_point()
    mask = (
        rep_points.x.between(GAZA_BBOX["min_lon"], GAZA_BBOX["max_lon"])
        & rep_points.y.between(GAZA_BBOX["min_lat"], GAZA_BBOX["max_lat"])
    )

    if "name" in gdf.columns and gdf["name"].dtype == "object":
        israeli_keywords = ["eshkol", "אשכול", "ישראל", "israel", "טרם", "מרכז"]
        for keyword in israeli_keywords:
            mask = mask & ~gdf["name"].str.contains(keyword, case=False, na=False, regex=False)

    filtered = gdf[mask].copy()
    removed = len(gdf) - len(filtered)
    if removed > 0:
        print(f"       - Filtered: {len(gdf)} -> {len(filtered)} features (removed {removed} outside Gaza)")
    return filtered
