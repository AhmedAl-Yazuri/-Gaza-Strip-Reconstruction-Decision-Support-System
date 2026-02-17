# Gaza Strip Reconstruction Decision Support System (DSS)
Academic Project Documentation  
**Institution:** University Research Project  
**Course:** Advanced GIS & Decision Support Systems  
**Last Update:** February 17, 2026  
**Version:** 1.0.0  

---

## Project Overview
The **Gaza Reconstruction DSS** is an AI-enhanced geospatial decision support platform for post-conflict reconstruction planning.  
It combines satellite-based damage data, spatial analysis, multi-criteria scoring, and interactive outputs to prioritize where reconstruction should start first.

---

## Key Features
- Hexagonal spatial analysis across Gaza (automatically generated zones from damage extent)
- Time-aware damage scoring from UNOSAT temporal cycles
- Infrastructure-aware prioritization (hospitals, schools, roads, utilities, municipalities)
- Network criticality for streets (strategic roads and connectivity impact)
- Interactive user selection of project focus sectors
- Automated generation of reconstruction portfolios (sector projects + street projects)
- Multi-output delivery (HTML maps, Excel sheets, PNG dashboard, TXT report, DOCX docs)

---

## Current Project Structure
```text
-Gaza-Strip-Reconstruction-Decision-Support-System/
├── reconstruction_modules/
│   ├── main.py
│   ├── config.py
│   ├── data_loader.py
│   ├── data_loader_common.py
│   ├── data_loader_downloads.py
│   ├── data_loader_fixed_data.py
│   ├── data_loader_loaders.py
│   ├── spatial_analysis.py
│   ├── municipality_analysis.py
│   ├── scoring_engine.py
│   ├── network_analysis.py
│   ├── project_selector.py
│   ├── project_generator.py
│   ├── phased_implementation.py
│   ├── population_data.py
│   ├── visualization.py
│   ├── streets_maps.py
│   ├── advanced_maps.py
│   ├── interactive_charts.py
│   ├── project_documentation.py
│   ├── data_erd_generator.py
│   └── gaza_gis_data/   (GIS inputs)
│
├── output/              (generated outputs)
├── PROJECT_PROGRESS_PRESENTATION_AR.md

```

---

## How the Code Works
The main pipeline is executed from:

```bash
python reconstruction_modules/main.py
```

Execution flow:
1. **Load Data**: Reads UNOSAT damage data and infrastructure layers.
2. **Damage Analysis**: Builds damage pattern indicators.
3. **Hex Grid Generation**: Creates analysis zones across Gaza.
4. **Spatial Integration**: Joins damage/infrastructure metrics into each zone.
5. **Strategy Assignment**: Applies municipality-based rebuilding strategy.
6. **AI Scoring**: Computes priority scores for each zone.
7. **Project Selection**: User chooses focus sectors (health, roads, utilities, etc.).
8. **Project Generation**: Creates prioritized reconstruction projects.
9. **Phasing & Enrichment**: Assigns implementation phases and reference points.
10. **Visualization & Reporting**: Exports maps, dashboards, Excel files, and reports.

---

## Project Outputs
After running the system, output files are saved in:

```text
output/
```

Typical generated files:
- `reconstruction_priority_map.html` (interactive reconstruction map)
- `damage_heatmap.html` (damage density heatmap)
- `damaged_streets_map.html` (damaged streets visualization)
- `streets_damage_map.html` (street damage status map)
- `streets_reconstruction_map.html` (street reconstruction priorities)
- `damage_animation.html` (interactive animation)
- `3d_damage_visualization.html` (3D damage visualization)
- `gaza_reconstruction_projects.xlsx` (main project portfolio)
- `gaza_streets_reconstruction_projects.xlsx` (streets project portfolio)
- `phased_projects.xlsx` (projects grouped by implementation phase)
- `statistical_dashboard.png` (summary dashboard)
- `summary_report.txt` (text summary report)
- `project_documentation.docx` (documented project report)
- `data_erd_documentation.txt` (data/ERD documentation)
