# ======================================================
# reconstruction_modules/visualization.py
# Interactive Dashboard and Map Generation
# ======================================================

from config import *
from datetime import datetime
import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster
import matplotlib.pyplot as plt
import seaborn as sns

# ======================================================
# Interactive Map Generation
# ======================================================

def create_damage_assessment_map(hex_gdf, damage_gdf, infrastructure_layers=None, output_path=None):
    """Create damage assessment map showing damage levels"""
    if hex_gdf.empty:
        return None

    wgs84_crs = "EPSG:4326"
    hex_gdf_wgs84 = hex_gdf.to_crs(wgs84_crs) if hex_gdf.crs != wgs84_crs else hex_gdf
    
    if infrastructure_layers:
        infrastructure_layers_wgs84 = {}
        for key, layer in infrastructure_layers.items():
            if layer is not None and not layer.empty:
                infrastructure_layers_wgs84[key] = layer.to_crs(wgs84_crs) if layer.crs != wgs84_crs else layer
    else:
        infrastructure_layers_wgs84 = None

    # Calculate center in projected CRS first to avoid warning
    if hex_gdf.crs != wgs84_crs:
        center_lat = hex_gdf.geometry.centroid.to_crs(wgs84_crs).y.mean()
        center_lon = hex_gdf.geometry.centroid.to_crs(wgs84_crs).x.mean()
    else:
        center_lat = hex_gdf_wgs84.geometry.centroid.y.mean()
        center_lon = hex_gdf_wgs84.geometry.centroid.x.mean()

    # Create base map with WHITE background and multiple tile options
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles='CartoDB positron'  # White background
    )
    
    # Add multiple basemap options
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer('CartoDB positron', name='Light Map (White)', show=True).add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='Dark Map (Black)').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        overlay=False,
        control=True
    ).add_to(m)

    # Color zones by damage level
    def get_damage_color(damage_count):
        if damage_count >= 400: return '#8B0000'  # Dark red - Severe
        elif damage_count >= 200: return '#FF0000'  # Red - High
        elif damage_count >= 100: return '#FF4500'  # Orange red - Moderate-High
        elif damage_count >= 50: return '#FFA500'   # Orange - Moderate
        elif damage_count >= 10: return '#FFFF00'   # Yellow - Low-Moderate
        elif damage_count > 0: return '#90EE90'     # Light green - Low
        else: return '#00FF00'                       # Green - No damage

    # Add damage zones
    for idx, row in hex_gdf_wgs84.iterrows():
        damage_count = row.get('damage_count', 0)
        coords = [[y, x] for x, y in row.geometry.exterior.coords]
        
        popup_content = f"""
        <b>🔥 DAMAGE ASSESSMENT</b><br>
        <b>Zone:</b> {row.get('zone_id', f'ZONE-{idx+1:03d}')}<br>
        <b>Damage Sites:</b> {damage_count}<br>
        <b>Municipality:</b> {row.get('primary_municipality', 'Unknown')}<br>
        <b>Damage Level:</b> {'Severe' if damage_count >= 400 else 'High' if damage_count >= 200 else 'Moderate' if damage_count >= 50 else 'Low' if damage_count > 0 else 'No Damage'}
        """
        
        color = get_damage_color(damage_count)
        folium.Polygon(
            locations=coords,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.5,
            popup=popup_content,
            weight=1
        ).add_to(m)

    # Add all infrastructure layers
    if infrastructure_layers_wgs84:
        # Hospitals
        if 'hospitals' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['hospitals'].empty:
            hospitals_group = folium.FeatureGroup(name='🏥 Hospitals', show=True).add_to(m)
            for _, facility in infrastructure_layers_wgs84['hospitals'].iterrows():
                lat, lon = facility.geometry.centroid.y, facility.geometry.centroid.x
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>🏥 {facility.get('name', 'Hospital')}</b>",
                    icon=folium.Icon(color='red', icon='plus', prefix='fa')
                ).add_to(hospitals_group)
        
        # Schools
        if 'schools' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['schools'].empty:
            schools_group = folium.FeatureGroup(name='🏫 Schools', show=True).add_to(m)
            for _, facility in infrastructure_layers_wgs84['schools'].head(100).iterrows():
                lat, lon = facility.geometry.centroid.y, facility.geometry.centroid.x
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>🏫 {facility.get('name', 'School')}</b>",
                    icon=folium.Icon(color='blue', icon='graduation-cap', prefix='fa')
                ).add_to(schools_group)
        
        # Universities
        if 'universities' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['universities'].empty:
            universities_group = folium.FeatureGroup(name='🎓 Universities', show=True).add_to(m)
            for _, facility in infrastructure_layers_wgs84['universities'].iterrows():
                lat, lon = facility.geometry.centroid.y, facility.geometry.centroid.x
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>🎓 {facility.get('name', 'University')}</b>",
                    icon=folium.Icon(color='darkblue', icon='university', prefix='fa')
                ).add_to(universities_group)
        
        # Water Utilities
        if 'water_util' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['water_util'].empty:
            water_group = folium.FeatureGroup(name='💧 Water Utilities', show=True).add_to(m)
            for _, facility in infrastructure_layers_wgs84['water_util'].iterrows():
                lat, lon = facility.geometry.centroid.y, facility.geometry.centroid.x
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>💧 {facility.get('name', 'Water Facility')}</b>",
                    icon=folium.Icon(color='lightblue', icon='tint', prefix='fa')
                ).add_to(water_group)
        
        
        # Streets - Damage severity visualization
        if 'streets' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['streets'].empty:
            # Damage level groups
            no_damage_group = folium.FeatureGroup(name='✅ Streets - No Damage', show=False).add_to(m)
            low_damage_group = folium.FeatureGroup(name='🟡 Streets - Low Damage', show=True).add_to(m)
            medium_damage_group = folium.FeatureGroup(name='🟠 Streets - Medium Damage', show=True).add_to(m)
            high_damage_group = folium.FeatureGroup(name='🔴 Streets - High Damage', show=True).add_to(m)
            severe_damage_group = folium.FeatureGroup(name='⚫ Streets - Severe Damage', show=True).add_to(m)
            
            streets_sorted = infrastructure_layers_wgs84['streets'].sort_values('damage_severity', ascending=False)
            
            # Count streets by damage level
            damage_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
            for _, street in infrastructure_layers_wgs84['streets'].iterrows():
                damage = int(street.get('damage_severity', 0))
                if damage in damage_counts:
                    damage_counts[damage] += 1
            
            print(f"   - Street damage distribution: No damage={damage_counts[0]}, Low={damage_counts[1]}, Medium={damage_counts[2]}, High={damage_counts[3]}, Severe={damage_counts[4]}")
            
            count = 0
            for _, street in streets_sorted.iterrows():
                if count >= 5000:
                    break
                
                damage = street.get('damage_severity', 0)
                if damage == 0:
                    continue
                    
                road_type = street.get('RoadType', 'Unknown')
                municipality = street.get('municipality', 'Unknown')
                length_km = street.get('Length_km', 0)
                
                if damage >= 4:
                    color, weight, opacity, target_group = '#000000', 8, 1.0, severe_damage_group
                    damage_level = 'Severe (4)'
                elif damage >= 3:
                    color, weight, opacity, target_group = '#8B0000', 7, 0.95, high_damage_group
                    damage_level = 'High (3)'
                elif damage >= 2:
                    color, weight, opacity, target_group = '#FF8000', 6, 0.9, medium_damage_group
                    damage_level = 'Medium (2)'
                else:
                    color, weight, opacity, target_group = '#FFD700', 5, 0.85, low_damage_group
                    damage_level = 'Low (1)'
                
                popup_html = f"""
                <div style="font-family: Arial; min-width: 280px;">
                    <h4 style="margin: 5px 0; color: {color};">💥 Street Damage</h4>
                    <b>Type:</b> {road_type}<br>
                    <b>Length:</b> {length_km:.2f} km<br>
                    <b>Damage:</b> {damage_level}<br>
                </div>
                """
                
                try:
                    if street.geometry.geom_type == 'MultiLineString':
                        for line in street.geometry.geoms:
                            coords = [(coord[1], coord[0]) for coord in line.coords]
                            if len(coords) >= 2:
                                folium.PolyLine(
                                    locations=coords,
                                    color=color,
                                    weight=weight,
                                    opacity=opacity,
                                    popup=folium.Popup(popup_html, max_width=300)
                                ).add_to(target_group)
                    elif street.geometry.geom_type == 'LineString':
                        coords = [(coord[1], coord[0]) for coord in street.geometry.coords]
                        if len(coords) >= 2:
                            folium.PolyLine(
                                locations=coords,
                                color=color,
                                weight=weight,
                                opacity=opacity,
                                popup=folium.Popup(popup_html, max_width=300)
                            ).add_to(target_group)
                    count += 1
                except:
                    continue

    # Add professional title
    title_html = '''
    <div style="position: fixed; top: 10px; left: 50px; width: 500px; z-index:9999;
                background-color: rgba(255,255,255,0.95); border:3px solid #FF0000; border-radius: 8px;
                font-size:16px; padding: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.3);">
        <h3 style="margin: 0; color: #8B0000;">🔥 Gaza Strip - Damage Assessment Map</h3>
        <p style="margin: 5px 0; font-size: 13px; color: #333;">
        Comprehensive damage assessment showing severity levels across Gaza Strip.
        Click on zones for detailed information.
        </p>
        <p style="margin: 5px 0; font-size: 11px; color: #666;">
        Data: UNOSAT | Generated: {date}
        </p>
    </div>
    '''.format(date=datetime.now().strftime('%Y-%m-%d'))
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Add professional legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 240px; height: 240px;
                background-color: rgba(255,255,255,0.95); border:3px solid #FF0000; border-radius: 8px;
                z-index:9999; font-size:13px; padding: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.3);">
        <h4 style="margin: 0 0 10px 0; color: #8B0000;"><b>🔥 Damage Assessment</b></h4>
        <p style="margin: 5px 0;"><span style="color:#8B0000; font-size: 18px;">●</span> <b>Severe</b> (400+ sites)</p>
        <p style="margin: 5px 0;"><span style="color:#FF0000; font-size: 18px;">●</span> <b>High</b> (200-399)</p>
        <p style="margin: 5px 0;"><span style="color:#FF4500; font-size: 18px;">●</span> <b>Moderate-High</b> (100-199)</p>
        <p style="margin: 5px 0;"><span style="color:#FFA500; font-size: 18px;">●</span> <b>Moderate</b> (50-99)</p>
        <p style="margin: 5px 0;"><span style="color:#FFFF00; font-size: 18px;">●</span> <b>Low-Moderate</b> (10-49)</p>
        <p style="margin: 5px 0;"><span style="color:#90EE90; font-size: 18px;">●</span> <b>Low</b> (1-9)</p>
        <p style="margin: 5px 0;"><span style="color:#00FF00; font-size: 18px;">●</span> <b>No Damage</b></p>
        <hr style="margin: 10px 0; border: 1px solid #ddd;">
        <p style="font-size: 11px; color: #666; margin: 5px 0;">
        <b>Use layer control</b> to toggle infrastructure visibility
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    folium.LayerControl().add_to(m)
    
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"gaza_damage_assessment_{timestamp}.html"
    
    m.save(output_path)
    print(f"   - Damage assessment map saved to {output_path}")
    return output_path

def create_reconstruction_priority_map(hex_gdf, projects_df, infrastructure_layers=None, output_path=None):
    """Create reconstruction priority map showing reconstruction priorities"""
    if hex_gdf.empty:
        return None

    wgs84_crs = "EPSG:4326"
    hex_gdf_wgs84 = hex_gdf.to_crs(wgs84_crs) if hex_gdf.crs != wgs84_crs else hex_gdf
    
    if infrastructure_layers:
        infrastructure_layers_wgs84 = {}
        for key, layer in infrastructure_layers.items():
            if layer is not None and not layer.empty:
                infrastructure_layers_wgs84[key] = layer.to_crs(wgs84_crs) if layer.crs != wgs84_crs else layer
    else:
        infrastructure_layers_wgs84 = None

    # Calculate center in projected CRS first to avoid warning
    if hex_gdf.crs != wgs84_crs:
        center_lat = hex_gdf.geometry.centroid.to_crs(wgs84_crs).y.mean()
        center_lon = hex_gdf.geometry.centroid.to_crs(wgs84_crs).x.mean()
    else:
        center_lat = hex_gdf_wgs84.geometry.centroid.y.mean()
        center_lon = hex_gdf_wgs84.geometry.centroid.x.mean()

    # Create base map with WHITE background
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles='CartoDB positron'
    )
    
    # Add basemap options
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer('CartoDB positron', name='Light Map', show=True).add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='Dark Map').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        overlay=False,
        control=True
    ).add_to(m)

    # Color zones by reconstruction priority
    max_rank = len(hex_gdf_wgs84)
    def get_priority_color(rank):
        if rank <= max_rank * 0.1: return '#8B0000'    # Dark red - Critical
        elif rank <= max_rank * 0.2: return '#FF0000'  # Red - Very High
        elif rank <= max_rank * 0.4: return '#FF8000'  # Orange - High
        elif rank <= max_rank * 0.6: return '#FFFF00'  # Yellow - Medium
        elif rank <= max_rank * 0.8: return '#80FF00'  # Light green - Low
        else: return '#00FF00'                          # Green - Very Low

    # Add priority zones
    for idx, row in hex_gdf_wgs84.iterrows():
        coords = [[y, x] for x, y in row.geometry.exterior.coords]
        
        popup_content = f"""
        <b>🏗️ RECONSTRUCTION PRIORITY</b><br>
        <b>Zone:</b> {row.get('zone_id', f'ZONE-{idx+1:03d}')}<br>
        <b>Priority Rank:</b> #{idx+1}<br>
        <b>AI Score:</b> {row.get('ai_score', 0):.3f}<br>
        <b>Municipality:</b> {row.get('primary_municipality', 'Unknown')}<br>
        <b>Strategy:</b> {row.get('rebuilding_strategy', {}).get('strategy', 'Unknown')}
        """
        
        color = get_priority_color(idx+1)
        folium.Polygon(
            locations=coords,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            popup=popup_content,
            weight=1
        ).add_to(m)

    # Add all infrastructure layers
    if infrastructure_layers_wgs84:
        # Add ALL streets as background first
        if 'streets' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['streets'].empty:
            all_streets_group = folium.FeatureGroup(name='🛣️ All Streets Network', show=True).add_to(m)
            street_count_bg = 0
            for idx, street in infrastructure_layers_wgs84['streets'].iterrows():
                try:
                    if street.geometry.geom_type == 'MultiLineString':
                        for line in street.geometry.geoms:
                            coords = [(coord[1], coord[0]) for coord in line.coords]
                            if len(coords) >= 2:
                                folium.PolyLine(
                                    locations=coords,
                                    color='#B0B0B0',
                                    weight=1.5,
                                    opacity=0.35
                                ).add_to(all_streets_group)
                        street_count_bg += 1
                    elif street.geometry.geom_type == 'LineString':
                        coords = [(coord[1], coord[0]) for coord in street.geometry.coords]
                        if len(coords) >= 2:
                            folium.PolyLine(
                                locations=coords,
                                color='#B0B0B0',
                                weight=1.5,
                                opacity=0.35
                            ).add_to(all_streets_group)
                            street_count_bg += 1
                except:
                    continue
            print(f"   - Added {street_count_bg:,} streets to reconstruction priority map")
        
        # Hospitals
        if 'hospitals' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['hospitals'].empty:
            hospitals_group = folium.FeatureGroup(name='🏥 Hospitals', show=True).add_to(m)
            for _, facility in infrastructure_layers_wgs84['hospitals'].iterrows():
                lat, lon = facility.geometry.centroid.y, facility.geometry.centroid.x
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>🏥 {facility.get('name', 'Hospital')}</b>",
                    icon=folium.Icon(color='red', icon='plus', prefix='fa')
                ).add_to(hospitals_group)
        
        # Schools
        if 'schools' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['schools'].empty:
            schools_group = folium.FeatureGroup(name='🏫 Schools', show=True).add_to(m)
            for _, facility in infrastructure_layers_wgs84['schools'].head(100).iterrows():
                lat, lon = facility.geometry.centroid.y, facility.geometry.centroid.x
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>🏫 {facility.get('name', 'School')}</b>",
                    icon=folium.Icon(color='blue', icon='graduation-cap', prefix='fa')
                ).add_to(schools_group)
        
        # Universities
        if 'universities' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['universities'].empty:
            universities_group = folium.FeatureGroup(name='🎓 Universities', show=True).add_to(m)
            for _, facility in infrastructure_layers_wgs84['universities'].iterrows():
                lat, lon = facility.geometry.centroid.y, facility.geometry.centroid.x
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>🎓 {facility.get('name', 'University')}</b>",
                    icon=folium.Icon(color='darkblue', icon='university', prefix='fa')
                ).add_to(universities_group)
        
        # Water Utilities
        if 'water_util' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['water_util'].empty:
            water_group = folium.FeatureGroup(name='💧 Water Utilities', show=True).add_to(m)
            for _, facility in infrastructure_layers_wgs84['water_util'].iterrows():
                lat, lon = facility.geometry.centroid.y, facility.geometry.centroid.x
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>💧 {facility.get('name', 'Water Facility')}</b>",
                    icon=folium.Icon(color='lightblue', icon='tint', prefix='fa')
                ).add_to(water_group)
        
        
        # Streets - Reconstruction priorities
        if 'streets' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['streets'].empty:
            critical_streets_group = folium.FeatureGroup(name='🔴 Streets - Critical Priority', show=True).add_to(m)
            high_streets_group = folium.FeatureGroup(name='🟠 Streets - High Priority', show=True).add_to(m)
            medium_streets_group = folium.FeatureGroup(name='🟡 Streets - Medium Priority', show=True).add_to(m)
            low_streets_group = folium.FeatureGroup(name='🟢 Streets - Low Priority', show=False).add_to(m)
            
            damaged_streets = infrastructure_layers_wgs84['streets'][infrastructure_layers_wgs84['streets'].get('damage_severity', 0) > 0]
            streets_sorted = damaged_streets.sort_values('reconstruction_priority', ascending=False)
            
            count = 0
            for _, street in streets_sorted.iterrows():
                if count >= 5000:
                    break
                
                damage = street.get('damage_severity', 0)
                road_type = street.get('RoadType', 'Unknown')
                municipality = street.get('municipality', 'Unknown')
                length_km = street.get('Length_km', 0)
                priority_score = street.get('reconstruction_priority', 0)
                
                if priority_score >= 30:
                    color, weight, opacity, target_group = '#8B0000', 10, 1.0, critical_streets_group
                    priority_level = 'Critical'
                elif priority_score >= 20:
                    color, weight, opacity, target_group = '#FF4500', 8, 0.95, high_streets_group
                    priority_level = 'High'
                elif priority_score >= 10:
                    color, weight, opacity, target_group = '#FFA500', 6, 0.9, medium_streets_group
                    priority_level = 'Medium'
                else:
                    color, weight, opacity, target_group = '#FFD700', 4, 0.85, low_streets_group
                    priority_level = 'Low'
                
                popup_html = f"""
                <div style="font-family: Arial; min-width: 300px;">
                    <h4 style="margin: 5px 0; color: {color};">🏗️ Street Reconstruction</h4>
                    <b>Type:</b> {road_type}<br>
                    <b>Length:</b> {length_km:.2f} km<br>
                    <b>Priority:</b> {priority_level}<br>
                    <b>Damage:</b> {damage:.1f}/4<br>
                </div>
                """
                
                try:
                    if street.geometry.geom_type == 'MultiLineString':
                        for line in street.geometry.geoms:
                            coords = [(coord[1], coord[0]) for coord in line.coords]
                            if len(coords) >= 2:
                                folium.PolyLine(
                                    locations=coords,
                                    color=color,
                                    weight=weight,
                                    opacity=opacity,
                                    popup=folium.Popup(popup_html, max_width=320)
                                ).add_to(target_group)
                    elif street.geometry.geom_type == 'LineString':
                        coords = [(coord[1], coord[0]) for coord in street.geometry.coords]
                        if len(coords) >= 2:
                            folium.PolyLine(
                                locations=coords,
                                color=color,
                                weight=weight,
                                opacity=opacity,
                                popup=folium.Popup(popup_html, max_width=320)
                            ).add_to(target_group)
                    count += 1
                except:
                    continue


    # Professional title
    title_html = '''
    <div style="position: fixed; top: 10px; left: 50px; width: 550px; z-index:9999;
                background-color: rgba(255,255,255,0.97); border:3px solid #0066CC; border-radius: 10px;
                font-size:16px; padding: 18px; box-shadow: 0 6px 12px rgba(0,0,0,0.25);">
        <h3 style="margin: 0; color: #0066CC; font-size: 18px; border-bottom: 2px solid #0066CC; padding-bottom: 8px;">
            🏗️ Gaza Strip - Reconstruction Priority Map
        </h3>
        <p style="margin: 10px 0 5px 0; font-size: 13px; color: #333; line-height: 1.5;">
        <b>Priority zones</b> color-coded by reconstruction urgency.<br>
        <b>Complete street network</b> displayed with infrastructure layers.
        </p>
        <p style="margin: 8px 0 0 0; font-size: 11px; color: #666;">
        Data: UNOSAT | Generated: {date}
        </p>
    </div>
    '''.format(date=datetime.now().strftime('%Y-%m-%d'))
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Professional legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 280px;
                background-color: rgba(255,255,255,0.97); border:3px solid #0066CC; border-radius: 10px;
                z-index:9999; font-size:13px; padding: 18px; box-shadow: 0 6px 12px rgba(0,0,0,0.25);">
        <h4 style="margin: 0 0 12px 0; color: #0066CC; font-size: 16px; border-bottom: 2px solid #0066CC; padding-bottom: 8px;">
            🏗️ Reconstruction Priority
        </h4>
        <p style="margin: 6px 0; line-height: 1.8;">
            <span style="color:#8B0000; font-size: 18px;">●</span> <b>Critical</b> - Top 10%<br>
            <span style="color:#FF0000; font-size: 18px;">●</span> <b>Very High</b> - 10-20%<br>
            <span style="color:#FF8000; font-size: 18px;">●</span> <b>High</b> - 20-40%<br>
            <span style="color:#FFFF00; font-size: 18px;">●</span> <b>Medium</b> - 40-60%<br>
            <span style="color:#80FF00; font-size: 18px;">●</span> <b>Low</b> - 60-80%<br>
            <span style="color:#00FF00; font-size: 18px;">●</span> <b>Very Low</b> - 80-100%
        </p>
        <div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid #ddd;">
            <p style="font-size: 11px; color: #666; margin: 0;">
                💡 <b>Tip:</b> Use layer control to toggle infrastructure
            </p>
        </div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    folium.LayerControl().add_to(m)
    
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"gaza_reconstruction_priority_{timestamp}.html"
    
    import os
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    m.save(output_path)
    print(f"   - Reconstruction priority map saved to {output_path}")
    return output_path

def create_population_density_map(hex_gdf, infrastructure_layers=None, output_path=None):
    """Create population density map showing population distribution"""
    if hex_gdf.empty:
        return None

    wgs84_crs = "EPSG:4326"
    hex_gdf_wgs84 = hex_gdf.to_crs(wgs84_crs) if hex_gdf.crs != wgs84_crs else hex_gdf
    
    if infrastructure_layers:
        infrastructure_layers_wgs84 = {}
        for key, layer in infrastructure_layers.items():
            if layer is not None and not layer.empty:
                infrastructure_layers_wgs84[key] = layer.to_crs(wgs84_crs) if layer.crs != wgs84_crs else layer
    else:
        infrastructure_layers_wgs84 = None

    center_lat = hex_gdf_wgs84.geometry.centroid.y.mean()
    center_lon = hex_gdf_wgs84.geometry.centroid.x.mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles='CartoDB dark_matter')

    # Color zones by population density - IMPROVED COLOR SCHEME
    def get_population_color(density, is_idp_hotspot=False):
        if is_idp_hotspot:
            return '#8B0000'  # Dark red for IDP hotspots
        if density > 50000: return '#660000'    # Very Dark Red - Extreme Crisis
        elif density > 30000: return '#8B0000'  # Dark red - CRISIS
        elif density > 20000: return '#B22222'  # Fire Brick - Very High
        elif density > 15000: return '#DC143C'  # Crimson - Very High
        elif density > 10000: return '#FF4500'  # Orange Red - High
        elif density > 8000: return '#FF6347'   # Tomato - High
        elif density > 5000: return '#FFA500'   # Orange - Medium-High
        elif density > 3000: return '#FFD700'   # Gold - Medium
        elif density > 2000: return '#F0E68C'   # Khaki - Medium-Low
        elif density > 1000: return '#ADFF2F'   # Green Yellow - Low-Medium
        elif density > 500: return '#90EE90'    # Light Green - Low
        elif density > 100: return '#E8E8E8'    # Very Light Gray - Very Low
        elif density > 0: return '#D3D3D3'      # Light Gray - Nearly Empty
        else: return '#FFFFFF'                  # White - Evacuated

    # Add population zones
    for idx, row in hex_gdf_wgs84.iterrows():
        coords = [[y, x] for x, y in row.geometry.exterior.coords]
        
        pop_total = row.get('population_total', 0)
        pop_density = row.get('population_density', 0)
        pop_prewar = row.get('population_prewar', 0)
        is_idp = row.get('is_idp_hotspot', False)
        
        # Get area from original projected data for accuracy
        if 'population_area_km2' in hex_gdf.columns:
            zone_area_km2 = hex_gdf.loc[idx, 'population_area_km2']
        else:
            # Fallback: calculate from original projected geometry
            zone_area_km2 = hex_gdf.loc[idx, 'geometry'].area / 1_000_000
        
        # Calculate displacement
        if pop_prewar > 0:
            displacement = ((pop_prewar - pop_total) / pop_prewar) * 100
        else:
            displacement = 0
        
        # Density classification
        if pop_density > 50000:
            density_class = '🔴 EXTREME CRISIS - Catastrophic Overcrowding'
        elif pop_density > 30000:
            density_class = '🔴 CRISIS - Extreme Overcrowding'
        elif pop_density > 20000:
            density_class = '🔴 VERY HIGH - Critical Density'
        elif pop_density > 15000:
            density_class = '🟠 URGENT - Very High Density'
        elif pop_density > 10000:
            density_class = '🟠 HIGH - Above Normal'
        elif pop_density > 8000:
            density_class = '🟡 HIGH - Above Normal'
        elif pop_density > 5000:
            density_class = '🟡 MEDIUM-HIGH'
        elif pop_density > 3000:
            density_class = '🟢 MEDIUM'
        elif pop_density > 2000:
            density_class = '🟢 MEDIUM-LOW'
        elif pop_density > 1000:
            density_class = '🟢 LOW'
        elif pop_density > 500:
            density_class = '⚪ VERY LOW'
        elif pop_density > 0:
            density_class = '⚫ NEARLY EMPTY - Evacuated'
        else:
            density_class = '⚫ NO DATA - Evacuated'
        
        popup_content = f"""
        <div style="font-family: Arial; font-size: 13px; min-width: 280px;">
        <h4 style="margin: 5px 0; color: #333; border-bottom: 2px solid #666;">👥 POPULATION ANALYSIS</h4>
        
        <b>📍 Location:</b><br>
        • Zone: {row.get('zone_id', f'ZONE-{idx+1:03d}')}<br>
        • Municipality: <b>{row.get('primary_municipality', 'Unknown')}</b><br>
        • Area: {zone_area_km2:.2f} km²<br>
        <br>
        
        <b>👨‍👩‍👧‍👦 Population Data (2024-2025):</b><br>
        • Current Population: <b style="color: #0066cc;">{pop_total:,.0f}</b> people<br>
        • Pre-war Population: <b>{pop_prewar:,.0f}</b> people<br>
        • Displaced: <b style="color: #cc0000;">{displacement:.1f}%</b> ({abs(pop_prewar - pop_total):,.0f} people)<br>
        <br>
        
        <b>📊 Density Analysis:</b><br>
        • Density: <b style="color: #ff6600;">{pop_density:,.0f}</b> people/km²<br>
        • Classification: {density_class}<br>
        {'<b style="color: red; background: #ffe6e6; padding: 3px;">⚠️ IDP HOTSPOT - EXTREME OVERCROWDING</b><br>' if is_idp else ''}
        <br>
        
        <b>💥 Damage Assessment:</b><br>
        • Damage Sites: <b>{row.get('damage_count', 0)}</b><br>
        • Priority Rank: <b>#{idx+1}</b><br>
        </div>
        """
        
        color = get_population_color(pop_density, is_idp)
        folium.Polygon(
            locations=coords,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85 if is_idp else 0.75,  # More opaque for better visibility
            popup=popup_content,
            weight=3 if is_idp else 1.5
        ).add_to(m)

    # Add infrastructure layers
    if infrastructure_layers_wgs84:
        if 'hospitals' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['hospitals'].empty:
            hospitals_group = folium.FeatureGroup(name='🏥 Hospitals', show=True).add_to(m)
            for _, facility in infrastructure_layers_wgs84['hospitals'].iterrows():
                lat, lon = facility.geometry.centroid.y, facility.geometry.centroid.x
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>🏥 {facility.get('name', 'Hospital')}</b>",
                    icon=folium.Icon(color='red', icon='plus', prefix='fa')
                ).add_to(hospitals_group)
        
        if 'schools' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['schools'].empty:
            schools_group = folium.FeatureGroup(name='🏫 Schools', show=False).add_to(m)
            for _, facility in infrastructure_layers_wgs84['schools'].head(100).iterrows():
                lat, lon = facility.geometry.centroid.y, facility.geometry.centroid.x
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>🏫 {facility.get('name', 'School')}</b>",
                    icon=folium.Icon(color='blue', icon='graduation-cap', prefix='fa')
                ).add_to(schools_group)

    # Add legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 240px; height: 240px;
                background-color: white; border:2px solid #333; border-radius: 8px; z-index:9999;
                font-size:12px; padding: 15px;">
        <h4><b>👥 Population Density (2024-2025)</b></h4>
        <p><span style="color:#8B0000;">●</span> <b>CRISIS (>30,000/km²)</b></p>
        <p><span style="color:#DC143C;">●</span> Very High (15,000-30,000)</p>
        <p><span style="color:#FF4500;">●</span> High (8,000-15,000)</p>
        <p><span style="color:#FFA500;">●</span> Medium-High (5,000-8,000)</p>
        <p><span style="color:#FFD700;">●</span> Medium (2,000-5,000)</p>
        <p><span style="color:#ADFF2F;">●</span> Low-Medium (500-2,000)</p>
        <p><span style="color:#E8E8E8;">●</span> Very Low (100-500)</p>
        <p><span style="color:#D3D3D3;">●</span> Nearly Empty (0-100)</p>
        <p><span style="color:#FFFFFF; border:1px solid #999;">●</span> Evacuated</p>
        <hr style="margin: 5px 0;">
        <p style="font-size:10px;"><i>Source: UN OCHA + Estimates</i></p>
        <p style="font-size:9px; color:red;"><b>⚠️ Red zones: IDP concentration</b></p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    folium.LayerControl().add_to(m)
    
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"gaza_population_density_{timestamp}.html"
    
    m.save(output_path)
    print(f"   - Population density map saved to {output_path}")
    return output_path

def create_interactive_map(hex_gdf, damage_gdf=None, projects_df=None, infrastructure_layers=None, output_path=None):
    """Create interactive Folium map with reconstruction priorities and selected projects"""
    if hex_gdf.empty:
        print("   - Warning: No data available for map generation")
        return None

    # Ensure all data is in WGS84 for Folium
    wgs84_crs = "EPSG:4326"
    hex_gdf_wgs84 = hex_gdf.to_crs(wgs84_crs) if hex_gdf.crs != wgs84_crs else hex_gdf

    if damage_gdf is not None and not damage_gdf.empty:
        damage_gdf_wgs84 = damage_gdf.to_crs(wgs84_crs) if damage_gdf.crs != wgs84_crs else damage_gdf
    else:
        damage_gdf_wgs84 = None

    if infrastructure_layers:
        infrastructure_layers_wgs84 = {}
        for key, layer in infrastructure_layers.items():
            if layer is not None and not layer.empty:
                infrastructure_layers_wgs84[key] = layer.to_crs(wgs84_crs) if layer.crs != wgs84_crs else layer
            else:
                infrastructure_layers_wgs84[key] = layer
    else:
        infrastructure_layers_wgs84 = None

    # Calculate center point (in projected CRS for accuracy, then convert to WGS84)
    if hex_gdf.crs != wgs84_crs:
        # Calculate centroids in projected CRS for accuracy
        centroids_projected = hex_gdf.geometry.centroid
        # Convert centroids to WGS84 for map coordinates
        centroids_wgs84 = centroids_projected.to_crs(wgs84_crs)
        center_lat = centroids_wgs84.y.mean()
        center_lon = centroids_wgs84.x.mean()
    else:
        # Already in WGS84
        center_lat = hex_gdf.geometry.centroid.y.mean()
        center_lon = hex_gdf.geometry.centroid.x.mean()

    # Create base map with better tiles
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13,
                   tiles='CartoDB dark_matter')

    # Add satellite imagery option
    folium.TileLayer('OpenStreetMap').add_to(m)
    folium.TileLayer(
        tiles='https://stamen-tiles-{s}.a.ssl.fastly.net/terrain/{z}/{x}/{y}.png',
        attr='Map tiles by <a href="http://stamen.com">Stamen Design</a>, <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a> — Map data © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        name='Stamen Terrain'
    ).add_to(m)
    folium.TileLayer(
        tiles='https://stamen-tiles-{s}.a.ssl.fastly.net/toner/{z}/{x}/{y}.png',
        attr='Map tiles by <a href="http://stamen.com">Stamen Design</a>, <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a> — Map data © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        name='Stamen Toner'
    ).add_to(m)

    # Fit map bounds to Gaza Strip area only, avoiding neighboring territories
    bounds = hex_gdf_wgs84.total_bounds
    # Adjust bounds to avoid showing Egyptian and Israeli territories
    # Reduce eastern bound slightly to avoid Israeli territory
    east_bound = min(bounds[2], 34.55)  # Gaza-Israel border is ~34.6°E, inset slightly
    south_bound = max(bounds[1], 31.25)  # Avoid Egyptian territory in south
    m.fit_bounds([[south_bound, bounds[0]], [bounds[3], east_bound]])

    # Color scheme for priority levels
    def get_priority_color(rank, max_rank):
        if rank <= max_rank * 0.2:  # Top 20%
            return '#ff0000'  # Red - Critical
        elif rank <= max_rank * 0.4:  # Next 20%
            return '#ff8000'  # Orange - High
        elif rank <= max_rank * 0.6:  # Next 20%
            return '#ffff00'  # Yellow - Medium-High
        elif rank <= max_rank * 0.8:  # Next 20%
            return '#80ff00'  # Light Green - Medium
        else:
            return '#00ff00'  # Green - Low

    # Add hexagonal zones
    max_rank = len(hex_gdf_wgs84)
    for idx, row in hex_gdf_wgs84.iterrows():
        # Convert geometry to coordinates
        if hasattr(row.geometry, 'exterior'):
            coords = [[y, x] for x, y in row.geometry.exterior.coords]
        else:
            # Handle centroid for point geometry
            coords = [[row.geometry.centroid.y, row.geometry.centroid.x]]

        # Create popup content
        popup_content = f"""
        <b>Zone ID:</b> {row.get('zone_id', f'ZONE-{idx+1:03d}')}<br>
        <b>Priority Rank:</b> {idx+1}<br>
        <b>AI Score:</b> {row.get('ai_score', 0):.3f}<br>
        <b>Damage Sites:</b> {row.get('damage_count', 0)}<br>
        <b>Municipality:</b> {row.get('primary_municipality', 'Unknown')}<br>
        <b>Strategy:</b> {row.get('rebuilding_strategy', {}).get('strategy', 'Unknown')}<br>
        <b>Expert Notes:</b> {row.get('expert_explanation', '')[:100]}...
        """

        # Add infrastructure counts to popup
        infra_counts = []
        if row.get('hospitals_count', 0) > 0:
            infra_counts.append(f"Hospitals: {int(row.get('hospitals_count', 0))}")
        if row.get('schools_count', 0) > 0:
            infra_counts.append(f"Schools: {int(row.get('schools_count', 0))}")
        if row.get('universities_count', 0) > 0:
            infra_counts.append(f"Universities: {int(row.get('universities_count', 0))}")
        if row.get('water_util_count', 0) > 0:
            infra_counts.append(f"Water Facilities: {int(row.get('water_util_count', 0))}")
        if row.get('fuel_util_count', 0) > 0:
            infra_counts.append(f"Fuel Facilities: {int(row.get('fuel_util_count', 0))}")
        if row.get('streets_count', 0) > 0:
            infra_counts.append(f"Street Segments: {int(row.get('streets_count', 0))}")
        if row.get('municipalities_count', 0) > 0:
            infra_counts.append(f"Municipal Buildings: {int(row.get('municipalities_count', 0))}")

        if infra_counts:
            popup_content += f"<br><b>Infrastructure:</b><br>{'<br>'.join(infra_counts)}"

        # Add polygon/marker
        color = get_priority_color(idx+1, max_rank)

        if len(coords) > 2:  # Polygon
            folium.Polygon(
                locations=coords,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.3,
                popup=popup_content,
                weight=2
            ).add_to(m)
        else:  # Point
            folium.CircleMarker(
                location=coords[0],
                radius=5,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                popup=popup_content
            ).add_to(m)

    # Add infrastructure markers if layers are provided
    if infrastructure_layers_wgs84:
        # Add hospitals/clinics
        if 'hospitals' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['hospitals'].empty:
            hospitals_group = folium.FeatureGroup(name='🏥 Hospitals & Clinics', show=True).add_to(m)
            for _, facility in infrastructure_layers_wgs84['hospitals'].head(100).iterrows():  # Increased limit
                if hasattr(facility.geometry, 'centroid'):
                    lat, lon = facility.geometry.centroid.y, facility.geometry.centroid.x
                else:
                    lat, lon = facility.geometry.y, facility.geometry.x

                name = facility.get('name', 'Hospital/Clinic')
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>🏥 Hospital/Clinic:</b><br>{name}<br><i>Critical healthcare facility</i>",
                    icon=folium.Icon(color='red', icon='plus', prefix='fa')
                ).add_to(hospitals_group)

        # Add streets as polylines with damage indication
        if 'streets' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['streets'].empty:
            streets_group = folium.FeatureGroup(name='🛣️ Street Network', show=True).add_to(m)
            damaged_streets_group = folium.FeatureGroup(name='💥 Damaged Streets', show=True).add_to(m)
            strategic_streets_group = folium.FeatureGroup(name='⭐ Strategic Streets', show=True).add_to(m)
            
            print(f"   - Adding {len(infrastructure_layers_wgs84['streets'])} streets to map...")
            
            street_count = 0
            damaged_count = 0
            strategic_count = 0
            
            # Sort by reconstruction priority (highest first)
            streets_sorted = infrastructure_layers_wgs84['streets'].sort_values('reconstruction_priority', ascending=False)
            
            for _, street in streets_sorted.iterrows():
                if street_count >= 5000:  # Much higher limit for visibility
                    break

                try:
                    is_damaged = street.get('damage_severity', 0) > 0
                    is_strategic = street.get('near_hospital', False) or street.get('is_major_artery', False)
                    road_type = street.get('RoadType', 'Unknown')
                    municipality = street.get('municipality', street.get('Governorate', 'Unknown'))
                    priority = street.get('reconstruction_priority', 0)
                    
                    # Determine target group and styling
                    if is_strategic and is_damaged:
                        color = 'darkred'
                        weight = 8
                        opacity = 1.0
                        target_group = strategic_streets_group
                        strategic_count += 1
                    elif is_damaged:
                        color = 'red'
                        weight = 6
                        opacity = 0.9
                        target_group = damaged_streets_group
                        damaged_count += 1
                    elif road_type in ['Main', 'Regional']:  # Show main roads even if not damaged
                        color_map = {
                            'Main': 'darkblue',
                            'Regional': 'blue'
                        }
                        color = color_map.get(road_type, 'darkblue')
                        weight = 4
                        opacity = 0.8
                        target_group = streets_group
                    else:
                        # Skip minor roads to reduce clutter
                        continue
                    
                    # Create popup with strategic information
                    tags = []
                    if street.get('near_hospital', False):
                        tags.append('🏥 Near Hospital')
                    if street.get('is_major_artery', False):
                        tags.append('🛤️ Major Artery')
                    
                    popup_text = f"""<b>🛣️ {road_type} Road</b><br>
                    Municipality: {municipality}<br>
                    Length: {street.get('Length_km', 0):.2f} km<br>
                    Damage: {street.get('damage_severity', 0):.0f}<br>
                    Priority Score: {priority:.0f}<br>
                    Status: {'💥 DAMAGED' if is_damaged else '✓ Intact'}<br>
                    {' | '.join(tags) if tags else ''}"""
                    
                    if street.geometry.geom_type == 'LineString':
                        coords = [(y, x) for x, y in street.geometry.coords]
                        folium.PolyLine(
                            locations=coords,
                            color=color,
                            weight=weight,
                            opacity=opacity,
                            popup=popup_text
                        ).add_to(target_group)
                        street_count += 1
                    elif street.geometry.geom_type == 'MultiLineString':
                        for line in street.geometry.geoms:
                            coords = [(y, x) for x, y in line.coords]
                            folium.PolyLine(
                                locations=coords,
                                color=color,
                                weight=weight,
                                opacity=opacity,
                                popup=popup_text
                            ).add_to(target_group)
                            street_count += 1
                            if street_count >= 2000:
                                break
                except Exception as e:
                    continue
            
            print(f"   - Added {street_count} streets ({strategic_count} strategic, {damaged_count} damaged) to map")

        # Add municipalities as boundary polygons (DISABLED - not shown on map)
        # if 'municipalities' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['municipalities'].empty:
        #     municipalities_group = folium.FeatureGroup(name='🏛️ Municipal Boundaries', show=False).add_to(m)
        #     for _, municipality in infrastructure_layers_wgs84['municipalities'].iterrows():
        #         ...

        # Add schools
        if 'schools' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['schools'].empty:
            schools_group = folium.FeatureGroup(name='🏫 Schools & Education', show=True).add_to(m)
            for _, facility in infrastructure_layers_wgs84['schools'].head(100).iterrows():
                if hasattr(facility.geometry, 'centroid'):
                    lat, lon = facility.geometry.centroid.y, facility.geometry.centroid.x
                else:
                    lat, lon = facility.geometry.y, facility.geometry.x

                name = facility.get('name', 'School')
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>🏫 School:</b><br>{name}<br><i>Educational facility</i>",
                    icon=folium.Icon(color='blue', icon='graduation-cap', prefix='fa')
                ).add_to(schools_group)

        # Add universities
        if 'universities' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['universities'].empty:
            universities_group = folium.FeatureGroup(name='🎓 Universities', show=True).add_to(m)
            for _, facility in infrastructure_layers_wgs84['universities'].head(50).iterrows():
                if hasattr(facility.geometry, 'centroid'):
                    lat, lon = facility.geometry.centroid.y, facility.geometry.centroid.x
                else:
                    lat, lon = facility.geometry.y, facility.geometry.x

                name = facility.get('name', 'University')
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>🎓 University:</b><br>{name}<br><i>Higher education facility</i>",
                    icon=folium.Icon(color='darkblue', icon='university', prefix='fa')
                ).add_to(universities_group)


        # Add water infrastructure
        if 'water' in infrastructure_layers_wgs84 and not infrastructure_layers_wgs84['water'].empty:
            water_group = folium.FeatureGroup(name='💧 Water Infrastructure', show=False).add_to(m)
            for _, facility in infrastructure_layers_wgs84['water'].head(50).iterrows():
                if hasattr(facility.geometry, 'centroid'):
                    lat, lon = facility.geometry.centroid.y, facility.geometry.centroid.x
                else:
                    lat, lon = facility.geometry.y, facility.geometry.x

                name = facility.get('name', 'Water Facility')
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>💧 Water Infrastructure:</b><br>{name}<br><i>Water supply facility</i>",
                    icon=folium.Icon(color='blue', icon='tint', prefix='fa')
                ).add_to(water_group)

    # Damage sites layer removed - not displayed on map
    # if damage_gdf_wgs84 is not None and not damage_gdf_wgs84.empty:
    #     damage_cluster = folium.FeatureGroup(name='💥 Damage Sites', show=False).add_to(m)
    #     ...

    # Add project markers if projects are provided
    if projects_df is not None and not projects_df.empty:
        projects_group = folium.FeatureGroup(name='📋 Selected Projects', show=True).add_to(m)

        for _, project in projects_df.iterrows():
            # Find the corresponding zone
            zone_id = project.get('Zone_ID', '')
            zone_match = hex_gdf_wgs84[hex_gdf_wgs84['zone_id'] == zone_id]
            if not zone_match.empty:
                zone = zone_match.iloc[0]
                lat, lon = zone.geometry.centroid.y, zone.geometry.centroid.x

                project_type = project.get('Project_Type', 'unknown').lower()
                icon_color = {
                    'healthcare': 'red',
                    'education': 'blue',
                    'universities': 'darkblue',
                    'transportation': 'orange',
                    'municipal': 'purple',
                    'utilities': 'green'
                }.get(project_type, 'gray')

                icon_shape = {
                    'healthcare': 'plus',
                    'education': 'graduation-cap',
                    'universities': 'university',
                    'transportation': 'road',
                    'municipal': 'building',
                    'utilities': 'cog'
                }.get(project_type, 'star')

                folium.Marker(
                    location=[lat, lon],
                    popup=f"""
                    <b>Project:</b> {project.get('Project_ID', 'Unknown')}<br>
                    <b>Type:</b> {project.get('Infrastructure_Type', 'Unknown')}<br>
                    <b>Municipality:</b> {project.get('Municipality', 'Unknown')}<br>
                    <b>Priority:</b> #{project.get('Final_Priority_Rank', 'Unknown')}<br>
                    <b>Cost:</b> {project.get('Estimated_Cost', 'TBD')}<br>
                    <b>Timeline:</b> {project.get('Timeline_Months', 'Unknown')} months
                    """,
                    icon=folium.Icon(color=icon_color, icon=icon_shape, prefix='fa')
                ).add_to(projects_group)

    # Add layer control
    folium.LayerControl().add_to(m)

    # Add professional legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 240px; height: 220px;
                background-color: white; border:2px solid #333; border-radius: 8px; z-index:9999;
                font-size:12px; padding: 15px; box-shadow: 0 0 15px rgba(0,0,0,0.2);">
        <h4 style="margin: 0 0 10px 0; color: #333; font-size: 14px;"><b>🗺️ Gaza Reconstruction DSS</b></h4>

        <p style="margin: 5px 0;"><b>🏗️ Priority Zones</b></p>
        <p style="margin: 2px 0;"><span style="color:#ff0000;">●</span> Critical (Top 20%)</p>
        <p style="margin: 2px 0;"><span style="color:#ff8000;">●</span> High Priority (20-40%)</p>
        <p style="margin: 2px 0;"><span style="color:#ffff00;">●</span> Medium-High (40-60%)</p>
        <p style="margin: 2px 0;"><span style="color:#80ff00;">●</span> Medium (60-80%)</p>
        <p style="margin: 2px 0;"><span style="color:#00ff00;">●</span> Low Priority (80-100%)</p>

        <hr style="margin: 8px 0; border: 1px solid #ddd;">

        <p style="margin: 5px 0;"><b>🏢 Infrastructure</b></p>
        <p style="margin: 2px 0;"><span style="color:red;">🏥</span> Healthcare</p>
        <p style="margin: 2px 0;"><span style="color:blue;">🏫</span> Schools</p>
        <p style="margin: 2px 0;"><span style="color:darkblue;">🎓</span> Universities</p>
        <p style="margin: 2px 0;"><span style="color:red;">━</span> Damaged Streets</p>
        <p style="margin: 2px 0;"><span style="color:darkblue;">━</span> Main Roads</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # Add title
    title_html = '''
    <div style="position: fixed; top: 10px; left: 50px; width: 400px; z-index:9999;
                background-color: rgba(255,255,255,0.9); border:2px solid #333; border-radius: 8px;
                font-size:16px; padding: 10px; box-shadow: 0 0 15px rgba(0,0,0,0.2);">
        <h3 style="margin: 0; color: #333;">🇵🇸 Gaza Strip Reconstruction Decision Support System</h3>
        <p style="margin: 5px 0; font-size: 12px; color: #666;">
        Interactive map showing reconstruction priorities, infrastructure, and selected projects.
        Use layer controls to toggle visibility. Data current as of January 2026.
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    # Save map
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"gaza_reconstruction_map_{timestamp}.html"

    m.save(output_path)
    print(f"   - Interactive map saved to {output_path}")

    return output_path

    # Add layer control
    folium.LayerControl().add_to(m)

    # Add legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 150px; height: 120px;
                background-color: white; border:2px solid grey; z-index:9999; font-size:14px;">
        <p><b>Priority Levels</b></p>
        <p><span style="color:#ff0000;">●</span> Critical (Top 20%)</p>
        <p><span style="color:#ff8000;">●</span> High (20-40%)</p>
        <p><span style="color:#ffff00;">●</span> Medium-High (40-60%)</p>
        <p><span style="color:#80ff00;">●</span> Medium (60-80%)</p>
        <p><span style="color:#00ff00;">●</span> Low (80-100%)</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # Save map
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"gaza_reconstruction_map_{timestamp}.html"

    m.save(output_path)
    print(f"   - Interactive map saved to {output_path}")

    return output_path

# ======================================================
# Statistical Dashboard
# ======================================================

def create_statistical_dashboard(hex_gdf, projects_df=None, output_path=None):
    """Create statistical dashboard with multiple charts"""
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"gaza_reconstruction_dashboard_{timestamp}.png"

    # Set up the matplotlib figure
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Gaza Reconstruction DSS - Statistical Dashboard', fontsize=16, fontweight='bold')

    # Chart 1: Priority distribution
    if 'ai_score' in hex_gdf.columns:
        axes[0, 0].hist(hex_gdf['ai_score'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        axes[0, 0].set_title('AI Score Distribution')
        axes[0, 0].set_xlabel('AI Score')
        axes[0, 0].set_ylabel('Frequency')

    # Chart 2: Damage count distribution
    if 'damage_count' in hex_gdf.columns:
        axes[0, 1].hist(hex_gdf['damage_count'], bins=20, alpha=0.7, color='salmon', edgecolor='black')
        axes[0, 1].set_title('Damage Count Distribution')
        axes[0, 1].set_xlabel('Damage Sites')
        axes[0, 1].set_ylabel('Frequency')

    # Chart 3: Strategy breakdown
    if 'rebuilding_strategy' in hex_gdf.columns:
        strategy_counts = hex_gdf['rebuilding_strategy'].apply(lambda x: x.get('strategy', 'Unknown') if isinstance(x, dict) else 'Unknown').value_counts()
        strategy_counts.plot(kind='bar', ax=axes[0, 2], color='lightgreen', edgecolor='black')
        axes[0, 2].set_title('Rebuilding Strategies')
        axes[0, 2].set_xlabel('Strategy')
        axes[0, 2].set_ylabel('Count')
        axes[0, 2].tick_params(axis='x', rotation=45)

    # Chart 4: Top municipalities by damage
    if 'primary_municipality' in hex_gdf.columns and 'damage_count' in hex_gdf.columns:
        municipality_damage = hex_gdf.groupby('primary_municipality')['damage_count'].sum().nlargest(10)
        municipality_damage.plot(kind='barh', ax=axes[1, 0], color='orange', edgecolor='black')
        axes[1, 0].set_title('Top 10 Municipalities by Damage')
        axes[1, 0].set_xlabel('Total Damage Sites')

    # Chart 5: Infrastructure correlation
    infrastructure_cols = ['hospitals_count', 'water_util_count', 'fuel_util_count', 'streets_count']
    available_cols = [col for col in infrastructure_cols if col in hex_gdf.columns]

    if len(available_cols) > 1 and 'damage_count' in hex_gdf.columns:
        corr_data = hex_gdf[available_cols + ['damage_count']].corr()
        sns.heatmap(corr_data, annot=True, cmap='coolwarm', ax=axes[1, 1], fmt='.2f')
        axes[1, 1].set_title('Infrastructure Correlation Matrix')

    # Chart 6: Project timeline distribution (if projects available)
    if projects_df is not None and 'Timeline_Months' in projects_df.columns:
        axes[1, 2].hist(projects_df['Timeline_Months'], bins=10, alpha=0.7, color='purple', edgecolor='black')
        axes[1, 2].set_title('Project Timeline Distribution')
        axes[1, 2].set_xlabel('Timeline (Months)')
        axes[1, 2].set_ylabel('Number of Projects')
    else:
        axes[1, 2].text(0.5, 0.5, 'No Project Data\nAvailable', ha='center', va='center', transform=axes[1, 2].transAxes)
        axes[1, 2].set_title('Project Timeline Distribution')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"   - Statistical dashboard saved to {output_path}")
    return output_path

# ======================================================
# Summary Report Generation
# ======================================================

def generate_summary_report(hex_gdf, projects_df, damage_analysis, output_path=None):
    """Generate comprehensive summary report"""
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"gaza_reconstruction_report_{timestamp}.txt"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("GAZA RECONSTRUCTION DECISION SUPPORT SYSTEM - SUMMARY REPORT\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"System Version: {SYSTEM_VERSION}\n\n")

        # Quantile-based damage classification (robust against skewed distributions)
        damage_series = pd.to_numeric(hex_gdf.get('damage_count', pd.Series(dtype='float64')), errors='coerce').fillna(0)
        q_high = float(damage_series.quantile(0.90)) if len(damage_series) else 0.0
        q_moderate = float(damage_series.quantile(0.70)) if len(damage_series) else 0.0
        high_damage_count = int((damage_series >= q_high).sum()) if len(damage_series) else 0
        moderate_damage_count = int(((damage_series >= q_moderate) & (damage_series < q_high)).sum()) if len(damage_series) else 0
        low_damage_count = int((damage_series < q_moderate).sum()) if len(damage_series) else 0

        # Analysis Summary
        f.write("ANALYSIS SUMMARY\n")
        f.write("-" * 20 + "\n")
        f.write(f"Total Zones Analyzed: {len(hex_gdf)}\n")
        f.write(f"Total Damage Sites: {damage_analysis.get('total_damage_sites', 0)}\n")
        f.write(f"High Damage Areas (>= P90, threshold {q_high:.1f}): {high_damage_count}\n")
        f.write(f"Moderate Damage Areas (P70-P90, threshold {q_moderate:.1f} to <{q_high:.1f}): {moderate_damage_count}\n")
        f.write(f"Low Damage Areas (< P70, threshold <{q_moderate:.1f}): {low_damage_count}\n\n")

        # Strategy Breakdown
        if 'rebuilding_strategy' in hex_gdf.columns:
            strategy_counts = hex_gdf['rebuilding_strategy'].apply(lambda x: x.get('strategy', 'Unknown') if isinstance(x, dict) else 'Unknown').value_counts()
            f.write("STRATEGY BREAKDOWN\n")
            f.write("-" * 20 + "\n")
            for strategy, count in strategy_counts.items():
                f.write(f"{strategy}: {count} zones\n")
            f.write("\n")

        # Project Summary
        if projects_df is not None:
            f.write("PROJECT SUMMARY\n")
            f.write("-" * 20 + "\n")
            f.write(f"Total Projects Generated: {len(projects_df)}\n")

            if 'Required_Units' in projects_df.columns:
                total_units = projects_df['Required_Units'].sum()
                f.write(f"Total Required Units: {total_units:,}\n")

            if 'Timeline_Months' in projects_df.columns:
                avg_timeline = projects_df['Timeline_Months'].mean()
                f.write(f"Average Timeline: {avg_timeline:.1f} months\n")
            f.write("\n")

        # Top Priority Zones
        f.write("TOP 10 PRIORITY ZONES\n")
        f.write("-" * 20 + "\n")
        top_10 = hex_gdf.head(10)
        for idx, row in top_10.iterrows():
            strategy = row.get('rebuilding_strategy', {})
            strategy_name = strategy.get('strategy', 'Unknown') if isinstance(strategy, dict) else str(strategy)
            f.write(f"Rank {idx+1}: Zone {row.get('zone_id', f'ZONE-{idx+1:03d}')} ")
            f.write(f"(AI Score: {row.get('ai_score', 0):.3f}, ")
            f.write(f"Damage: {row.get('damage_count', 0)}, ")
            f.write(f"Strategy: {strategy_name}, ")
            f.write(f"Municipality: {row.get('primary_municipality', 'Unknown')})\n")
        f.write("\n")

        # Recommendations
        f.write("RECOMMENDATIONS\n")
        f.write("-" * 20 + "\n")
        f.write("1. Focus initial reconstruction efforts on high-damage areas with basic infrastructure priorities\n")
        f.write("2. Implement balanced reconstruction approaches in moderate-damage municipalities\n")
        f.write("3. Prioritize street rebuilding in low-damage areas to restore connectivity\n")
        f.write("4. Consider age-based ranking for persistent damage sites requiring long-term attention\n")
        f.write("5. Monitor and adjust strategies based on field assessments and changing conditions\n\n")

        f.write("=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")

    print(f"   - Summary report saved to {output_path}")
    return output_path
