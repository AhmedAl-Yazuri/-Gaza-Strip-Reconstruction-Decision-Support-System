# ======================================================
# main.py - Gaza Reconstruction DSS Main Orchestration Script
# ======================================================

import sys
import os
from datetime import datetime

# Add modules directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'reconstruction_modules'))

# Import all modules
from config import *
from data_loader import load_damage_data, load_infrastructure_layers
from spatial_analysis import create_hex_grid, integrate_spatial_data
from municipality_analysis import analyze_damage_patterns, determine_rebuilding_strategy, generate_expert_explanation
from scoring_engine import apply_scoring_pipeline
from project_selector import display_project_menu, get_user_project_selection, analyze_infrastructure_needs
from project_generator import export_projects_to_excel, generate_projects_from_zones
from visualization import create_damage_assessment_map, create_reconstruction_priority_map, create_statistical_dashboard, generate_summary_report
from streets_maps import create_streets_damage_map, create_streets_reconstruction_map
from project_documentation import create_project_documentation
from advanced_maps import create_damage_heatmap, create_damaged_streets_map
from interactive_charts import create_damage_animation, create_3d_damage_visualization
from phased_implementation import assign_project_phases, export_phased_excel
from data_erd_generator import generate_data_erd
from project_generator import generate_street_reconstruction_projects, enrich_projects_with_reference_points
from network_analysis import apply_network_criticality

# ======================================================
# Main Execution Pipeline
# ======================================================

def main():
    """Main execution pipeline for Gaza Reconstruction DSS"""
    print("=" * 80)
    print("GAZA RECONSTRUCTION DECISION SUPPORT SYSTEM")
    print("=" * 80)
    print(f"Version: {SYSTEM_VERSION}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Create output directory
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}/")
    print()

    try:
        # Step 1: Load and validate data
        print("STEP 1: Loading Data")
        print("-" * 20)

        damage_gdf = load_damage_data()
        if damage_gdf is None or damage_gdf.empty:
            print("ERROR: No damage data loaded. Exiting.")
            return False

        infrastructure_layers = load_infrastructure_layers()
        infrastructure_layers['streets'] = apply_network_criticality(
            infrastructure_layers.get('streets'),
            infrastructure_layers.get('hospitals'),
            infrastructure_layers.get('water_util')
        )
        print(f"   - Loaded {len(infrastructure_layers)} infrastructure layers")
        print()
        

        # Step 2: Analyze damage patterns
        print("STEP 2: Analyzing Damage Patterns")
        print("-" * 20)

        damage_analysis = analyze_damage_patterns(damage_gdf)
        print()

        # Step 3: Create spatial analysis grid
        print("STEP 3: Creating Spatial Analysis Grid")
        print("-" * 20)

        hex_gdf = create_hex_grid(damage_gdf)
        if hex_gdf.empty:
            print("ERROR: Failed to create hexagonal grid. Exiting.")
            return False

        hex_gdf = integrate_spatial_data(hex_gdf, damage_gdf, infrastructure_layers)
        print()

        # Step 4: Apply municipality-based strategies
        print("STEP 4: Applying Municipality-Based Strategies")
        print("-" * 20)

        hex_gdf['rebuilding_strategy'] = hex_gdf.apply(
            lambda row: determine_rebuilding_strategy(row, damage_analysis), axis=1
        )
        print(f"   - Applied rebuilding strategies to {len(hex_gdf)} zones")
        print()

        # Step 5: Apply AI-enhanced scoring
        print("STEP 5: Applying AI-Enhanced Scoring")
        print("-" * 20)

        hex_gdf = apply_scoring_pipeline(hex_gdf, damage_analysis)
        print()

        # Step 6: Generate expert explanations
        print("STEP 6: Generating Expert Explanations")
        print("-" * 20)

        hex_gdf['expert_explanation'] = hex_gdf.apply(generate_expert_explanation, axis=1)
        print(f"   - Generated explanations for {len(hex_gdf)} zones")
        print()

        # Step 7: Interactive Project Selection
        print("STEP 7: Interactive Project Selection")
        print("-" * 20)

        # Display project selection menu
        display_project_menu()

        # Get user selection
        selected_projects = get_user_project_selection()
        if selected_projects is None:
            print("User exited the system.")
            return False

        print(f"Selected project types: {', '.join(selected_projects)}")
        print()

        # Analyze infrastructure needs for selected projects
        infrastructure_needs = analyze_infrastructure_needs(hex_gdf, infrastructure_layers, selected_projects, damage_gdf)

        # Step 8: Generate reconstruction projects for selected types
        print("STEP 8: Generating Reconstruction Projects")
        print("-" * 20)

        projects_df = generate_projects_from_zones(hex_gdf, selected_projects, top_n=TOP_PROJECTS_COUNT)

        # Generate street reconstruction projects
        streets_layer = infrastructure_layers.get('streets')
        if streets_layer is None or streets_layer.empty:
            streets_projects_df = None
        else:
            streets_projects_df = generate_street_reconstruction_projects(streets_layer, top_n=100)
        
        print("   - Assigning projects to implementation phases...")
        projects_df = assign_project_phases(projects_df, num_phases=4)
        projects_df = enrich_projects_with_reference_points(projects_df, infrastructure_layers)
        
        # Divide street projects into phases
        if streets_projects_df is not None and not streets_projects_df.empty:
            streets_projects_df = assign_project_phases(streets_projects_df, num_phases=4)
            streets_projects_df = enrich_projects_with_reference_points(streets_projects_df, infrastructure_layers)

        # Export projects to Excel
        excel_path = export_projects_to_excel(projects_df, output_path=os.path.join(output_dir, "gaza_reconstruction_projects.xlsx"))
        
        # Export streets projects to separate Excel
        if streets_projects_df is not None and not streets_projects_df.empty:
            streets_excel_path = export_projects_to_excel(streets_projects_df, output_path=os.path.join(output_dir, "gaza_streets_reconstruction_projects.xlsx"))
        print()

        # Step 9: Create visualizations
        print("STEP 9: Creating Visualizations")
        print("-" * 20)

        # Create separate maps
        reconstruction_map_path = create_reconstruction_priority_map(hex_gdf, projects_df, infrastructure_layers, output_path=os.path.join(output_dir, "reconstruction_priority_map.html"))
        
        # Advanced maps
        print("   - Creating advanced visualizations...")
        heatmap_path = create_damage_heatmap(damage_gdf, output_path=os.path.join(output_dir, "damage_heatmap.html"))
        streets_map_path = create_damaged_streets_map(infrastructure_layers['streets'], output_path=os.path.join(output_dir, "damaged_streets_map.html"))
        
        # Interactive animated charts
        print("   - Creating interactive animated charts...")
        damage_animation_path = create_damage_animation(hex_gdf, output_path=os.path.join(output_dir, "damage_animation.html"))
        viz_3d_path = create_3d_damage_visualization(hex_gdf, output_path=os.path.join(output_dir, "3d_damage_visualization.html"))
        
        # Phased implementation visualizations
        print("   - Creating phased implementation plans...")
        phased_excel_path = export_phased_excel(projects_df, output_path=os.path.join(output_dir, "phased_projects.xlsx"))
        
        # Specialized streets maps
        print("   - Creating specialized streets maps...")
        streets_damage_path = None
        streets_recon_path = None
        damage_counts = {}
        priority_counts = {}
        recon_cost = 0

        streets_layer = infrastructure_layers.get('streets')
        if streets_layer is None or streets_layer.empty:
            print("   - Skipping specialized streets maps (no streets data available)")
        else:
            streets_damage_result = create_streets_damage_map(
                streets_layer,
                output_path=os.path.join(output_dir, "streets_damage_map.html")
            )
            if streets_damage_result is not None:
                streets_damage_path, damage_counts = streets_damage_result

            streets_recon_result = create_streets_reconstruction_map(
                streets_layer,
                output_path=os.path.join(output_dir, "streets_reconstruction_map.html")
            )
            if streets_recon_result is not None:
                streets_recon_path, priority_counts, recon_cost = streets_recon_result
        
        # Statistical dashboard
        dashboard_path = create_statistical_dashboard(hex_gdf, projects_df, output_path=os.path.join(output_dir, "statistical_dashboard.png"))

        # Summary report
        report_path = generate_summary_report(hex_gdf, projects_df, damage_analysis, output_path=os.path.join(output_dir, "summary_report.txt"))
        
        # Project documentation
        print("   - Generating project documentation...")
        documentation_path = create_project_documentation(output_path=os.path.join(output_dir, "project_documentation.docx"))
        
        # Data ERD documentation
        print("   - Generating data ERD documentation...")
        erd_path = generate_data_erd(damage_gdf, infrastructure_layers, hex_gdf, projects_df, output_path=os.path.join(output_dir, "data_erd_documentation.txt"))
        print()

        # Step 10: Final summary
        print("EXECUTION COMPLETE")
        print("-" * 20)
        print(f"All outputs saved to: {output_dir}/")
        print("\nGenerated files:")
        if excel_path:
            print(f"   - {os.path.basename(excel_path)}")
        if 'streets_excel_path' in locals() and streets_excel_path:
            print(f"   - {os.path.basename(streets_excel_path)}")
        if phased_excel_path:
            print(f"   - {os.path.basename(phased_excel_path)}")
        if reconstruction_map_path:
            print(f"   - {os.path.basename(reconstruction_map_path)}")
        if heatmap_path:
            print(f"   - {os.path.basename(heatmap_path)}")
        if streets_map_path:
            print(f"   - {os.path.basename(streets_map_path)}")
        if streets_damage_path:
            print(f"   - {os.path.basename(streets_damage_path)}")
        if streets_recon_path:
            print(f"   - {os.path.basename(streets_recon_path)}")
        if damage_animation_path:
            print(f"   - {os.path.basename(damage_animation_path)}")
        if viz_3d_path:
            print(f"   - {os.path.basename(viz_3d_path)}")
        if dashboard_path:
            print(f"   - {os.path.basename(dashboard_path)}")
        if report_path:
            print(f"   - {os.path.basename(report_path)}")
        if documentation_path:
            print(f"   - {os.path.basename(documentation_path)}")
        if erd_path:
            print(f"   - {os.path.basename(erd_path)}")
        print(f"\n✓ Total files in output folder: {len(os.listdir(output_dir))}")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"ERROR: Execution failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

# ======================================================
# Command Line Interface
# ======================================================

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
