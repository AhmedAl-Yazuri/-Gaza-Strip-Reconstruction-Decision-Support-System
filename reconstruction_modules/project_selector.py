# ======================================================
# reconstruction_modules/project_selector.py
# Tiered Project Selection System
# ======================================================

from config import *
import pandas as pd
from datetime import datetime

# Display limits for infrastructure analysis output
DEFAULT_ANALYSIS_ZONE_LIMIT = 100
DEFAULT_TOP_DAMAGED_FACILITIES = 30
DEFAULT_TOP_PRIORITY_FACILITIES = 20

# ======================================================
# Project Types and Categories
# ======================================================

PROJECT_TYPES = {
    'major_hospitals': {
        'name': 'Major Hospital Reconstruction',
        'description': 'Priority reconstruction for major medical complexes (Al-Shifa, Nasser, etc.)',
        'priority_weight': 1.0,
        'infrastructure_types': ['major_hospitals_count'],
        'icon': '🏥'
    },
    'healthcare': {
        'name': 'Local Clinics & Health Centers',
        'description': 'Reconstruction of local clinics and community health centers',
        'priority_weight': 0.6,
        'infrastructure_types': ['hospitals_count'],
        'icon': '🩺'
    },
    'education': {
        'name': 'Educational Institutions',
        'description': 'Schools, universities, and educational facilities',
        'infrastructure_types': ['schools'],
        'priority_weight': 0.8,
        'icon': '🏫'
    },
    'universities': {
        'name': 'Universities & Higher Education',
        'description': 'University campuses and higher education facilities',
        'infrastructure_types': ['universities'],
        'priority_weight': 0.9,
        'icon': '🎓'
    },
    'transportation': {
        'name': 'Transportation & Streets',
        'description': 'Road networks, streets, and transportation infrastructure',
        'infrastructure_types': ['streets'],
        'priority_weight': 0.7,
        'icon': '🛣️'
    },
    'municipal': {
        'name': 'Municipal Infrastructure',
        'description': 'Municipal buildings, administrative centers, and local governance',
        'infrastructure_types': ['municipalities'],
        'priority_weight': 0.6,
        'icon': '🏛️'
    },
    'utilities': {
        'name': 'Utilities & Services',
        'description': 'Water, electricity, fuel stations, and utility infrastructure',
        'infrastructure_types': ['water_util', 'fuel_util'],
        'priority_weight': 0.8,
        'icon': '⚡'
    }
}

# ======================================================
# Project Selection Interface
# ======================================================

def display_project_menu():
    """Display available project types for user selection"""
    print("\n" + "="*80)
    print("GAZA RECONSTRUCTION PROJECT SELECTION SYSTEM")
    print("="*80)
    print("Select project types to focus reconstruction efforts on:")
    print()

    for key, project in PROJECT_TYPES.items():
        print(f"{project['icon']} {key.upper()}: {project['name']}")
        print(f"   {project['description']}")
        print(f"   Priority Weight: {project['priority_weight']}")
        print()

    print("Available commands:")
    print("  'all' - Select all project types")
    print("  'healthcare' - Focus on healthcare facilities")
    print("  'education' - Focus on educational institutions")
    print("  'universities' - Focus on universities and higher education")
    print("  'transportation' - Focus on streets and transportation")
    print("  'municipal' - Focus on municipal infrastructure")
    print("  'utilities' - Focus on utilities and services")
    print("  'quit' - Exit the system")
    print()

def get_user_project_selection():
    """Get user's project type selection"""
    while True:
        selection = input("Enter your project selection (or 'help' for options): ").strip().lower()

        if selection == 'help':
            display_project_menu()
            continue
        elif selection == 'quit':
            return None
        elif selection == 'all':
            return list(PROJECT_TYPES.keys())
        elif selection in PROJECT_TYPES:
            return [selection]
        elif selection.replace(' ', '').replace(',', '') == '':
            print("Please make a selection.")
            continue
        else:
            # Try to parse multiple selections
            selections = [s.strip() for s in selection.split(',')]
            valid_selections = []
            invalid_selections = []

            for sel in selections:
                if sel in PROJECT_TYPES:
                    valid_selections.append(sel)
                else:
                    invalid_selections.append(sel)

            if invalid_selections:
                print(f"Invalid selections: {', '.join(invalid_selections)}")
                print("Valid options:", ', '.join(PROJECT_TYPES.keys()))
            elif valid_selections:
                return valid_selections
            else:
                print("No valid selections made.")

# ======================================================
# Infrastructure Analysis and Display
# ======================================================

def check_facility_damage(facility, damage_gdf, zone):
    """Check if a facility is located in a damaged area"""
    if damage_gdf is None or damage_gdf.empty:
        return False

    # Check if there are damage sites within a certain radius of the facility
    facility_point = facility.geometry.centroid
    # Look for damage sites within 500 meters of the facility
    nearby_damage = damage_gdf[damage_gdf.geometry.distance(facility_point) <= 500]

    return len(nearby_damage) > 0

def analyze_infrastructure_needs(
    hex_gdf,
    infrastructure_layers,
    selected_projects,
    damage_gdf=None,
    zone_limit=DEFAULT_ANALYSIS_ZONE_LIMIT,
    top_damaged=DEFAULT_TOP_DAMAGED_FACILITIES,
    top_priority=DEFAULT_TOP_PRIORITY_FACILITIES,
):
    """Analyze and display infrastructure needs for selected project types"""
    print("\n" + "="*80)
    print("INFRASTRUCTURE NEEDS ANALYSIS")
    print("="*80)

    total_needs = {}
    analysis_zone_count = min(zone_limit, len(hex_gdf))
    print(f"Analyzing top {analysis_zone_count} priority zones (configurable).")

    for project_type in selected_projects:
        if project_type in PROJECT_TYPES:
            project_info = PROJECT_TYPES[project_type]
            print(f"\n{project_info['icon']} {project_info['name'].upper()}")
            print("-" * 50)

            infrastructure_types = project_info['infrastructure_types']
            project_needs = []

            for infra_type in infrastructure_types:
                # Map infrastructure type to layer key
                layer_key = infra_type
                if infra_type == 'major_hospitals_count':
                    layer_key = 'hospitals'
                elif infra_type == 'hospitals_count':
                    layer_key = 'hospitals'
                elif infra_type == 'schools':
                    layer_key = 'schools'
                elif infra_type == 'universities':
                    layer_key = 'universities'
                elif infra_type == 'streets':
                    layer_key = 'streets'
                elif infra_type == 'municipalities':
                    layer_key = 'municipalities'
                
                print(f"   - Checking {infra_type} -> layer_key: {layer_key}")
                
                if layer_key not in infrastructure_layers:
                    print(f"   - WARNING: {layer_key} not found in infrastructure_layers")
                    print(f"   - Available keys: {list(infrastructure_layers.keys())}")
                    continue
                    
                layer_data = infrastructure_layers[layer_key]
                print(f"   - Layer {layer_key}: {len(layer_data)} features, empty={layer_data.empty}")

                if not layer_data.empty:
                        print(f"   - Found {len(layer_data)} {layer_key} in infrastructure layers")
                        
                        # For universities, municipalities, and streets - show ALL facilities
                        if project_type in ['universities', 'municipal', 'transportation']:
                            print(f"  📍 All {infra_type.replace('_', ' ').title()} in Gaza Strip:")
                            
                            # For streets, show summary by road type and damage
                            if project_type == 'transportation' and 'RoadType' in layer_data.columns:
                                # Sort by reconstruction priority
                                layer_data_sorted = layer_data.sort_values('reconstruction_priority', ascending=False)
                                
                                road_summary = layer_data.groupby('RoadType').agg({
                                    'Length_km': 'sum',
                                    'damage_severity': 'sum'
                                }).round(2)
                                print(f"    Road Network Summary:")
                                for road_type, row in road_summary.iterrows():
                                    damage_status = "🚨 DAMAGED" if row['damage_severity'] > 0 else "✓ Intact"
                                    print(f"    {damage_status} {road_type} Roads: {row['Length_km']:.1f} km (Damage: {row['damage_severity']:.0f})")
                                
                                # Show strategic roads (near hospitals or major arteries)
                                strategic_roads = layer_data_sorted[
                                    (layer_data_sorted['damage_severity'] > 0) & 
                                    ((layer_data_sorted.get('near_hospital', False) == True) | 
                                     (layer_data_sorted.get('is_major_artery', False) == True))
                                ].head(10)
                                
                                if not strategic_roads.empty:
                                    print(f"\n    ⭐ STRATEGIC Priority Roads (Near Hospitals/Major Arteries):")
                                    for idx, road in strategic_roads.iterrows():
                                        municipality = road.get('municipality', road.get('Governorate', 'Unknown'))
                                        tags = []
                                        if road.get('near_hospital', False):
                                            tags.append("🏥 Near Hospital")
                                        if road.get('is_major_artery', False):
                                            tags.append("🛍️ Major Artery")
                                        tag_str = " ".join(tags)
                                        print(f"    🔴 {road.get('RoadType', 'Road')} in {municipality} - {road['Length_km']:.2f} km (Damage: {road['damage_severity']:.0f}) {tag_str}")
                                
                                # Show top damaged roads by priority
                                damaged_roads = layer_data_sorted[layer_data_sorted['damage_severity'] > 0].head(15)
                                if not damaged_roads.empty:
                                    print(f"\n    Top Damaged Road Segments by Priority:")
                                    for idx, road in damaged_roads.iterrows():
                                        municipality = road.get('municipality', road.get('Governorate', 'Unknown'))
                                        priority_score = road.get('reconstruction_priority', 0)
                                        print(f"    💥 {road.get('RoadType', 'Road')} in {municipality} - {road['Length_km']:.2f} km (Damage: {road['damage_severity']:.0f}, Priority: {priority_score:.0f})")
                            else:
                                # For universities and municipalities, show individual facilities
                                for idx, facility in layer_data.head(20).iterrows():
                                    facility_name = get_facility_name(facility, layer_key)
                                    coords = (facility.geometry.centroid.y, facility.geometry.centroid.x)
                                    print(f"    • {facility_name} (Coordinates: {coords[0]:.4f}, {coords[1]:.4f})")
                                if len(layer_data) > 20:
                                    print(f"    ... and {len(layer_data) - 20} more facilities")
                            
                            project_needs.extend([{
                                'name': get_facility_name(facility, layer_key),
                                'zone_id': 'N/A',
                                'municipality': facility.get('municipality', facility.get('Governorate', 'Gaza Strip')),
                                'priority_rank': idx + 1,
                                'damage_level': facility.get('damage_severity', 0) if 'damage_severity' in facility.index else 0,
                                'coordinates': (facility.geometry.centroid.y, facility.geometry.centroid.x),
                                'is_damaged': facility.get('damage_severity', 0) > 0 if 'damage_severity' in facility.index else False
                            } for idx, facility in layer_data.iterrows()])
                            continue
                        
                        # Find facilities in priority zones
                        damaged_facilities = []
                        priority_facilities = []

                        for idx, zone in hex_gdf.head(analysis_zone_count).iterrows():
                            # Find facilities within this zone (use buffer for better detection)
                            zone_buffer = zone.geometry.buffer(500)  # 500m buffer
                            facilities = layer_data[layer_data.intersects(zone_buffer)]
                            if not facilities.empty:
                                for _, facility in facilities.iterrows():
                                    # For major hospitals project, show ONLY major hospitals
                                    if project_type == 'major_hospitals':
                                        if not facility.get('is_major', False):
                                            continue
                                    # For healthcare project, show ONLY non-major hospitals/clinics
                                    elif project_type == 'healthcare':
                                        if facility.get('is_major', False):
                                            continue
                                    
                                    facility_info = {
                                        'name': get_facility_name(facility, layer_key),
                                        'zone_id': f"ZONE-{idx+1:03d}",
                                        'municipality': zone.get('primary_municipality', 'Unknown'),
                                        'priority_rank': idx + 1,
                                        'damage_level': zone.get('damage_count', 0),
                                        'coordinates': (facility.geometry.centroid.y, facility.geometry.centroid.x)
                                    }

                                    if project_type == 'major_hospitals':
                                        facility_info['name'] = f"CRITICAL: {facility_info['name']}"

                                    # Check if damaged
                                    is_damaged = check_facility_damage(facility, damage_gdf, zone) if damage_gdf is not None else False
                                    facility_info['is_damaged'] = is_damaged

                                    if is_damaged or idx < 10:
                                        if is_damaged:
                                            damaged_facilities.append(facility_info)
                                        else:
                                            priority_facilities.append(facility_info)

                        # Show top damaged facilities first (deduplicated)
                        if damaged_facilities:
                            damaged_facilities = (
                                pd.DataFrame(damaged_facilities)
                                .sort_values(["damage_level", "priority_rank"], ascending=[False, True])
                                .drop_duplicates(subset=["name", "zone_id"])
                                .to_dict("records")
                            )
                            print(f"  TOP DAMAGED {infra_type.replace('_', ' ').title()} requiring reconstruction:")
                            for facility in damaged_facilities[:top_damaged]:
                                damage_indicator = "[CRITICAL]" if facility["damage_level"] > 10 else "[WARN]"
                                print(
                                    f"    {damage_indicator} {facility['name']} "
                                    f"(Zone {facility['zone_id']}, Priority #{facility['priority_rank']}, "
                                    f"{facility['damage_level']} damage sites nearby)"
                                )
                            if len(damaged_facilities) > top_damaged:
                                print(f"    ... and {len(damaged_facilities) - top_damaged} more damaged facilities")

                        # Show facilities in priority zones
                        if priority_facilities:
                            priority_facilities = (
                                pd.DataFrame(priority_facilities)
                                .sort_values(["priority_rank", "damage_level"], ascending=[True, False])
                                .drop_duplicates(subset=["name", "zone_id"])
                                .to_dict("records")
                            )
                            print(f"  PRIORITY {infra_type.replace('_', ' ').title()} in high-priority zones:")
                            for facility in priority_facilities[:top_priority]:
                                print(f"    - {facility['name']} (Zone {facility['zone_id']}, Priority #{facility['priority_rank']})")
                            if len(priority_facilities) > top_priority:
                                print(f"    ... and {len(priority_facilities) - top_priority} more facilities")

                        project_needs.extend(damaged_facilities + priority_facilities)

            total_needs[project_type] = project_needs

            if not project_needs:
                print("  No specific facilities identified in priority zones.")
                print("  (This may be due to limited data availability)")

    return total_needs

def get_facility_name(facility, infra_type):
    """Extract facility name from geodataframe row"""
    # Try different possible name columns
    name_columns = ['name', 'Name', 'NAME', 'facility_name', 'hospital_name', 'school_name']

    for col in name_columns:
        if col in facility.index and pd.notna(facility[col]) and str(facility[col]).strip():
            return str(facility[col]).strip()

    # Fallback naming based on type and location
    if infra_type == 'hospitals':
        return f"Hospital/Clinic at {facility.geometry.centroid.y:.4f}, {facility.geometry.centroid.x:.4f}"
    elif infra_type == 'schools':
        return f"School at {facility.geometry.centroid.y:.4f}, {facility.geometry.centroid.x:.4f}"
    elif infra_type == 'universities':
        return f"University at {facility.geometry.centroid.y:.4f}, {facility.geometry.centroid.x:.4f}"
    elif infra_type == 'water_util':
        return f"Water Facility at {facility.geometry.centroid.y:.4f}, {facility.geometry.centroid.x:.4f}"
    elif infra_type == 'fuel_util':
        return f"Fuel/Energy Facility at {facility.geometry.centroid.y:.4f}, {facility.geometry.centroid.x:.4f}"
    elif infra_type == 'streets':
        return f"Street Segment at {facility.geometry.centroid.y:.4f}, {facility.geometry.centroid.x:.4f}"
    elif infra_type == 'municipalities':
        return f"Municipal Building at {facility.geometry.centroid.y:.4f}, {facility.geometry.centroid.x:.4f}"
    else:
        return f"{infra_type.title()} Facility at {facility.geometry.centroid.y:.4f}, {facility.geometry.centroid.x:.4f}"

# ======================================================
# Project Generation for Selected Types
# ======================================================

def generate_projects_for_selection(hex_gdf, infrastructure_layers, selected_projects, damage_gdf, top_n=30):
    """Generate reconstruction projects focused on selected project types"""
    print(f"\nGenerating reconstruction projects for selected types: {', '.join(selected_projects)}")

    # Adjust scoring weights based on selected projects
    adjusted_weights = SCORING_WEIGHTS['default'].copy()

    # Boost weights for selected project types
    for project_type in selected_projects:
        if project_type in PROJECT_TYPES:
            infra_types = PROJECT_TYPES[project_type]['infrastructure_types']
            weight_boost = PROJECT_TYPES[project_type]['priority_weight']

            for infra_type in infra_types:
                if infra_type == 'hospitals':
                    adjusted_weights['hospitals'] *= weight_boost
                elif infra_type == 'schools':
                    # Education is handled separately in SCORING_WEIGHTS
                    pass  # We'll handle this below
                elif infra_type == 'water_util':
                    adjusted_weights['water'] *= weight_boost
                elif infra_type == 'fuel_util':
                    adjusted_weights['fuel'] *= weight_boost
                elif infra_type == 'streets':
                    adjusted_weights['streets'] *= weight_boost
                elif infra_type == 'municipalities':
                    adjusted_weights['municipalities'] *= weight_boost

    # Handle education separately since it's not in the default weights
    if 'education' in selected_projects:
        weight_boost = PROJECT_TYPES['education']['priority_weight']
        # Add education weight to the adjusted weights
        adjusted_weights['education'] = SCORING_WEIGHTS.get('education', 0.02) * weight_boost

    # Normalize weights
    total_weight = sum(adjusted_weights.values())
    for key in adjusted_weights:
        adjusted_weights[key] /= total_weight

    print(f"Adjusted scoring weights: {adjusted_weights}")

    # Get top priority zones with adjusted weights
    top_zones = hex_gdf.head(top_n).copy()

    projects = []

    for idx, row in top_zones.iterrows():
        # Create multiple projects per zone based on infrastructure needs
        zone_projects = create_zone_projects(row, idx, selected_projects, infrastructure_layers, damage_gdf)
        projects.extend(zone_projects)

    projects_df = pd.DataFrame(projects)

    if not projects_df.empty:
        # Sort by adjusted priority
        projects_df = projects_df.sort_values('Adjusted_Priority_Score', ascending=False).reset_index(drop=True)
        projects_df['Final_Priority_Rank'] = range(1, len(projects_df) + 1)
        projects_df['Priority_Rank'] = projects_df['Final_Priority_Rank']  # Add alias for compatibility

    return projects_df

def create_zone_projects(zone_row, zone_idx, selected_projects, infrastructure_layers, damage_gdf=None):
    """Create multiple projects for a single zone based on selected project types"""
    projects = []

    for project_type in selected_projects:
        if project_type in PROJECT_TYPES:
            project_info = PROJECT_TYPES[project_type]
            infra_types = project_info['infrastructure_types']

            # Check if zone has relevant infrastructure
            has_relevant_infra = False
            damaged_infra_count = 0
            facility_names = []

            for infra_type in infra_types:
                count_col = f"{infra_type}_count"
                if count_col in zone_row.index and zone_row[count_col] > 0:
                    has_relevant_infra = True

                    # Check for damaged facilities of this type and collect names
                    if infra_type in infrastructure_layers and damage_gdf is not None:
                        layer_data = infrastructure_layers[infra_type]
                        if not layer_data.empty:
                            facilities = layer_data[layer_data.intersects(zone_row.geometry)]
                            for _, facility in facilities.iterrows():
                                if check_facility_damage(facility, damage_gdf, zone_row):
                                    damaged_infra_count += 1
                                    # Get facility name
                                    facility_name = get_facility_name(facility, infra_type)
                                    if facility_name and facility_name not in facility_names:
                                        facility_names.append(facility_name)

            if has_relevant_infra or zone_row.get('damage_count', 0) > 5:  # Include high-damage zones
                # Create project name with specific facilities if available
                if facility_names:
                    # Use the first facility name as the primary project name
                    primary_facility = facility_names[0]
                    if len(facility_names) > 1:
                        project_name = f"{primary_facility} (+{len(facility_names)-1} facilities)"
                    else:
                        project_name = primary_facility
                else:
                    # Fallback to generic name
                    project_name = f"{project_info['name']} - {zone_row.get('primary_municipality', 'Unknown')}"

                # Create project for this type
                project = {
                    'Project_ID': f"GAZA-{project_type.upper()}-{zone_idx+1:03d}",
                    'Project_Name': project_name,
                    'Zone_ID': zone_row.get('zone_id', f"ZONE-{zone_idx+1:03d}"),
                    'Municipality': zone_row.get('primary_municipality', 'Unknown'),
                    'Project_Type': project_type,
                    'Project_Category': project_info['name'],
                    'Base_Priority_Rank': zone_idx + 1,
                    'AI_Score': round(zone_row.get('ai_score', 0), 3),
                    'Damage_Level': zone_row.get('damage_count', 0),
                    'Damaged_Infrastructure': damaged_infra_count,
                    'Facility_Names': '; '.join(facility_names) if facility_names else 'Multiple facilities',
                    'Rebuilding_Strategy': zone_row.get('rebuilding_strategy', {}).get('strategy', 'Balanced_Reconstruction') if isinstance(zone_row.get('rebuilding_strategy'), dict) else 'Balanced_Reconstruction',
                    'Required_Units': estimate_required_units(zone_row, project_type),
                    'Adjusted_Priority_Score': calculate_adjusted_score(zone_row, project_type),
                    'Timeline_Months': estimate_project_timeline(project_type),
                    'Infrastructure_Type': project_info['name'],
                    'Status': 'Planned',
                    'Funding_Source': 'TBD',
                    'Implementing_Agency': 'TBD',
                    'Expert_Notes': generate_project_notes(zone_row, project_type, damaged_infra_count)
                }

                projects.append(project)

    return projects

def calculate_adjusted_score(zone_row, project_type):
    """Calculate adjusted priority score for specific project type"""
    base_score = zone_row.get('ai_score', 0)
    weight = PROJECT_TYPES[project_type]['priority_weight']

    # Add bonus for relevant infrastructure
    infra_bonus = 0
    infra_types = PROJECT_TYPES[project_type]['infrastructure_types']
    for infra_type in infra_types:
        count_col = f"{infra_type}_count"
        if count_col in zone_row.index:
            infra_bonus += zone_row[count_col] * 0.1

    return base_score * weight + infra_bonus

def estimate_required_units(zone_row, project_type):
    """Estimate required units for specific project type"""
    damage_level = zone_row.get('damage_count', 0)

    # Base units per damage site
    base_units_per_damage = {
        'healthcare': 15,    # Healthcare needs more units
        'education': 12,     # Educational facilities
        'universities': 20,  # Universities need more units (larger facilities)
        'transportation': 8, # Streets need fewer units
        'municipal': 10,     # Municipal buildings
        'utilities': 6       # Utilities infrastructure
    }

    units_per_damage = base_units_per_damage.get(project_type, 10)

    # Calculate required units
    required_units = max(int(damage_level * units_per_damage), 50)  # Minimum 50 units

    # Adjust based on infrastructure presence
    infra_types = PROJECT_TYPES[project_type]['infrastructure_types']
    infra_bonus = 0
    for infra_type in infra_types:
        count_col = f"{infra_type}_count"
        if count_col in zone_row.index:
            infra_bonus += zone_row[count_col] * 20  # Bonus units for existing infrastructure

    return required_units + infra_bonus

def estimate_project_timeline(project_type):
    """Estimate timeline for specific project type"""
    base_timelines = {
        'healthcare': 12,   # Healthcare takes longer
        'education': 10,    # Education facilities
        'universities': 18, # Universities take much longer (complex facilities, specialized equipment)
        'transportation': 6, # Streets can be rebuilt faster
        'municipal': 15,    # Municipal buildings complex
        'utilities': 8      # Utilities vary
    }

    return base_timelines.get(project_type, 12)

def create_zone_projects(zone_row, zone_idx, selected_projects, infrastructure_layers, damage_gdf):
    """Create reconstruction projects for a specific zone"""
    projects = []

    for project_type in selected_projects:
        if project_type not in PROJECT_TYPES:
            continue

        project_info = PROJECT_TYPES[project_type]
        infra_types = project_info['infrastructure_types']

        # Count damaged infrastructure in this zone and collect facility names
        damaged_infra_count = 0
        facility_names = []

        if damage_gdf is not None and not damage_gdf.empty:
            # Check for damaged infrastructure within this zone
            zone_geom = zone_row.geometry
            damaged_sites = damage_gdf[damage_gdf.intersects(zone_geom)]
            damaged_infra_count = len(damaged_sites)

        # Collect facility names for this project type
        for infra_type in infra_types:
            if infra_type in infrastructure_layers:
                layer_data = infrastructure_layers[infra_type]
                if not layer_data.empty:
                    facilities = layer_data[layer_data.intersects(zone_row.geometry)]
                    for _, facility in facilities.iterrows():
                        facility_name = get_facility_name(facility, infra_type)
                        if facility_name and facility_name not in facility_names:
                            facility_names.append(facility_name)

        # Create project name with specific facilities if available
        if facility_names:
            # Use the first facility name as the primary project name
            primary_facility = facility_names[0]
            if len(facility_names) > 1:
                project_name = f"{primary_facility} (+{len(facility_names)-1} facilities)"
            else:
                project_name = primary_facility
        else:
            # Fallback to generic name
            project_name = f"{project_info['name']} - {zone_row.get('primary_municipality', 'Unknown')}"

        # Create project entry
        project = {
            'Project_ID': f"GAZA-{zone_idx+1:03d}-{project_type[:3].upper()}",
            'Project_Name': project_name,
            'Zone_ID': f"ZONE-{zone_idx+1:03d}",
            'Municipality': zone_row.get('primary_municipality', 'Unknown'),
            'Project_Type': project_type.title(),
            'Infrastructure_Type': PROJECT_TYPES[project_type]['name'],  # Add infrastructure type
            'Priority_Rank': zone_idx + 1,
            'AI_Score': round(zone_row.get('ai_score', 0), 3),
            'Damage_Level': int(zone_row.get('damage_count', 0)),
            'Facility_Names': '; '.join(facility_names) if facility_names else 'Multiple facilities',
            'Rebuilding_Strategy': zone_row.get('rebuilding_strategy', {}).get('strategy', 'Balanced_Reconstruction'),
            'Required_Units': estimate_required_units(zone_row, project_type),
            'Timeline_Months': estimate_project_timeline(project_type),
            'Status': 'Planned',
            'Funding_Source': 'TBD',
            'Implementing_Agency': 'TBD',
            'Expert_Notes': generate_project_notes(zone_row, project_type, damaged_infra_count),
            'Adjusted_Priority_Score': zone_row.get('final_score', 0),
            'Coordinates': (zone_row.geometry.centroid.y, zone_row.geometry.centroid.x)
        }

        projects.append(project)

    return projects

def generate_project_notes(zone_row, project_type, damaged_infra_count=0):
    """Generate expert notes for specific project type"""
    notes = []

    # Add damaged infrastructure information
    if damaged_infra_count > 0:
        notes.append(f"🚨 CRITICAL: {damaged_infra_count} infrastructure facilities directly damaged")


    if project_type == 'major_hospitals':
        hospital_names = zone_row.get('major_hospital_names', 'None')
        if hospital_names != 'None':
            notes.append(f"🏥 STRATEGIC HUB: Reconstruction of {hospital_names}")
        else:
            notes.append("High-priority medical zone for regional support")

    elif project_type == 'healthcare':
        hospital_count = zone_row.get('hospitals_count', 0)
        if hospital_count > 0:
            notes.append(f"Critical healthcare infrastructure: {int(hospital_count)} facilities affected")

    elif project_type == 'education':
        school_count = zone_row.get('schools_count', 0)
        if school_count > 0:
            notes.append(f"Educational facilities: {int(school_count)} schools requiring reconstruction")

    elif project_type == 'universities':
        university_count = zone_row.get('universities_count', 0)
        if university_count > 0:
            notes.append(f"Higher education facilities: {int(university_count)} universities requiring reconstruction")

    elif project_type == 'transportation':
        street_count = zone_row.get('streets_count', 0)
        if street_count > 0:
            notes.append(f"Transportation network: {int(street_count)} street segments damaged")

    elif project_type == 'municipal':
        notes.append("Municipal governance and administrative infrastructure reconstruction")

    elif project_type == 'utilities':
        water_count = zone_row.get('water_util_count', 0)
        fuel_count = zone_row.get('fuel_util_count', 0)
        if water_count > 0:
            notes.append(f"Water infrastructure: {int(water_count)} facilities affected")
        if fuel_count > 0:
            notes.append(f"Energy infrastructure: {int(fuel_count)} facilities impacted")

    damage_level = zone_row.get('damage_count', 0)
    if damage_level > 10:
        notes.append(f"High damage concentration: {int(damage_level)} sites affected")

    return " | ".join(notes) if notes else "Standard reconstruction requirements"

