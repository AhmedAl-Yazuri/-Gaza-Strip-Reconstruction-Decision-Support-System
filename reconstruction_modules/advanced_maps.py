# ======================================================
# advanced_maps.py - Advanced Map Visualizations
# ======================================================

import folium
from folium.plugins import HeatMap, TimestampedGeoJson
import pandas as pd
from datetime import datetime
import json

def create_damage_heatmap(damage_gdf, output_path=None):
    """Create heatmap showing damage intensity across Gaza Strip"""
    
    wgs84_crs = "EPSG:4326"
    damage_wgs84 = damage_gdf.to_crs(wgs84_crs) if damage_gdf.crs != wgs84_crs else damage_gdf
    
    # Calculate center from bounds to avoid centroid operations in geographic CRS
    minx, miny, maxx, maxy = damage_wgs84.total_bounds
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2
    
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
    
    # Prepare heatmap data
    heat_data = []
    for idx, row in damage_wgs84.iterrows():
        rep_point = row.geometry.representative_point()
        lat = rep_point.y
        lon = rep_point.x
        weight = row.get('damage_severity', 1)
        heat_data.append([lat, lon, weight])
    
    # Add heatmap layer
    HeatMap(
        heat_data,
        min_opacity=0.3,
        max_opacity=0.9,
        radius=15,
        blur=20,
        gradient={
            0.0: '#8B0000',  # Dark Red - Extreme
            0.3: '#FF4500',  # Orange Red - Very High
            0.5: '#FFA500',  # Orange - High
            0.7: '#FFFF00',  # Yellow - Medium
            1.0: '#00FF00'   # Green - Low
        }
    ).add_to(m)
    
    # Title
    title_html = '''
    <div style="position: fixed; top: 10px; left: 50px; width: 500px; z-index:9999;
                background-color: rgba(255,255,255,0.95); border:3px solid #FF0000; border-radius: 8px;
                font-size:16px; padding: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.3);">
        <h3 style="margin: 0; color: #8B0000;">🔥 Gaza Strip - Damage Intensity Heatmap</h3>
        <p style="margin: 5px 0; font-size: 13px; color: #333;">
        Visualization of damage concentration across Gaza Strip.
        Red areas indicate highest damage intensity.
        </p>
        <p style="margin: 5px 0; font-size: 11px; color: #666;">
        Data: UNOSAT | Generated: {date}
        </p>
    </div>
    '''.format(date=datetime.now().strftime('%Y-%m-%d'))
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 200px; height: 180px;
                background-color: rgba(255,255,255,0.95); border:3px solid #FF0000; border-radius: 8px;
                z-index:9999; font-size:13px; padding: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.3);">
        <h4 style="margin: 0 0 10px 0; color: #8B0000;"><b>🔥 Damage Intensity</b></h4>
        <div style="background: linear-gradient(to bottom, #8B0000, #FF4500, #FFA500, #FFFF00, #00FF00);
                    height: 100px; width: 30px; float: left; margin-right: 10px; border-radius: 3px;"></div>
        <div style="float: left;">
            <p style="margin: 0; line-height: 20px;">Extreme</p>
            <p style="margin: 20px 0 0 0; line-height: 20px;">High</p>
            <p style="margin: 20px 0 0 0; line-height: 20px;">Medium</p>
            <p style="margin: 20px 0 0 0; line-height: 20px;">Low</p>
        </div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"gaza_damage_heatmap_{timestamp}.html"
    
    folium.LayerControl(position='topright').add_to(m)
    m.save(output_path)
    print(f"   - Damage heatmap saved to {output_path}")
    return output_path


def create_population_3d_map(hex_gdf, output_path=None):
    """Create 3D-style population density visualization"""
    
    wgs84_crs = "EPSG:4326"
    hex_gdf_wgs84 = hex_gdf.to_crs(wgs84_crs) if hex_gdf.crs != wgs84_crs else hex_gdf
    
    minx, miny, maxx, maxy = hex_gdf_wgs84.total_bounds
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles='CartoDB positron'
    )
    
    # Get max density for scaling
    max_density = hex_gdf_wgs84['population_density'].max()
    
    # Add zones with height effect (opacity = height)
    for idx, row in hex_gdf_wgs84.iterrows():
        coords = [[y, x] for x, y in row.geometry.exterior.coords]
        density = row.get('population_density', 0)
        
        # Color based on density
        if density > 30000:
            color = '#8B0000'
        elif density > 15000:
            color = '#DC143C'
        elif density > 8000:
            color = '#FF4500'
        elif density > 5000:
            color = '#FFA500'
        elif density > 2000:
            color = '#FFD700'
        else:
            color = '#90EE90'
        
        # Opacity represents "height" (3D effect)
        opacity = min(0.3 + (density / max_density * 0.7), 1.0) if max_density > 0 else 0.3
        
        folium.Polygon(
            locations=coords,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=opacity,
            weight=1,
            popup=f"<b>Density:</b> {density:,.0f} people/km²"
        ).add_to(m)
    
    # Title
    title_html = '''
    <div style="position: fixed; top: 10px; left: 50px; width: 450px; z-index:9999;
                background-color: rgba(0,0,0,0.8); border:2px solid #00BFFF; border-radius: 8px;
                font-size:16px; padding: 15px; color: white;">
        <h3 style="margin: 0; color: #00BFFF;">👥 Gaza Strip - 3D Population Density</h3>
        <p style="margin: 5px 0; font-size: 12px;">
        Opacity represents population density (darker = higher density).
        Simulates 3D visualization of population distribution.
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"gaza_population_3d_{timestamp}.html"
    
    folium.LayerControl(position='topright').add_to(m)
    m.save(output_path)
    print(f"   - 3D population map saved to {output_path}")
    return output_path



def create_before_after_comparison(hex_gdf, output_path=None):
    """Create side-by-side before/after comparison map"""
    
    wgs84_crs = "EPSG:4326"
    hex_gdf_wgs84 = hex_gdf.to_crs(wgs84_crs) if hex_gdf.crs != wgs84_crs else hex_gdf
    
    minx, miny, maxx, maxy = hex_gdf_wgs84.total_bounds
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2
    
    # Create dual pane map using plugins
    from folium.plugins import DualMap
    
    m = DualMap(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles='CartoDB positron'
    )
    
    # LEFT MAP: Pre-war population (2020)
    for idx, row in hex_gdf_wgs84.iterrows():
        coords = [[y, x] for x, y in row.geometry.exterior.coords]
        pop_prewar = row.get('population_prewar', 0)
        
        # Color based on pre-war population
        if pop_prewar > 5000:
            color = '#0066CC'
        elif pop_prewar > 2000:
            color = '#4D94FF'
        elif pop_prewar > 1000:
            color = '#80B3FF'
        else:
            color = '#B3D1FF'
        
        folium.Polygon(
            locations=coords,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            weight=1,
            popup=f"<b>Pre-war:</b> {pop_prewar:,.0f} people"
        ).add_to(m.m1)
    
    # RIGHT MAP: Current population (2024-2025)
    for idx, row in hex_gdf_wgs84.iterrows():
        coords = [[y, x] for x, y in row.geometry.exterior.coords]
        pop_current = row.get('population_total', 0)
        
        # Color based on current population
        if pop_current > 10000:
            color = '#8B0000'
        elif pop_current > 5000:
            color = '#DC143C'
        elif pop_current > 2000:
            color = '#FF6347'
        elif pop_current > 1000:
            color = '#FFA07A'
        else:
            color = '#FFE4E1'
        
        folium.Polygon(
            locations=coords,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            weight=1,
            popup=f"<b>Current:</b> {pop_current:,.0f} people"
        ).add_to(m.m2)
    
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"gaza_before_after_{timestamp}.html"
    
    folium.LayerControl(position='topright').add_to(m)
    m.save(output_path)
    print(f"   - Before/After comparison map saved to {output_path}")
    return output_path


def create_damaged_streets_map(streets_gdf, output_path=None):
    """Create professional damaged streets map with all streets visible"""
    
    if streets_gdf is None or streets_gdf.empty:
        print("   - WARNING: No streets data available")
        return None
    
    print(f"   - Processing {len(streets_gdf)} streets...")
    
    wgs84_crs = "EPSG:4326"
    streets_wgs84 = streets_gdf.to_crs(wgs84_crs) if streets_gdf.crs != wgs84_crs else streets_gdf
    
    # Check geometry types
    geom_types = streets_wgs84.geometry.geom_type.value_counts()
    print(f"   - Geometry types: {dict(geom_types)}")
    
    # Filter LineString and MultiLineString geometries
    valid_streets = streets_wgs84[
        streets_wgs84.geometry.geom_type.isin(['LineString', 'MultiLineString'])
    ]
    print(f"   - Found {len(valid_streets)} valid street geometries")
    
    if valid_streets.empty:
        print("   - WARNING: No valid street geometries found")
        return None
    
    streets_wgs84 = valid_streets
    
    bounds = streets_wgs84.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    
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
    
    # Create feature groups
    all_streets_group = folium.FeatureGroup(name='🛣️ All Streets (Background)', show=True).add_to(m)
    critical_group = folium.FeatureGroup(name='🔴 Critical Priority', show=True).add_to(m)
    high_group = folium.FeatureGroup(name='🟠 High Priority', show=True).add_to(m)
    medium_group = folium.FeatureGroup(name='🟡 Medium Priority', show=True).add_to(m)
    low_group = folium.FeatureGroup(name='🟢 Low Priority', show=False).add_to(m)
    
    # First pass: Add ALL streets as background (professional gray)
    street_count_bg = 0
    line_count = 0
    print(f"   - Adding all streets background layer...")
    for idx, street in streets_wgs84.iterrows():
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
                        line_count += 1
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
                    line_count += 1
        except:
            continue
    
    print(f"   - Added {street_count_bg:,} streets ({line_count:,} segments)")
    
    # Second pass: Highlight priority streets (damaged or strategic)
    priority_streets = streets_wgs84[
        (streets_wgs84.get('damage_severity', pd.Series([0]*len(streets_wgs84))) > 0) | 
        (streets_wgs84.get('near_hospital', pd.Series([False]*len(streets_wgs84))) == True) | 
        (streets_wgs84.get('is_major_artery', pd.Series([False]*len(streets_wgs84))) == True) |
        (streets_wgs84.get('RoadType', pd.Series(['Unknown']*len(streets_wgs84))).isin(['Main', 'Regional']))
    ]
    
    # If no priority streets found, show top streets by any criteria
    if priority_streets.empty:
        print("   - No priority streets found, showing all streets with priority...")
        priority_streets = streets_wgs84.head(5000)
    
    priority_streets_sorted = priority_streets.sort_values('reconstruction_priority', ascending=False) if 'reconstruction_priority' in priority_streets.columns else priority_streets
    
    count = 0
    for idx, street in priority_streets_sorted.iterrows():
        if count >= 5000:
            break
        
        try:
            is_strategic = street.get('near_hospital', False) or street.get('is_major_artery', False)
            near_hospital = street.get('near_hospital', False)
            road_type = street.get('RoadType', 'Unknown')
            damage = street.get('damage_severity', 0)
            priority = street.get('reconstruction_priority', 0)
            length_km = street.get('Length_km', 0)
            municipality = street.get('municipality', street.get('Governorate', 'Unknown'))
            
            # Determine styling based on priority
            if damage > 0 and is_strategic and near_hospital:
                color = '#8B0000'
                weight = 14
                opacity = 1.0
                target_group = critical_group
                category = 'CRITICAL - Damaged + Strategic'
            elif damage > 0 and near_hospital:
                color = '#FF4500'
                weight = 12
                opacity = 0.95
                target_group = high_group
                category = 'HIGH - Damaged + Hospital'
            elif damage > 0 and road_type in ['Main', 'Regional']:
                color = '#FFA500'
                weight = 10
                opacity = 0.9
                target_group = medium_group
                category = 'MEDIUM - Damaged Main Road'
            elif damage > 0:
                color = '#FFD700'
                weight = 8
                opacity = 0.8
                target_group = low_group
                category = 'LOW - Damaged Local'
            elif is_strategic or near_hospital:
                color = '#0000CD'
                weight = 10
                opacity = 0.85
                target_group = high_group
                category = 'STRATEGIC - Intact'
            elif road_type in ['Main', 'Regional']:
                color = '#4169E1'
                weight = 8
                opacity = 0.75
                target_group = medium_group
                category = 'MAIN ROAD - Intact'
            else:
                continue
            
            popup_html = f"""
            <div style="font-family: Arial; min-width: 300px;">
                <h4 style="margin: 5px 0; color: {color}; border-bottom: 2px solid {color};">
                    🛣️ Street Information
                </h4>
                <b>📍 Location:</b><br>
                • Municipality: <b>{municipality}</b><br>
                • Road Type: <b>{road_type}</b><br>
                • Length: <b>{length_km:.2f} km</b><br>
                <br>
                <b>{'💥 Damage:' if damage > 0 else '✅ Status:'}</b><br>
                • {'Damage Level: <b>' + str(damage) + '/3</b>' if damage > 0 else 'Status: <b>Intact</b>'}<br>
                • Category: <b>{category}</b><br>
                • Priority Score: <b>{priority:.0f}</b><br>
                <br>
                {'<b>🏗️ Reconstruction:</b><br>• Cost: <b>$' + f'{length_km * 500000 * (damage / 3):,.0f}' + '</b><br>• Timeline: <b>' + str(int(length_km * 2)) + ' months</b><br>' if damage > 0 else ''}
            </div>
            """
            
            if street.geometry.geom_type == 'MultiLineString':
                for line in street.geometry.geoms:
                    coords = [(coord[1], coord[0]) for coord in line.coords]
                    folium.PolyLine(
                        locations=coords,
                        color=color,
                        weight=weight,
                        opacity=opacity,
                        popup=folium.Popup(popup_html, max_width=320)
                    ).add_to(target_group)
                count += 1
            elif street.geometry.geom_type == 'LineString':
                coords = [(coord[1], coord[0]) for coord in street.geometry.coords]
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
    title_html = f'''
    <div style="position: fixed; top: 10px; left: 50px; width: 550px; z-index:9999;
                background-color: rgba(255,255,255,0.97); border:3px solid #DC143C; border-radius: 10px;
                font-size:16px; padding: 18px; box-shadow: 0 6px 12px rgba(0,0,0,0.25);">
        <h3 style="margin: 0; color: #8B0000; font-size: 18px; border-bottom: 2px solid #DC143C; padding-bottom: 8px;">
            🛣️ Gaza Strip - Street Reconstruction Network
        </h3>
        <p style="margin: 10px 0 5px 0; font-size: 13px; color: #333; line-height: 1.5;">
        <b>Complete street network</b> displayed in gray background.<br>
        <b>Priority streets</b> highlighted by reconstruction urgency.
        </p>
        <p style="margin: 8px 0 0 0; font-size: 12px; color: #555; background: #f8f8f8; padding: 8px; border-radius: 5px;">
        📊 <b>Total Network:</b> {street_count_bg:,} streets ({line_count:,} segments)<br>
        🔴 <b>Priority Streets:</b> {count:,} streets requiring reconstruction
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Professional legend
    legend_html = f'''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 320px;
                background-color: rgba(255,255,255,0.97); border:3px solid #DC143C; border-radius: 10px;
                z-index:9999; font-size:13px; padding: 18px; box-shadow: 0 6px 12px rgba(0,0,0,0.25);">
        <h4 style="margin: 0 0 12px 0; color: #8B0000; font-size: 16px; border-bottom: 2px solid #DC143C; padding-bottom: 8px;">
            🛣️ Street Network Legend
        </h4>
        
        <div style="background: #f8f8f8; padding: 10px; border-radius: 6px; margin-bottom: 12px;">
            <p style="margin: 0; font-size: 12px; color: #555;">
                <span style="color:#B0B0B0; font-size: 22px; font-weight: bold;">━━</span> 
                <b>All Streets Network</b><br>
                <span style="margin-left: 30px; font-size: 11px; color: #777;">{street_count_bg:,} streets total</span>
            </p>
        </div>
        
        <h5 style="margin: 12px 0 8px 0; color: #8B0000; font-size: 13px;">
            🔴 Priority Reconstruction ({count:,} streets):
        </h5>
        <p style="margin: 6px 0; line-height: 1.8;">
            <span style="color:#8B0000; font-size: 22px; font-weight: bold;">━━</span> <b>Critical</b> - Damaged Strategic<br>
            <span style="color:#FF4500; font-size: 22px; font-weight: bold;">━━</span> <b>High</b> - Hospital Access<br>
            <span style="color:#FFA500; font-size: 22px; font-weight: bold;">━━</span> <b>Medium</b> - Main Roads<br>
            <span style="color:#FFD700; font-size: 22px; font-weight: bold;">━━</span> <b>Low</b> - Local Streets
        </p>
        
        <div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid #ddd;">
            <p style="font-size: 11px; color: #666; margin: 0;">
                💡 <b>Tip:</b> Use layer control (top-right) to toggle priorities
            </p>
        </div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    folium.LayerControl(position='topright').add_to(m)
    
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"gaza_damaged_streets_{timestamp}.html"
    
    m.save(output_path)
    print(f"   - Damaged streets map saved to {output_path}")
    return output_path
