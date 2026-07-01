import os
import traceback
from datetime import datetime

from advanced_maps import create_damage_heatmap, create_damaged_streets_map
from config import SYSTEM_VERSION, TOP_PROJECTS_COUNT
from data_erd_generator import generate_data_erd
from data_loader import load_damage_data, load_infrastructure_layers
from interactive_charts import create_3d_damage_visualization, create_damage_animation, create_interactive_dashboard
from municipality_analysis import analyze_damage_patterns, determine_rebuilding_strategy, generate_expert_explanation
from network_analysis import apply_network_criticality
from phased_implementation import assign_project_phases, export_phased_excel
from project_documentation import create_project_documentation
from project_generator import (
    enrich_projects_with_reference_points,
    export_projects_to_excel,
    generate_projects_from_zones,
    generate_street_reconstruction_projects,
)
from project_selector import PROJECT_TYPES, analyze_infrastructure_needs
from scoring_engine import apply_scoring_pipeline
from spatial_analysis import create_hex_grid, integrate_spatial_data
from streets_maps import create_streets_damage_map, create_streets_reconstruction_map
from visualization import create_reconstruction_priority_map, create_statistical_dashboard, generate_summary_report


def _emit(progress_callback, log_callback, step, message, percent):
    if progress_callback:
        progress_callback(step=step, message=message, percent=percent)
    if log_callback:
        log_callback(f"[{step}] {message}")


def run_reconstruction_pipeline(
    selected_projects,
    output_dir="output",
    progress_callback=None,
    log_callback=None,
    profile="full",
):
    """Run the reconstruction workflow using explicit project selections."""
    if not selected_projects:
        raise ValueError("selected_projects must contain at least one project type.")

    invalid = [project for project in selected_projects if project not in PROJECT_TYPES]
    if invalid:
        raise ValueError(f"Unsupported project types: {', '.join(invalid)}")

    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    started_at = datetime.now()
    outputs = {}

    try:
        _emit(progress_callback, log_callback, "load_data", "Loading damage and infrastructure datasets.", 8)
        damage_gdf = load_damage_data()
        if damage_gdf is None or damage_gdf.empty:
            raise RuntimeError("No damage data loaded.")

        infrastructure_layers = load_infrastructure_layers()
        infrastructure_layers["streets"] = apply_network_criticality(
            infrastructure_layers.get("streets"),
            infrastructure_layers.get("hospitals"),
            infrastructure_layers.get("water_util"),
        )

        _emit(progress_callback, log_callback, "damage_analysis", "Analyzing damage patterns.", 18)
        damage_analysis = analyze_damage_patterns(damage_gdf)

        _emit(progress_callback, log_callback, "grid", "Creating the spatial hex grid.", 28)
        hex_gdf = create_hex_grid(damage_gdf)
        if hex_gdf.empty:
            raise RuntimeError("Failed to create the spatial analysis grid.")
        hex_gdf = integrate_spatial_data(hex_gdf, damage_gdf, infrastructure_layers)

        _emit(progress_callback, log_callback, "strategy", "Applying municipality rebuilding strategies.", 38)
        hex_gdf["rebuilding_strategy"] = hex_gdf.apply(
            lambda row: determine_rebuilding_strategy(row, damage_analysis), axis=1
        )

        _emit(progress_callback, log_callback, "scoring", "Computing AI reconstruction scores.", 48)
        hex_gdf = apply_scoring_pipeline(hex_gdf, damage_analysis)

        _emit(progress_callback, log_callback, "explanations", "Generating expert explanations.", 56)
        hex_gdf["expert_explanation"] = hex_gdf.apply(generate_expert_explanation, axis=1)

        infrastructure_needs = {}
        if profile == "full":
            _emit(progress_callback, log_callback, "needs", "Reviewing selected-sector infrastructure needs.", 62)
            infrastructure_needs = analyze_infrastructure_needs(
                hex_gdf,
                infrastructure_layers,
                selected_projects,
                damage_gdf,
            )
        else:
            _emit(progress_callback, log_callback, "needs", "Skipping the detailed needs scan for faster web execution.", 62)

        _emit(progress_callback, log_callback, "projects", "Generating project portfolios.", 72)
        projects_df = generate_projects_from_zones(hex_gdf, selected_projects, top_n=TOP_PROJECTS_COUNT)
        projects_df = assign_project_phases(projects_df, num_phases=4)
        projects_df = enrich_projects_with_reference_points(projects_df, infrastructure_layers)

        streets_projects_df = None
        streets_layer = infrastructure_layers.get("streets")
        if streets_layer is not None and not streets_layer.empty:
            streets_projects_df = generate_street_reconstruction_projects(streets_layer, top_n=100)
            if streets_projects_df is not None and not streets_projects_df.empty:
                streets_projects_df = assign_project_phases(streets_projects_df, num_phases=4)
                streets_projects_df = enrich_projects_with_reference_points(streets_projects_df, infrastructure_layers)

        outputs["projects_excel"] = export_projects_to_excel(
            projects_df,
            output_path=os.path.join(output_dir, "gaza_reconstruction_projects.xlsx"),
        )
        if streets_projects_df is not None and not streets_projects_df.empty:
            outputs["streets_projects_excel"] = export_projects_to_excel(
                streets_projects_df,
                output_path=os.path.join(output_dir, "gaza_streets_reconstruction_projects.xlsx"),
            )

        _emit(progress_callback, log_callback, "exports", "Writing Excel outputs.", 80)
        outputs["priority_map"] = create_reconstruction_priority_map(
            hex_gdf,
            projects_df,
            infrastructure_layers,
            output_path=os.path.join(output_dir, "reconstruction_priority_map.html"),
        )
        outputs["phased_projects_excel"] = export_phased_excel(
            projects_df,
            output_path=os.path.join(output_dir, "phased_projects.xlsx"),
        )
        _emit(progress_callback, log_callback, "visuals", "Creating core map and dashboard outputs.", 86)
        outputs["interactive_dashboard"] = create_interactive_dashboard(
            hex_gdf,
            projects_df,
            damage_analysis,
            infrastructure_layers,
            output_path=os.path.join(output_dir, "interactive_dashboard.html"),
        )

        street_damage_counts = {}
        street_priority_counts = {}
        street_reconstruction_cost = 0

        if profile == "full":
            _emit(progress_callback, log_callback, "extended_visuals", "Creating extended visual reports.", 90)
            outputs["damage_heatmap"] = create_damage_heatmap(
                damage_gdf,
                output_path=os.path.join(output_dir, "damage_heatmap.html"),
            )
            if streets_layer is not None and not streets_layer.empty:
                outputs["damaged_streets_map"] = create_damaged_streets_map(
                    streets_layer,
                    output_path=os.path.join(output_dir, "damaged_streets_map.html"),
                )
            outputs["damage_animation"] = create_damage_animation(
                hex_gdf,
                output_path=os.path.join(output_dir, "damage_animation.html"),
            )
            outputs["damage_3d"] = create_3d_damage_visualization(
                hex_gdf,
                output_path=os.path.join(output_dir, "3d_damage_visualization.html"),
            )

        if profile == "full" and streets_layer is not None and not streets_layer.empty:
            streets_damage_result = create_streets_damage_map(
                streets_layer,
                output_path=os.path.join(output_dir, "streets_damage_map.html"),
            )
            if streets_damage_result is not None:
                outputs["streets_damage_map"], street_damage_counts = streets_damage_result

            streets_recon_result = create_streets_reconstruction_map(
                streets_layer,
                output_path=os.path.join(output_dir, "streets_reconstruction_map.html"),
            )
            if streets_recon_result is not None:
                outputs["streets_reconstruction_map"], street_priority_counts, street_reconstruction_cost = streets_recon_result

        outputs["dashboard_png"] = create_statistical_dashboard(
            hex_gdf,
            projects_df,
            output_path=os.path.join(output_dir, "statistical_dashboard.png"),
        )
        outputs["summary_report"] = generate_summary_report(
            hex_gdf,
            projects_df,
            damage_analysis,
            output_path=os.path.join(output_dir, "summary_report.txt"),
        )
        if profile == "full":
            _emit(progress_callback, log_callback, "documentation", "Generating documentation outputs.", 96)
            outputs["documentation_docx"] = create_project_documentation(
                output_path=os.path.join(output_dir, "project_documentation.docx"),
            )
            outputs["erd_report"] = generate_data_erd(
                damage_gdf,
                infrastructure_layers,
                hex_gdf,
                projects_df,
                output_path=os.path.join(output_dir, "data_erd_documentation.txt"),
            )

        _emit(progress_callback, log_callback, "complete", "Workflow completed successfully.", 100)
        return {
            "success": True,
            "profile": profile,
            "version": SYSTEM_VERSION,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now().isoformat(),
            "output_dir": output_dir,
            "selected_projects": selected_projects,
            "selected_project_labels": [PROJECT_TYPES[key]["name"] for key in selected_projects],
            "projects_count": int(len(projects_df)) if projects_df is not None else 0,
            "street_projects_count": int(len(streets_projects_df)) if streets_projects_df is not None else 0,
            "damage_site_count": int(damage_analysis.get("total_damage_sites", 0)),
            "zone_count": int(len(hex_gdf)),
            "outputs": {key: value for key, value in outputs.items() if value},
            "infrastructure_needs": infrastructure_needs,
            "street_damage_counts": street_damage_counts,
            "street_priority_counts": street_priority_counts,
            "street_reconstruction_cost": street_reconstruction_cost,
        }
    except Exception as exc:
        _emit(progress_callback, log_callback, "error", f"Workflow failed: {exc}", 100)
        return {
            "success": False,
            "profile": profile,
            "version": SYSTEM_VERSION,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now().isoformat(),
            "output_dir": output_dir,
            "selected_projects": selected_projects,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
