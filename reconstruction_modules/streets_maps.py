# ======================================================
# streets_maps.py - Specialized Streets Maps
# ======================================================

import folium
from datetime import datetime

def create_streets_damage_map(streets_gdf, output_path=None):
    """Create map showing only street damage levels"""
    
    if streets_gdf is None or streets_gdf.empty:
        print("   - WARNING: No streets data available")
        return None
    
    print(f"   - Creating streets damage map...")
    
    wgs84_crs = "EPSG:4326"
    streets_wgs84 = streets_gdf.to_crs(wgs84_crs) if streets_gdf.crs != wgs84_crs else streets_gdf
    
    bounds = streets_wgs84.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles='CartoDB positron'
    )
    
    # Add basemap options
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer('CartoDB positron', name='Light Map', show=True).add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='Dark Map').add_to(m)
    
    # Create damage level groups
    no_damage_group = folium.FeatureGroup(name='✅ No Damage', show=True).add_to(m)
    low_damage_group = folium.FeatureGroup(name='🟡 Low Damage (1)', show=True).add_to(m)
    medium_damage_group = folium.FeatureGroup(name='🟠 Medium Damage (2)', show=True).add_to(m)
    high_damage_group = folium.FeatureGroup(name='🔴 High Damage (3)', show=True).add_to(m)
    severe_damage_group = folium.FeatureGroup(name='⚫ Severe Damage (4)', show=True).add_to(m)
    
    # Count streets by damage level
    damage_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    
    for idx, street in streets_wgs84.iterrows():
        damage = street.get('damage_severity', 0)
        road_type = street.get('RoadType', 'Unknown')
        municipality = street.get('municipality', 'Unknown')
        length_km = street.get('Length_km', 0)
        
        # Determine color and group
        if damage >= 4:
            color, weight, opacity, target_group = '#000000', 8, 1.0, severe_damage_group
            damage_level = 'Severe (4)'
            damage_counts[4] += 1
        elif damage >= 3:
            color, weight, opacity, target_group = '#8B0000', 7, 0.95, high_damage_group
            damage_level = 'High (3)'
            damage_counts[3] += 1
        elif damage >= 2:
            color, weight, opacity, target_group = '#FF8000', 6, 0.9, medium_damage_group
            damage_level = 'Medium (2)'
            damage_counts[2] += 1
        elif damage >= 1:
            color, weight, opacity, target_group = '#FFD700', 5, 0.85, low_damage_group
            damage_level = 'Low (1)'
            damage_counts[1] += 1
        else:
            color, weight, opacity, target_group = '#90EE90', 3, 0.6, no_damage_group
            damage_level = 'No Damage'
            damage_counts[0] += 1
        
        popup_html = f"""
        <div style="font-family: Arial; min-width: 280px;">
            <h4 style="margin: 5px 0; color: {color}; border-bottom: 2px solid {color};">
                💥 Street Damage Assessment
            </h4>
            <b>📍 Location:</b><br>
            • Municipality: <b>{municipality}</b><br>
            • Road Type: <b>{road_type}</b><br>
            • Length: <b>{length_km:.2f} km</b><br>
            <br>
            <b>💥 Damage Level:</b><br>
            • Severity: <b>{damage_level}</b><br>
            • Damage Score: <b>{damage:.1f}/4</b><br>
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
        except:
            continue
    
    total_streets = sum(damage_counts.values())
    damaged_streets = sum(damage_counts[i] for i in [1, 2, 3, 4])
    
    # Title
    title_html = f'''
    <div style="position: fixed; top: 10px; left: 50px; width: 520px; z-index:9999;
                background-color: rgba(255,255,255,0.97); border:3px solid #DC143C; border-radius: 10px;
                font-size:16px; padding: 18px; box-shadow: 0 6px 12px rgba(0,0,0,0.25);">
        <h3 style="margin: 0; color: #8B0000; font-size: 18px; border-bottom: 2px solid #DC143C; padding-bottom: 8px;">
            💥 Gaza Strip - Streets Damage Assessment
        </h3>
        <p style="margin: 10px 0 5px 0; font-size: 13px; color: #333; line-height: 1.5;">
        Comprehensive damage assessment for all street network.<br>
        Color-coded by damage severity level.
        </p>
        <p style="margin: 8px 0 0 0; font-size: 12px; color: #555; background: #f8f8f8; padding: 8px; border-radius: 5px;">
        📊 <b>Total Streets:</b> {total_streets:,}<br>
        💥 <b>Damaged Streets:</b> {damaged_streets:,} ({(damaged_streets/total_streets*100):.1f}%)
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Legend
    legend_html = f'''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 300px;
                background-color: rgba(255,255,255,0.97); border:3px solid #DC143C; border-radius: 10px;
                z-index:9999; font-size:13px; padding: 18px; box-shadow: 0 6px 12px rgba(0,0,0,0.25);">
        <h4 style="margin: 0 0 12px 0; color: #8B0000; font-size: 16px; border-bottom: 2px solid #DC143C; padding-bottom: 8px;">
            💥 Damage Severity Levels
        </h4>
        <p style="margin: 6px 0; line-height: 1.8;">
            <span style="color:#000000; font-size: 22px; font-weight: bold;">━━</span> <b>Severe (4)</b> - {damage_counts[4]:,} streets<br>
            <span style="color:#8B0000; font-size: 22px; font-weight: bold;">━━</span> <b>High (3)</b> - {damage_counts[3]:,} streets<br>
            <span style="color:#FF8000; font-size: 22px; font-weight: bold;">━━</span> <b>Medium (2)</b> - {damage_counts[2]:,} streets<br>
            <span style="color:#FFD700; font-size: 22px; font-weight: bold;">━━</span> <b>Low (1)</b> - {damage_counts[1]:,} streets<br>
            <span style="color:#90EE90; font-size: 22px; font-weight: bold;">━━</span> <b>No Damage</b> - {damage_counts[0]:,} streets
        </p>
        <div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid #ddd;">
            <p style="font-size: 11px; color: #666; margin: 0;">
                💡 <b>Tip:</b> Toggle layers to filter by damage level
            </p>
        </div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    folium.LayerControl(position='topright').add_to(m)
    
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"GAZA_STREETS_DAMAGE_SEVERITY_MAP_{timestamp}.html"
    
    m.save(output_path)
    print(f"   - Streets damage map saved to {output_path}")
    return output_path, damage_counts


def create_streets_reconstruction_map(streets_gdf, output_path=None):
    """Create map showing street reconstruction priorities and costs"""
    
    if streets_gdf is None or streets_gdf.empty:
        print("   - WARNING: No streets data available")
        return None
    
    print(f"   - Creating streets reconstruction map...")
    
    wgs84_crs = "EPSG:4326"
    streets_wgs84 = streets_gdf.to_crs(wgs84_crs) if streets_gdf.crs != wgs84_crs else streets_gdf
    
    # Filter only damaged streets
    damaged_streets = streets_wgs84[streets_wgs84.get('damage_severity', 0) > 0].copy()
    
    if damaged_streets.empty:
        print("   - No damaged streets found")
        return None
    
    bounds = damaged_streets.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles='CartoDB positron'
    )
    
    # Add basemap options
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer('CartoDB positron', name='Light Map', show=True).add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='Dark Map').add_to(m)
    
    # Create priority groups
    critical_group = folium.FeatureGroup(name='🔴 Critical Priority', show=True).add_to(m)
    high_group = folium.FeatureGroup(name='🟠 High Priority', show=True).add_to(m)
    medium_group = folium.FeatureGroup(name='🟡 Medium Priority', show=True).add_to(m)
    low_group = folium.FeatureGroup(name='🟢 Low Priority', show=True).add_to(m)
    
    # Calculate reconstruction costs and timeline
    priority_counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0}
    total_cost = 0
    
    for idx, street in damaged_streets.iterrows():
        damage = street.get('damage_severity', 0)
        road_type = street.get('RoadType', 'Unknown')
        municipality = street.get('municipality', 'Unknown')
        length_km = street.get('Length_km', 0)
        priority_score = street.get('reconstruction_priority', 0)
        
        # Calculate reconstruction cost and timeline
        cost_per_km = 500000  # $500k per km base cost
        damage_multiplier = damage / 3  # Scale by damage
        reconstruction_cost = length_km * cost_per_km * damage_multiplier
        reconstruction_months = int(length_km * 2 * damage_multiplier)
        
        total_cost += reconstruction_cost
        
        # Determine priority
        if priority_score >= 30:
            color, weight, opacity, target_group = '#8B0000', 10, 1.0, critical_group
            priority_level = 'Critical'
            priority_counts['Critical'] += 1
        elif priority_score >= 20:
            color, weight, opacity, target_group = '#FF4500', 8, 0.95, high_group
            priority_level = 'High'
            priority_counts['High'] += 1
        elif priority_score >= 10:
            color, weight, opacity, target_group = '#FFA500', 6, 0.9, medium_group
            priority_level = 'Medium'
            priority_counts['Medium'] += 1
        else:
            color, weight, opacity, target_group = '#FFD700', 4, 0.85, low_group
            priority_level = 'Low'
            priority_counts['Low'] += 1
        
        popup_html = f"""
        <div style="font-family: Arial; min-width: 300px;">
            <h4 style="margin: 5px 0; color: {color}; border-bottom: 2px solid {color};">
                🏗️ Street Reconstruction Plan
            </h4>
            <b>📍 Location:</b><br>
            • Municipality: <b>{municipality}</b><br>
            • Road Type: <b>{road_type}</b><br>
            • Length: <b>{length_km:.2f} km</b><br>
            <br>
            <b>🎯 Priority:</b><br>
            • Level: <b>{priority_level}</b><br>
            • Priority Score: <b>{priority_score:.0f}</b><br>
            • Damage: <b>{damage:.1f}/4</b><br>
            <br>
            <b>🏗️ Reconstruction:</b><br>
            • Estimated Cost: <b>${reconstruction_cost:,.0f}</b><br>
            • Timeline: <b>{reconstruction_months} months</b><br>
            • Cost per km: <b>${cost_per_km:,}</b>
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
        except:
            continue
    
    total_streets = len(damaged_streets)
    
    # Title
    title_html = f'''
    <div style="position: fixed; top: 10px; left: 50px; width: 550px; z-index:9999;
                background-color: rgba(255,255,255,0.97); border:3px solid #0066CC; border-radius: 10px;
                font-size:16px; padding: 18px; box-shadow: 0 6px 12px rgba(0,0,0,0.25);">
        <h3 style="margin: 0; color: #0066CC; font-size: 18px; border-bottom: 2px solid #0066CC; padding-bottom: 8px;">
            🏗️ Gaza Strip - Streets Reconstruction Plan
        </h3>
        <p style="margin: 10px 0 5px 0; font-size: 13px; color: #333; line-height: 1.5;">
        Reconstruction priorities and cost estimates for damaged streets.<br>
        Click streets for detailed reconstruction information.
        </p>
        <p style="margin: 8px 0 0 0; font-size: 12px; color: #555; background: #f8f8f8; padding: 8px; border-radius: 5px;">
        🛣️ <b>Damaged Streets:</b> {total_streets:,}<br>
        💰 <b>Total Cost:</b> ${total_cost:,.0f}
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Legend
    legend_html = f'''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 300px;
                background-color: rgba(255,255,255,0.97); border:3px solid #0066CC; border-radius: 10px;
                z-index:9999; font-size:13px; padding: 18px; box-shadow: 0 6px 12px rgba(0,0,0,0.25);">
        <h4 style="margin: 0 0 12px 0; color: #0066CC; font-size: 16px; border-bottom: 2px solid #0066CC; padding-bottom: 8px;">
            🏗️ Reconstruction Priority
        </h4>
        <p style="margin: 6px 0; line-height: 1.8;">
            <span style="color:#8B0000; font-size: 22px; font-weight: bold;">━━</span> <b>Critical</b> - {priority_counts['Critical']:,} streets<br>
            <span style="color:#FF4500; font-size: 22px; font-weight: bold;">━━</span> <b>High</b> - {priority_counts['High']:,} streets<br>
            <span style="color:#FFA500; font-size: 22px; font-weight: bold;">━━</span> <b>Medium</b> - {priority_counts['Medium']:,} streets<br>
            <span style="color:#FFD700; font-size: 22px; font-weight: bold;">━━</span> <b>Low</b> - {priority_counts['Low']:,} streets
        </p>
        <div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid #ddd;">
            <p style="font-size: 11px; color: #666; margin: 0;">
                💡 <b>Tip:</b> Toggle layers to filter by priority
            </p>
        </div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    folium.LayerControl(position='topright').add_to(m)
    
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"GAZA_STREETS_RECONSTRUCTION_PRIORITIES_MAP_{timestamp}.html"
    
    m.save(output_path)
    print(f"   - Streets reconstruction map saved to {output_path}")
    return output_path, priority_counts, total_cost
