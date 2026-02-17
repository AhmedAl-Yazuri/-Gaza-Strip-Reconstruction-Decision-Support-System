# ======================================================
# data_erd_generator.py - Data ERD Documentation Generator
# ======================================================

import pandas as pd
import geopandas as gpd
from datetime import datetime
import os

def generate_data_erd(damage_gdf, infrastructure_layers, hex_gdf, projects_df, output_path=None):
    """Generate comprehensive ERD documentation for all project data"""
    
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"DATA_ERD_DOCUMENTATION_{timestamp}.txt"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("GAZA RECONSTRUCTION DSS - DATA ENTITY RELATIONSHIP DIAGRAM (ERD)\n")
        f.write("=" * 100 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # ===== DAMAGE DATA =====
        f.write("=" * 100 + "\n")
        f.write("1. DAMAGE ASSESSMENT DATA (Primary Input)\n")
        f.write("=" * 100 + "\n\n")
        
        if damage_gdf is not None and not damage_gdf.empty:
            f.write(f"Source: UNOSAT Gaza Strip Damage Assessment\n")
            f.write(f"Total Records (Rows): {len(damage_gdf):,}\n")
            f.write(f"Total Attributes (Columns): {len(damage_gdf.columns)}\n")
            f.write(f"Geometry Type: {damage_gdf.geometry.geom_type.unique()[0] if len(damage_gdf) > 0 else 'N/A'}\n")
            f.write(f"Coordinate System: {damage_gdf.crs}\n\n")
            
            f.write("Key Attributes:\n")
            f.write("-" * 50 + "\n")
            for col in damage_gdf.columns:
                dtype = str(damage_gdf[col].dtype)
                non_null = damage_gdf[col].notna().sum()
                null_count = damage_gdf[col].isna().sum()
                f.write(f"  • {col}\n")
                f.write(f"    - Data Type: {dtype}\n")
                f.write(f"    - Non-Null Values: {non_null:,} ({non_null/len(damage_gdf)*100:.1f}%)\n")
                f.write(f"    - Null Values: {null_count:,} ({null_count/len(damage_gdf)*100:.1f}%)\n")
                
                if col == 'Municipality':
                    unique_vals = damage_gdf[col].value_counts()
                    f.write(f"    - Unique Values: {len(unique_vals)}\n")
                    f.write(f"    - Distribution:\n")
                    for val, count in unique_vals.head(10).items():
                        f.write(f"      * {val}: {count:,} ({count/len(damage_gdf)*100:.1f}%)\n")
                elif damage_gdf[col].dtype in ['int64', 'float64'] and col != 'geometry':
                    f.write(f"    - Min: {damage_gdf[col].min()}\n")
                    f.write(f"    - Max: {damage_gdf[col].max()}\n")
                    f.write(f"    - Mean: {damage_gdf[col].mean():.2f}\n")
                f.write("\n")
        
        # ===== INFRASTRUCTURE LAYERS =====
        f.write("\n" + "=" * 100 + "\n")
        f.write("2. INFRASTRUCTURE LAYERS DATA\n")
        f.write("=" * 100 + "\n\n")
        
        for layer_name, layer_gdf in infrastructure_layers.items():
            if layer_gdf is not None and not layer_gdf.empty:
                f.write(f"Layer: {layer_name.upper()}\n")
                f.write("-" * 50 + "\n")
                f.write(f"Total Records: {len(layer_gdf):,}\n")
                f.write(f"Total Attributes: {len(layer_gdf.columns)}\n")
                f.write(f"Geometry Type: {layer_gdf.geometry.geom_type.unique()[0] if len(layer_gdf) > 0 else 'N/A'}\n")
                f.write(f"Coordinate System: {layer_gdf.crs}\n\n")
                
                f.write("Attributes:\n")
                for col in layer_gdf.columns:
                    if col != 'geometry':
                        dtype = str(layer_gdf[col].dtype)
                        non_null = layer_gdf[col].notna().sum()
                        f.write(f"  • {col}: {dtype} ({non_null:,} non-null)\n")
                
                # Special statistics for streets
                if layer_name == 'streets' and 'damage_severity' in layer_gdf.columns:
                    f.write("\nStreet Damage Statistics:\n")
                    damage_dist = layer_gdf['damage_severity'].value_counts().sort_index()
                    for level, count in damage_dist.items():
                        f.write(f"  • Level {int(level)}: {count:,} streets ({count/len(layer_gdf)*100:.1f}%)\n")
                    
                    if 'Length_km' in layer_gdf.columns:
                        total_length = layer_gdf['Length_km'].sum()
                        f.write(f"\nTotal Street Length: {total_length:,.2f} km\n")
                
                f.write("\n")
        
        # ===== HEXAGONAL GRID =====
        f.write("\n" + "=" * 100 + "\n")
        f.write("3. SPATIAL ANALYSIS GRID (Hexagonal Zones)\n")
        f.write("=" * 100 + "\n\n")
        
        if hex_gdf is not None and not hex_gdf.empty:
            f.write(f"Total Zones: {len(hex_gdf):,}\n")
            f.write(f"Total Attributes: {len(hex_gdf.columns)}\n")
            f.write(f"Geometry Type: Hexagonal Polygons\n")
            f.write(f"Coordinate System: {hex_gdf.crs}\n\n")
            
            f.write("Key Computed Attributes:\n")
            f.write("-" * 50 + "\n")
            
            key_attrs = ['zone_id', 'damage_count', 'ai_score', 'damage_age', 'primary_municipality', 
                        'rebuilding_strategy', 'hospitals_count', 'schools_count', 'water_util_count']
            
            for col in key_attrs:
                if col in hex_gdf.columns:
                    dtype = str(hex_gdf[col].dtype)
                    f.write(f"  • {col}: {dtype}\n")
                    
                    if hex_gdf[col].dtype in ['int64', 'float64']:
                        f.write(f"    - Min: {hex_gdf[col].min()}\n")
                        f.write(f"    - Max: {hex_gdf[col].max()}\n")
                        f.write(f"    - Mean: {hex_gdf[col].mean():.2f}\n")
                        f.write(f"    - Median: {hex_gdf[col].median():.2f}\n")
                    elif col == 'primary_municipality':
                        unique_vals = hex_gdf[col].value_counts()
                        f.write(f"    - Unique Municipalities: {len(unique_vals)}\n")
                        for val, count in unique_vals.head(5).items():
                            f.write(f"      * {val}: {count:,} zones\n")
                    f.write("\n")
        
        # ===== PROJECTS DATA =====
        f.write("\n" + "=" * 100 + "\n")
        f.write("4. RECONSTRUCTION PROJECTS DATA (Output)\n")
        f.write("=" * 100 + "\n\n")
        
        if projects_df is not None and not projects_df.empty:
            f.write(f"Total Projects: {len(projects_df):,}\n")
            f.write(f"Total Attributes: {len(projects_df.columns)}\n\n")
            
            f.write("Attributes:\n")
            f.write("-" * 50 + "\n")
            for col in projects_df.columns:
                dtype = str(projects_df[col].dtype)
                non_null = projects_df[col].notna().sum()
                f.write(f"  • {col}: {dtype} ({non_null:,} non-null)\n")
            
            f.write("\nProject Type Distribution:\n")
            if 'Infrastructure_Type' in projects_df.columns:
                type_dist = projects_df['Infrastructure_Type'].value_counts()
                for ptype, count in type_dist.items():
                    f.write(f"  • {ptype}: {count:,} projects ({count/len(projects_df)*100:.1f}%)\n")
            
            f.write("\nPhase Distribution:\n")
            if 'Phase' in projects_df.columns:
                phase_dist = projects_df['Phase'].value_counts().sort_index()
                for phase, count in phase_dist.items():
                    f.write(f"  • Phase {int(phase)}: {count:,} projects ({count/len(projects_df)*100:.1f}%)\n")
            
            f.write("\n")
        
        # ===== DATA RELATIONSHIPS =====
        f.write("\n" + "=" * 100 + "\n")
        f.write("5. DATA RELATIONSHIPS (ERD)\n")
        f.write("=" * 100 + "\n\n")
        
        f.write("Primary Relationships:\n")
        f.write("-" * 50 + "\n\n")
        
        f.write("1. DAMAGE_DATA (1) ──> (Many) HEXAGONAL_ZONES\n")
        f.write("   - Relationship: Spatial Join\n")
        f.write("   - Key: geometry (spatial intersection)\n")
        f.write("   - Description: Each damage site is assigned to one hexagonal zone\n\n")
        
        f.write("2. INFRASTRUCTURE_LAYERS (Many) ──> (Many) HEXAGONAL_ZONES\n")
        f.write("   - Relationship: Spatial Join\n")
        f.write("   - Key: geometry (spatial intersection/proximity)\n")
        f.write("   - Description: Infrastructure facilities are counted within each zone\n\n")
        
        f.write("3. HEXAGONAL_ZONES (1) ──> (Many) PROJECTS\n")
        f.write("   - Relationship: One-to-Many\n")
        f.write("   - Key: zone_id\n")
        f.write("   - Description: Each zone can have multiple reconstruction projects\n\n")
        
        f.write("4. MUNICIPALITIES (1) ──> (Many) HEXAGONAL_ZONES\n")
        f.write("   - Relationship: One-to-Many\n")
        f.write("   - Key: primary_municipality\n")
        f.write("   - Description: Each zone belongs to one primary municipality\n\n")
        
        # ===== DATA FLOW =====
        f.write("\n" + "=" * 100 + "\n")
        f.write("6. DATA PROCESSING FLOW\n")
        f.write("=" * 100 + "\n\n")
        
        f.write("Input Data:\n")
        f.write("  1. UNOSAT Damage Assessment (GDB) → damage_gdf\n")
        f.write("  2. Infrastructure Layers (GPKG/OSM) → infrastructure_layers\n\n")
        
        f.write("Processing Steps:\n")
        f.write("  1. Create Hexagonal Grid → hex_gdf\n")
        f.write("  2. Spatial Join: Damage → Hexagons\n")
        f.write("  3. Spatial Join: Infrastructure → Hexagons\n")
        f.write("  4. Calculate AI Scores → hex_gdf['ai_score']\n")
        f.write("  5. Determine Strategies → hex_gdf['rebuilding_strategy']\n")
        f.write("  6. Generate Projects → projects_df\n")
        f.write("  7. Assign Phases → projects_df['Phase']\n\n")
        
        f.write("Output Data:\n")
        f.write("  1. Prioritized Hexagonal Zones (hex_gdf)\n")
        f.write("  2. Reconstruction Projects List (projects_df)\n")
        f.write("  3. Interactive Maps (HTML)\n")
        f.write("  4. Excel Reports (XLSX)\n")
        f.write("  5. Documentation (TXT/DOCX)\n\n")
        
        # ===== SUMMARY STATISTICS =====
        f.write("\n" + "=" * 100 + "\n")
        f.write("7. SUMMARY STATISTICS\n")
        f.write("=" * 100 + "\n\n")
        
        total_damage = len(damage_gdf) if damage_gdf is not None else 0
        total_zones = len(hex_gdf) if hex_gdf is not None else 0
        total_projects = len(projects_df) if projects_df is not None else 0
        
        f.write(f"Total Damage Sites: {total_damage:,}\n")
        f.write(f"Total Analysis Zones: {total_zones:,}\n")
        f.write(f"Total Reconstruction Projects: {total_projects:,}\n")
        
        if infrastructure_layers:
            total_hospitals = len(infrastructure_layers.get('hospitals', [])) if infrastructure_layers.get('hospitals') is not None else 0
            total_schools = len(infrastructure_layers.get('schools', [])) if infrastructure_layers.get('schools') is not None else 0
            total_streets = len(infrastructure_layers.get('streets', [])) if infrastructure_layers.get('streets') is not None else 0
            
            f.write(f"Total Hospitals: {total_hospitals:,}\n")
            f.write(f"Total Schools: {total_schools:,}\n")
            f.write(f"Total Streets: {total_streets:,}\n")
        
        f.write("\n" + "=" * 100 + "\n")
        f.write("END OF ERD DOCUMENTATION\n")
        f.write("=" * 100 + "\n")
    
    print(f"   - Data ERD documentation saved to {output_path}")
    return output_path
